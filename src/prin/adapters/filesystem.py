from __future__ import annotations

import functools
import os
from pathlib import Path, PurePosixPath
from typing import Iterable, Self

from prin import core
from prin.adapters import errors
from prin.core import Entry, NodeKind, SourceAdapter


def _to_posix(path: Path) -> PurePosixPath:
    # Normalize to POSIX-like logical paths for cross-source formatting
    return PurePosixPath(str(path.as_posix()))


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


class FileSystemSource(SourceAdapter):
    """
    Adapter for the local filesystem.
    """

    root: Path

    def __init__(self, root) -> None:
        self.root = Path(root).resolve(strict=True)

    def _ensure_existing_subpath(func):
        """Also passes a resolved path to the function"""

        # @functools.wraps(func)
        def wrapper(self: Self, *args, **kwargs):
            if not args:
                # import pudb

                # pudb.set_trace()
                raise errors.NotExistingSubpath("No positional path provided")
            path = args[0]
            candidate = Path(path)
            # import pudb

            # pudb.set_trace()
            if not self.exists(candidate):
                raise errors.NotExistingSubpath(
                    f"{path!r} is not an existing subpath of {self.root!r}"
                )
            candidate = (self.root / candidate).resolve()
            args = (candidate, *args[1:])
            return func(self, *args, **kwargs)

        return wrapper

    @_ensure_existing_subpath
    def resolve_pattern(self, path) -> PurePosixPath:
        return _to_posix((self.root / path).resolve())

    @_ensure_existing_subpath
    def list_dir(self, dir_path) -> Iterable[Entry]:
        entries: list[Entry] = []
        # import pudb

        # pudb.set_trace()
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
                        path=_to_posix(Path(entry.path)),
                        name=entry.name,
                        kind=kind,
                    )
                )
        return entries

    @_ensure_existing_subpath
    def read_file_bytes(self, file_path) -> bytes:
        return file_path.read_bytes()

    def exists(self, path) -> bool:
        return Path(path).exists()
        try:
            # Subtle bug: resolve resolves symlinks, which is undesired
            target = (self.root / p).resolve(strict=True)
        except (FileNotFoundError, OSError, PermissionError):
            return False
        return target.is_relative_to(self.root)

    @_ensure_existing_subpath
    def is_empty(self, file_path) -> bool:
        # Read bytes and use shared semantic emptiness check
        p = Path(file_path)
        if not p.is_file():
            return False
        try:
            blob = p.read_bytes()
        except Exception:
            return False
        if not blob.strip():
            return True
        return core.is_blob_semantically_empty(blob, file_path)
