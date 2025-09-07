import os
import shutil
import tempfile
from pathlib import Path
from typing import NamedTuple

import pytest

from tests.utils import touch_file, write_file


@pytest.fixture(scope="session", autouse=True)
def _ensure_github_token():
    if os.environ.get("GITHUB_TOKEN"):
        return
    token_path = Path.home() / ".github-token"
    try:
        token = token_path.read_text().strip()
    except Exception:
        token = ""
    if token:
        os.environ["GITHUB_TOKEN"] = token


class VFS(NamedTuple):
    root: Path
    paths: list[str]
    contents: dict[str, str]


@pytest.fixture(scope="session")
def fs_root(tmp_path_factory: pytest.TempPathFactory) -> VFS:
    """
    A session-cached fake filesystem tree for FS option tests.

    The tree includes examples for each filter category: tests, lock, binary, docs,
    hidden, cache/vendor/build, gitignored entry, empty/semantically-empty files, etc.
    """
    # Use a neutral temp directory name that won't be excluded by default rules
    # (avoid substrings like "test" or "tests"). Ensure cleanup after the session.
    root = Path(tempfile.mkdtemp(prefix="prinfs_"))

    # Root-level files
    write_file(root / "README.md", "# Root readme\n")
    write_file(root / "notes.rst", "Doc rst\n")
    write_file(root / "foo.py", "def foo():\n    return 1\n")

    # Empty and semantically empty
    touch_file(root / "empty.txt")  # truly empty
    touch_file(root / "empty.py")  # truly empty .py
    write_file(
        root / "semantically_empty.py",
        '"""Module docstring"""\nimport os\nfrom sys import version as _v\n__all__ = ["x"]\n',
    )

    # Binary-like and cache/hidden
    write_file(
        root / "image.png", "PNG"
    )  # trivial content, treated as text but matches binary exclude
    write_file(root / ".env", "SECRET=1\n")  # hidden file

    # .gitignore and a file it ignores
    write_file(root / ".gitignore", "gitignored.txt\n")
    write_file(root / "gitignored.txt", "should be ignored by default\n")

    # Common directories
    write_file(root / "src" / "app.py", "def app():\n    return 'ok'\n")
    write_file(root / "src" / "util.py", "def util():\n    pass\n")
    write_file(root / "src" / "data.json", '{"a":1}\n')

    write_file(root / "docs" / "readme.md", "# Docs\n")
    write_file(root / "docs" / "guide.rst", "RST content\n")

    write_file(root / "tests" / "test_mod.py", "def test_x():\n    assert True\n")
    write_file(root / "tests" / "spec.ts", "export {};\n")

    write_file(root / "node_modules" / "pkg" / "index.js", "console.log('x');\n")
    write_file(root / "build" / "artifact.o", "OBJ\n")
    write_file(root / "__pycache__" / "junk.pyc", "PYC\n")
    write_file(root / "cache" / "tmp.txt", "cache file\n")
    write_file(root / "vendor" / "vendorlib.py", "def v():\n    pass\n")
    write_file(root / "logs" / "app.log", "log entry\n")
    write_file(root / "secrets" / "key.pem", "KEY\n")

    write_file(root / "poetry.lock", "content\n")
    write_file(root / "package-lock.json", "{}\n")
    write_file(root / "uv.lock", "content\n")

    # Build a traversal-ordered list of file paths and a content mapping
    import os as _os

    rel_paths: list[str] = []
    contents: dict[str, str] = {}

    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        with _os.scandir(current) as it:
            dirs = []
            files = []
            for e in it:
                if e.is_dir(follow_symlinks=False):
                    dirs.append(e)
                elif e.is_file(follow_symlinks=False):
                    files.append(e)
            dirs.sort(key=lambda d: d.name.casefold())
            files.sort(key=lambda f: f.name.casefold())
            for d in reversed(dirs):
                stack.append(Path(d.path))
            for f in files:
                p = Path(f.path)
                rel = p.relative_to(root).as_posix()
                rel_paths.append(rel)
                try:
                    blob = p.read_bytes()
                    text = blob.decode("utf-8", errors="ignore")
                except Exception:
                    text = ""
                contents[rel] = text

    try:
        yield VFS(root=root, paths=rel_paths, contents=contents)
    finally:
        shutil.rmtree(root, ignore_errors=True)
