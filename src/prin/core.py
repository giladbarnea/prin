from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Iterable, Protocol, Self

from prin import filters
from prin.formatters import Formatter, HeaderFormatter
from prin.path_classifier import classify_pattern

if TYPE_CHECKING:
    from .cli_common import Context


class NodeKind(Enum):
    DIRECTORY = auto()
    FILE = auto()
    OTHER = auto()


@dataclass(frozen=True)
class Entry:
    path: PurePosixPath
    name: str
    kind: NodeKind


class Writer(Protocol):
    def write(self, text: str) -> None: ...


class SourceAdapter(Protocol):
    """
    Filesystem-style adapter for various sources.
    Maintains a single root path that filesystem operations are relative to.
    """

    root: PurePosixPath

    def resolve_pattern(self: Self, path) -> PurePosixPath: ...
    def list_dir(self: Self, dir_path) -> Iterable[Entry]: ...
    def read_file_bytes(self: Self, file_path) -> bytes: ...
    def is_empty(self: Self, file_path) -> bool: ...
    def exists(self: Self, path) -> bool: ...


def _is_text_semantically_empty(text: str) -> bool:
    """
    Return True if text contains only imports, __all__=..., or docstrings.

    Mirrors the behavior used by the filesystem implementation.
    """
    import ast

    if not text.strip():
        return True

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        elif isinstance(node, ast.Assign):
            targets = node.targets
            if (
                len(targets) == 1
                and isinstance(targets[0], ast.Name)
                and targets[0].id == "__all__"
            ):
                continue
            # Any other assignment means the file is not semantically empty
            return False
        elif (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            # Docstring
            continue
        else:
            return False
    return True


def _is_text_bytes(blob: bytes) -> bool:
    if b"\x00" in blob:
        return False
    try:
        blob.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _decode_text(blob: bytes) -> str:
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError:
        return blob.decode("latin-1")


def is_blob_semantically_empty(blob: bytes, file_path: PurePosixPath) -> bool:
    """Return True if the provided blob represents a semantically empty text file."""
    blob = blob.strip()
    if not blob:
        return True
    if file_path.suffix not in (".py", ".pyi"):
        return False
    if not _is_text_bytes(blob):
        return False
    text = _decode_text(blob)
    return _is_text_semantically_empty(text)


class StdoutWriter(Writer):
    def write(self, text: str) -> None:
        sys.stdout.write(text)


class StringWriter(Writer):
    """
    Collects written text into an internal buffer for tests and callers.

    Provides a lightweight Writer implementation that accumulates text and
    exposes it via the `text()` accessor.
    """

    def __init__(self) -> None:
        self._parts: list[str] = []

    def write(self, text: str) -> None:  # Writer protocol
        self._parts.append(text)

    def text(self) -> str:
        return "".join(self._parts)


class FileBudget:
    """
    Global print-budget shared across sources. Each printed file consumes 1 unit.
    When exhausted, traversal and printing should stop as early as possible.
    """

    def __init__(self, max_files: int | None) -> None:
        self._remaining = max_files if (isinstance(max_files, int) and max_files > 0) else None

    def spent(self) -> bool:
        return self._remaining == 0

    def available(self) -> bool:
        return self._remaining is None or self._remaining > 0

    def consume(self) -> None:
        if self._remaining is None:
            return
        if self._remaining > 0:
            self._remaining -= 1


class DepthFirstPrinter:
    source: SourceAdapter
    formatter: Formatter
    exclusions: list
    extensions: list
    include_empty: bool
    only_headers: bool

    def __init__(
        self,
        source: SourceAdapter,
        formatter: Formatter,
        ctx: "Context",
    ) -> None:
        self.source = source
        if ctx.only_headers:
            if not isinstance(formatter, HeaderFormatter):
                import logging

                logging.getLogger(__name__).warning(
                    "[WARNING] --only-headers was specified but formatter passed is not a HeaderFormatter. Forcing to HeaderFormatter."
                )
            formatter = HeaderFormatter()
        self.formatter = formatter

        self._set_from_context(ctx)
        self._printed_paths: set[str] = set()

    def _set_from_context(self, ctx: "Context") -> None:
        self.exclusions = ctx.exclusions
        self.extensions = ctx.extensions
        self.include_empty = ctx.include_empty
        self.only_headers = ctx.only_headers

    def run(self, patterns: list, writer: Writer, budget: "FileBudget | None" = None) -> None:
        for pattern in patterns:
            if budget is not None and budget.spent():
                return
            root = self.source.resolve_pattern(pattern)

            # Experimental: if the resolved root does not exist on the filesystem,
            # treat the token as a search pattern and match files by name using re.search
            # when the token is classified as regex. This is used by tests/test_matching.py.
            try:
                if anchor_base is not None and not self.source.exists(root):
                    self._search_and_print(anchor_base, root_spec, writer, budget)
                    continue
            except Exception:
                # If existence check is not applicable for this adapter, fall back to normal traversal
                pass
            # Decide display base: if root is under anchor_base, use anchor; otherwise the root itself
            display_base = root
            if anchor_base is not None:
                try:
                    _ = root.relative_to(anchor_base)
                    display_base = anchor_base
                except Exception:
                    display_base = root
            stack: list[PurePosixPath] = [root]
            while stack:
                if budget is not None and budget.spent():
                    return
                current = stack.pop()
                try:
                    entries = list(self.source.list_dir(current))
                except NotADirectoryError:
                    # Treat the current path as a file
                    file_entry = Entry(path=current, name=current.name, kind=NodeKind.FILE)
                    self._handle_file(
                        file_entry, writer, base=display_base, force=True, budget=budget
                    )
                    continue
                except FileNotFoundError:
                    # Skip missing paths. Smell: will cover-up a bug in list_dir.
                    continue
                # Sort directories then files, both case-insensitive
                dirs, files = [], []
                for e in entries:
                    match e.kind:
                        case NodeKind.DIRECTORY:
                            dirs.append(e)
                        case NodeKind.FILE:
                            files.append(e)
                        case _:
                            import logging

                            logging.getLogger(__name__).warning(
                                "[WARNING] Unexpected node kind: %r", e.kind
                            )
                dirs.sort(key=lambda e: e.name.casefold())
                files.sort(key=lambda e: e.name.casefold())

                for entry in reversed(dirs):  # reversed for stack DFS order
                    if not self._excluded(entry):
                        stack.append(entry.path)

                for entry in files:
                    self._handle_file(entry, writer, base=display_base, budget=budget)

    def _pattern_matches(self, entry: Entry, token: str, *, base: PurePosixPath) -> bool:
        """
        Return True if entry's name matches token according to experimental rules.

        For this POC, when token is classified as regex or text, we use re.search
        against the entry's filename (not the full path) to mimic fd-like behavior
        of matching within a single path segment.
        """
        # Two modes only: glob or regex (regex by default). Match against full POSIX path (relative to base).
        try:
            rel = self._display_path(entry.path, base)
        except Exception:
            rel = str(entry.path)
        kind = classify_pattern(token)
        if kind == "glob":
            from fnmatch import fnmatch

            return fnmatch(rel, token)
        try:
            return re.search(token, rel) is not None
        except re.error:
            return False

    def _search_and_print(
        self,
        base: PurePosixPath,
        token: str,
        writer: Writer,
        budget: "FileBudget | None",
    ) -> None:
        """
        Traverse from base and print files whose names match token.

        Respects existing exclusion, extension, and emptiness rules.
        """
        stack: list[PurePosixPath] = [base]
        while stack:
            if budget is not None and budget.spent():
                return
            current = stack.pop()
            try:
                entries = list(self.source.list_dir(current))
            except NotADirectoryError:
                # Treat current as a file
                file_entry = Entry(path=current, name=current.name, kind=NodeKind.FILE)
                if (
                    not self._excluded(file_entry)
                    and self._extension_match(file_entry)
                    and self._pattern_matches(file_entry, token, base=base)
                ):
                    self._handle_file(file_entry, writer, base=base, budget=budget)
                continue
            except FileNotFoundError:
                continue

            dirs, files = [], []
            for e in entries:
                match e.kind:
                    case NodeKind.DIRECTORY:
                        dirs.append(e)
                    case NodeKind.FILE:
                        files.append(e)
                    case _:
                        import logging

                        logging.getLogger(__name__).warning(
                            "[WARNING] Unexpected node kind: %r", e.kind
                        )
            dirs.sort(key=lambda e: e.name.casefold())
            files.sort(key=lambda e: e.name.casefold())

            for entry in reversed(dirs):
                if not self._excluded(entry):
                    stack.append(entry.path)

            for entry in files:
                if self._excluded(entry):
                    continue
                if not self._extension_match(entry):
                    continue
                if not self.include_empty and self.source.is_empty(entry.path):
                    continue
                if self._pattern_matches(entry, token, base=base):
                    self._handle_file(entry, writer, base=base, budget=budget)

    def _excluded(self, entry: Entry) -> bool:
        # The reference implementation accepts strings/paths/globs/callables
        return filters.is_excluded(entry, exclude=self.exclusions)

    def _extension_match(self, entry: Entry) -> bool:
        return filters.extension_match(entry, extensions=self.extensions)

    def _handle_file(
        self,
        entry: Entry,
        writer: Writer,
        *,
        base: PurePosixPath,
        force: bool = False,
        budget: "FileBudget | None" = None,
    ) -> None:
        # Avoid duplicate prints when a file is both an explicit root and encountered during traversal
        key = str(entry.path)
        if key in self._printed_paths:
            return

        if budget and budget.spent():
            return

        if not force:
            if self._excluded(entry):
                return
            if not self._extension_match(entry):
                return
            if not self.include_empty and self.source.is_empty(entry.path):
                return

        path_str = self._display_path(entry.path, base)
        if self.only_headers:
            writer.write(self.formatter.format(path_str, ...))
        else:
            blob = self.source.read_file_bytes(entry.path)
            if _is_text_bytes(blob):
                text = _decode_text(blob)
                writer.write(self.formatter.format(path_str, text))
            else:
                writer.write(self.formatter.binary(path_str))
        budget and budget.consume()
        self._printed_paths.add(key)

    def _display_path(self, path: PurePosixPath, base: PurePosixPath) -> str:
        # If path is under base, return a relative POSIX path; otherwise absolute
        try:
            rel = os.path.relpath(str(path), start=str(base))
            if rel == "." or rel == "":
                return path.name
        except Exception:
            return str(path)
