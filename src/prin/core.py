from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Iterable, Protocol, Self

from prin.formatters import Formatter, HeaderFormatter

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
    # Absolute path identifier for reading (when path is used for display/filtering)
    abs_path: PurePosixPath | None = None
    # True when explicitly provided as a root token (force-include semantics)
    explicit: bool = False


class Writer(Protocol):
    def write(self, text: str) -> None: ...


class SourceAdapter(Protocol):
    """
    Filesystem-style adapter for various sources.
    Now owns traversal, filtering, emptiness and I/O.

    - Responsibilities: configure, walk, should_print, read_body_text, resolve/exists.
    - Non-responsibilities: printing, budgeting, formatting selection.
    """

    anchor: Path

    def resolve(self: Self, path) -> PurePosixPath: ...
    def list_dir(self: Self, dir_path) -> Iterable[Entry]: ...
    def read_file_bytes(self: Self, file_path) -> bytes: ...
    def is_empty(self: Self, file_path) -> bool: ...
    def exists(self: Self, path) -> bool: ...
    def configure(self: Self, ctx: "Context") -> None: ...
    def walk(self: Self, token: str) -> Iterable[Entry]: ...
    def walk_pattern(self: Self, pattern: str, search_path: str | None) -> Iterable[Entry]: ...
    def should_print(self: Self, entry: Entry) -> bool: ...
    def read_body_text(self: Self, entry: Entry) -> tuple[str | None, bool]: ...


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
    """
    Printer with strict responsibilities: printing, budget, formatter.
    Delegates traversal, filtering, and I/O to the source adapter.
    """

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
        # Delegate configuration to the source (filters, extensions, include_empty, etc.)
        self.source.configure(ctx)
        self._printed_paths: set[str] = set()

    def _set_from_context(self, ctx: "Context") -> None:
        self.exclusions = ctx.exclusions
        self.extensions = ctx.extensions
        self.include_empty = ctx.include_empty
        self.only_headers = ctx.only_headers

    def run(self, patterns: list, writer: Writer, budget: "FileBudget | None" = None) -> None:
        for token in patterns:
            if budget is not None and budget.spent():
                return
            for entry in self.source.walk(token):
                if budget is not None and budget.spent():
                    return
                self._handle_file(entry, writer, budget=budget)

    def run_pattern(
        self,
        pattern: str,
        search_path: str | None,
        writer: Writer,
        budget: "FileBudget | None" = None,
    ) -> None:
        """New interface: run with pattern and search path."""
        if budget is not None and budget.spent():
            return
        for entry in self.source.walk_pattern(pattern, search_path):
            if budget is not None and budget.spent():
                return
            self._handle_file(entry, writer, budget=budget)

    def _handle_file(
        self,
        entry: Entry,
        writer: Writer,
        *,
        force: bool = False,
        budget: "FileBudget | None" = None,
    ) -> None:
        # Avoid duplicate prints when a file is both an explicit root and encountered during traversal
        key = str(entry.abs_path or entry.path)
        if key in self._printed_paths:
            return

        if budget and budget.spent():
            return

        # Delegate include/exclude logic to the source
        if not (force or self.source.should_print(entry)):
            return

        path_str = entry.path.as_posix()
        if self.only_headers:
            writer.write(self.formatter.format(path_str, ...))
        else:
            body_text, is_binary = self.source.read_body_text(entry)
            if is_binary:
                writer.write(self.formatter.binary(path_str))
            else:
                writer.write(self.formatter.format(path_str, body_text or ""))
        budget and budget.consume()
        self._printed_paths.add(key)
