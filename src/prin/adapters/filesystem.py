from __future__ import annotations

import functools
import os
from pathlib import Path, PurePosixPath
from typing import Iterable, Self

from prin import core
from prin.core import Entry, NodeKind, SourceAdapter


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

    def __init__(self, anchor=None) -> None:
        self.anchor = Path(anchor or Path.cwd()).resolve()
        super().__init__()

    def __repr__(self) -> str:
        return f"FileSystemSource(anchor={self.anchor!r})"

    def _ensure_exists(func):
        # @functools.wraps(func)
        def wrapper(self: Self, *args, **kwargs):
            if not args:
                raise FileNotFoundError("No positional path provided")
            path = args[0]
            if not self.exists(path):
                raise FileNotFoundError(f"{path!r} does not exist. Anchor: {self.anchor!r}")
            return func(self, *args, **kwargs)

        return wrapper

    def resolve_display(self, path) -> str:
        """
        Following the behavior of fd and rg, displayed paths are agnostic of the anchor.
        """
        return str(path)

    def resolve(self, path) -> Path:
        """
        Resolve the path relative to the anchor to its absolute form.

        Implementation detail: resolve resolves symlinks, which is undesired, and absolute does not resolve '..' segments, which is desired, so we use normpath+absolute to resolve both.
        """
        return Path(os.path.normpath((self.anchor / path).absolute()))

    @_ensure_exists
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

    @_ensure_exists
    def read_file_bytes(self, file_path) -> bytes:
        return self.resolve(file_path).read_bytes()

    def exists(self, path) -> bool:
        return self.resolve(path).exists(follow_symlinks=False)

    @_ensure_exists
    def is_empty(self, file_path) -> bool:
        # Read bytes and use shared semantic emptiness check
        blob = self.read_file_bytes(file_path)
        if not blob.strip():
            return True
        path = self.resolve(file_path)
        return core.is_blob_semantically_empty(blob, path)
