from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Iterable

from ..core import Entry, NodeKind, SourceAdapter


def _to_posix(path: Path) -> PurePosixPath:
    # Normalize to POSIX-like logical paths for cross-source formatting
    return PurePosixPath(str(path.as_posix()))


class FileSystemSource(SourceAdapter):
    def __init__(self, root_cwd: Path | None = None) -> None:
        self._cwd = Path.cwd() if root_cwd is None else Path(root_cwd)

    def resolve_root(self, root_spec: str) -> PurePosixPath:
        return _to_posix((self._cwd / root_spec).resolve())

    def list_dir(self, dir_path: PurePosixPath) -> Iterable[Entry]:
        p = Path(str(dir_path))
        entries: list[Entry] = []
        with os.scandir(p) as it:
            for e in it:
                if e.is_dir(follow_symlinks=False):
                    kind = NodeKind.DIRECTORY
                elif e.is_file(follow_symlinks=False):
                    kind = NodeKind.FILE
                else:
                    kind = NodeKind.OTHER
                entries.append(
                    Entry(
                        path=_to_posix(Path(e.path)),
                        name=e.name,
                        kind=kind,
                    )
                )
        return entries

    def read_file_bytes(self, file_path: PurePosixPath) -> bytes:
        p = Path(str(file_path))
        try:
            with p.open("rb") as f:
                return f.read()
        except Exception:
            return b""

    def is_empty(self, file_path: PurePosixPath) -> bool:
        # Read bytes and use shared semantic emptiness check
        p = Path(str(file_path))
        if not p.is_file():
            return False
        try:
            blob = p.read_bytes()
        except Exception:
            return False
        if not blob.strip():
            return True
        from ..core import is_blob_semantically_empty
        return is_blob_semantically_empty(blob, file_path)
