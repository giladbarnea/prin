from __future__ import annotations

import functools
import os
import re
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Iterable

from prin import core
from prin.core import Entry, NodeKind, SourceAdapter
from prin.filters import GitIgnoreEngine, extension_match, is_excluded
from prin.path_classifier import classify_pattern

if TYPE_CHECKING:
    from prin.cli_common import Context


def settrace_if_returns(value):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if result is value:
                import pudb

                pudb.set_trace()
            return result

        return wrapper

    return decorator


# Notes to self:
# (/tmp/RustDesk / ..).parent == /tmp/RustDesk  # Lexical
# (/tmp/RustDesk / ..).resolve() == /tmp        # Real
# (/tmp/RustDesk).relative_to(/tmp) == RustDesk
# (/usr).relative_to(/tmp) == ValueError
# (/usr).relative_to(/tmp, walk_up=True) == ../usr  <- key!
# (/usr).samefile(/usr/bin/..) == True              <- Also useful, because resolves implicitly.
# (RustDesk).is_relative_to(/tmp) == False      # Lexical
# ('/tmp')  /  ('RustDesk') == '/tmp/RustDesk'
# ('/tmp')  /  ('/tmp/RustDesk') == '/tmp/RustDesk'
# ('/tmp')  /  ('/usr') == '/usr'         # Last wins


class FileSystemSource(SourceAdapter):
    """
    Adapter for the local filesystem.
    """

    anchor: Path
    # Configuration derived from Context (filters)
    exclusions: list
    extensions: list
    include_empty: bool
    _ignore_engine: GitIgnoreEngine | None

    def __init__(self, anchor=None) -> None:
        self.anchor = Path(anchor or Path.cwd()).resolve()
        self.exclusions = []
        self.extensions = []
        self.include_empty = False
        self._ignore_engine = None
        super().__init__()

    def __repr__(self) -> str:
        return f"FileSystemSource(anchor={self.anchor!r})"

    # Removed: display is computed internally by walk(); keep no public API.

    def resolve(self, path) -> Path:
        """
        Resolve the path relative to the anchor to its absolute form.

        Implementation detail: os.path.resolve() resolves symlinks, which is undesired, and .absolute() does not resolve '..' segments, which is desired, so we use normpath+absolute to resolve both.
        """
        return Path(os.path.normpath((self.anchor / path).absolute()))

    def list_dir(self, dir_path) -> Iterable[Entry]:
        entries: list[Entry] = []
        with os.scandir(Path(str(dir_path))) as dir_iterator:
            for entry in dir_iterator:
                if entry.is_dir(follow_symlinks=False):
                    kind = NodeKind.DIRECTORY
                elif entry.is_file(follow_symlinks=False):
                    kind = NodeKind.FILE
                else:
                    kind = NodeKind.OTHER
                entries.append(
                    Entry(
                        path=PurePosixPath(entry.path),
                        name=entry.name,
                        kind=kind,
                    )
                )
        return entries

    def read_file_bytes(self, file_path) -> bytes:
        return self.resolve(file_path).read_bytes()

    def exists(self, path) -> bool:
        # Path.exists() does not support follow_symlinks, and resolve() already normalizes.
        return self.resolve(path).exists()

    def is_empty(self, file_path) -> bool:
        # Read bytes and use shared semantic emptiness check
        blob = self.read_file_bytes(file_path)
        if not blob.strip():
            return True
        path = self.resolve(file_path)
        return core.is_blob_semantically_empty(blob, path)

    # Depth-first traversal delegated to the adapter. Yields files only, in stable order.
    def _walk_dfs(self, root) -> Iterable[Entry]:
        """
        Yield Entry objects for files under the given root in depth-first order.

        - If root is a file, yields that single file entry.
        - If root is a directory, traverses directories first (case-insensitive sort),
          then files (case-insensitive sort) at each level.
        - Symbolic links are not followed.
        """
        start = Path(str(root))
        # If it's a file, emit and stop
        try:
            if start.is_file():
                yield Entry(path=PurePosixPath(str(start)), name=start.name, kind=NodeKind.FILE)
                return
        except Exception:
            # Non-existent or inaccessible; let caller decide handling
            return

        # Treat non-directories as non-traversable
        if not start.exists() or not start.is_dir():
            return

        stack: list[Path] = [start]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    dirs: list[os.DirEntry] = []
                    files: list[os.DirEntry] = []
                    for entry in it:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                dirs.append(entry)
                            elif entry.is_file(follow_symlinks=False):
                                files.append(entry)
                            else:
                                # Skip OTHER kinds
                                continue
                        except PermissionError:
                            continue
                # Sort directories then files, both case-insensitive
                dirs.sort(key=lambda e: e.name.casefold())
                files.sort(key=lambda e: e.name.casefold())

                # Push directories in reverse order for stack-based DFS
                for d in reversed(dirs):
                    stack.append(Path(d.path))

                # Yield files at this level
                for f in files:
                    yield Entry(
                        path=PurePosixPath(f.path),
                        name=f.name,
                        kind=NodeKind.FILE,
                    )
            except (FileNotFoundError, NotADirectoryError, PermissionError):
                # Skip paths that disappeared or aren't traversable
                continue

    def _display_rel(self, path: Path, base: Path) -> str:
        try:
            rel = os.path.relpath(str(path), start=str(base))
            if rel == "." or rel == "":
                return path.name
            return rel
        except Exception:
            return str(path)

    def walk_pattern(self, pattern: str, search_path: str | None) -> Iterable[Entry]:
        """
        Search for pattern in the given path.
        If search_path is None, use anchor.
        If pattern is empty, list all files in the path.
        """
        # Determine the search root (absolute path used for traversal)
        if search_path is None:
            search_root = self.anchor
        else:
            search_root = self.resolve(search_path)

        # Determine display relativity rules based on the raw search_path token
        # Rules (cwd == anchor):
        # - None: display relative to cwd (bare, no leading './')
        # - Absolute token: display absolute paths
        # - Token == '.' or startswith './': display relative to cwd with leading './'
        # - Token startswith '../': display relative to resolved(base) with the literal '../...' prefix
        # - Other relative token (e.g., 'foo', 'foo/bar'): display relative to cwd (bare)
        abs_display: bool = False
        display_prefix: str = ""
        if search_path is None:
            display_base = self.anchor
        else:
            if Path(search_path).is_absolute():
                abs_display = True
                display_base = search_root
            elif search_path == "." or search_path.startswith("./"):
                display_base = self.anchor
                display_prefix = "./"
            elif search_path.startswith("../"):
                display_base = search_root
                # Keep the literal ../... prefix normalized
                display_prefix = os.path.normpath(search_path)
            else:
                # Child path under cwd without explicit './' → bare paths relative to cwd
                display_base = self.anchor

        def make_display_path(abs_file: Path) -> tuple[str, str | None]:
            if abs_display:
                # For absolute display, preserve a double-leading tag-friendly path as-is without duplicate prefixes
                return str(abs_file), None
            rel = self._display_rel(abs_file, display_base)
            if display_prefix:
                # Avoid duplicate separators
                return f"{display_prefix.rstrip('/')}/{rel}", f"{display_prefix.rstrip('/')}/{rel}"
            return rel, None

        # Special case: if pattern is an exact existing file path, also emit it explicitly.
        # Do not return early; still traverse to allow pattern matching to include other files.
        if pattern and search_path is None:
            try:
                pattern_as_path = self.resolve(pattern)
                if pattern_as_path.exists() and pattern_as_path.is_file():
                    if str(pattern_as_path).startswith(str(self.anchor) + os.sep):
                        rel = self._display_rel(pattern_as_path, self.anchor)
                        disp = rel
                    else:
                        disp = str(pattern_as_path)
                    yield Entry(
                        path=PurePosixPath(disp),
                        name=pattern_as_path.name,
                        kind=NodeKind.FILE,
                        abs_path=PurePosixPath(str(pattern_as_path)),
                        explicit=True,
                    )
            except Exception:
                pass

        # If no pattern or empty pattern, list all files
        if not pattern:
            if search_root.is_file():
                # Single file
                disp, disp_raw = make_display_path(search_root)
                yield Entry(
                    path=PurePosixPath(disp),
                    name=search_root.name,
                    kind=NodeKind.FILE,
                    abs_path=PurePosixPath(str(search_root)),
                    explicit=True,
                    display_path=disp_raw,
                )
            else:
                # Directory - traverse all files
                for e in self._walk_dfs(search_root):
                    f_abs = Path(str(e.path))
                    disp, disp_raw = make_display_path(f_abs)
                    cand = Entry(
                        path=PurePosixPath(disp),
                        name=e.name,
                        kind=e.kind,
                        abs_path=PurePosixPath(str(f_abs)),
                        display_path=disp_raw,
                    )
                    if self.should_print(cand):
                        yield cand
            return

        # Pattern matching
        kind = classify_pattern(pattern)
        # For pattern matching, use the same display rules

        for e in self._walk_dfs(search_root):
            f_abs = Path(str(e.path))
            rel = self._display_rel(f_abs, search_root)

            match = False
            if kind == "glob":
                match = fnmatch(rel, pattern)
            else:
                try:
                    match = re.search(pattern, rel) is not None
                except re.error:
                    match = False

            if match:
                disp, disp_raw = make_display_path(f_abs)
                cand = Entry(
                    path=PurePosixPath(disp),
                    name=e.name,
                    kind=e.kind,
                    abs_path=PurePosixPath(str(f_abs)),
                    display_path=disp_raw,
                )
                if self.should_print(cand):
                    yield cand

    # Configuration from Context
    def configure(self, ctx: "Context") -> None:
        self.exclusions = ctx.exclusions
        self.extensions = ctx.extensions
        self.include_empty = ctx.include_empty
        # Initialize ignore engine unless --no-ignore or --no-exclude
        if not ctx.no_exclude and not ctx.no_ignore:
            self._ignore_engine = GitIgnoreEngine(self.anchor)
        else:
            self._ignore_engine = None

    def should_print(self, entry: Entry) -> bool:
        """Source-owned filtering decision"""
        if entry.explicit:
            return True
        # Exclusion rules
        # Normalize display path for filtering
        # 1) If absolute, make it relative to the adapter anchor so hidden globs like '.*' work
        # 2) Strip leading './' or '../' segments used only for display
        target = entry.path.as_posix()
        if target.startswith("/"):
            try:
                base = str(self.anchor)
                absolute = str(entry.abs_path or entry.path)
                target = os.path.relpath(absolute, start=base)
            except Exception:
                # Fallback: remove only the leading slash to avoid blocking 'Hidden' checks at project root
                target = target.lstrip("/")
        if target.startswith("./"):
            target = target[2:]
        while target.startswith("../"):
            target = target[3:]
        dummy = Entry(path=PurePosixPath(target), name=entry.name, kind=entry.kind)
        # Apply gitignore engine first (fd behavior: VCS ignores by default, overridable)
        if self._ignore_engine is not None:
            abs_path = Path(str(entry.abs_path or entry.path))
            if self._ignore_engine.is_ignored(abs_path):
                return False
        if is_excluded(dummy, exclude=self.exclusions):
            return False
        if not extension_match(dummy, extensions=self.extensions):
            return False
        return not (not self.include_empty and self.is_empty(entry.abs_path or entry.path))

    # Source-owned body reading and text/binary decision
    def read_body_text(self, entry: Entry) -> tuple[str | None, bool]:
        blob = self.read_file_bytes(entry.abs_path or entry.path)
        if core._is_text_bytes(blob):
            text = core._decode_text(blob)
            return text, False
        return None, True
