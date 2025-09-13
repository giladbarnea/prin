import os
import shutil
import tempfile
import warnings
from pathlib import Path
from typing import NamedTuple

import pytest

from tests.utils import write_file


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
    paths: list[Path]
    contents: dict[Path, str]
    regular_files: dict[str, str]
    doc_files: dict[str, str]
    empty_files: dict[str, str]
    binary_files: dict[str, str]
    hidden_files: dict[str, str]
    test_files: dict[str, str]
    dependency_files: dict[str, str]
    artifact_files: dict[str, str]
    cache_files: dict[str, str]
    log_files: dict[str, str]
    secret_files: dict[str, str]
    lock_files: dict[str, str]


@pytest.fixture(scope="session")
def fs_root() -> VFS:
    """
    A session-cached fake filesystem tree for FS option tests.

    The tree includes examples for each filter category (as defined in the DEFAULT_* consts in defaults.py): tests, lock, binary, docs,
    hidden, cache/vendor/build, gitignored entry, empty/semantically-empty files, etc.

    As a continuous maintenance responsibility, any inevitable gap between the DEFAULT_* consts and the actual tree should be filled in. Consequently, tests that assert hardcoded assumed paths should be updated accordingly.
    """
    # Use a neutral temp directory name that won't be excluded by default rules
    # (avoid substrings like "test" or "tests"). Ensure cleanup after the session.
    # Ensure unique non-empty contents across files to avoid incidental substring collisions
    root = Path(tempfile.mkdtemp(prefix="prinfs_"))

    regular_files: dict[Path, str] = {
        "README.md": "# Root readme\n",
        "notes.rst": "Doc rst\n",
        "foo.py": "def foo():\n    return 1\n",
        "src/app.py": "def app():\n    return 'ok'\n",
        "src/util.py": "def util():\n    pass\n",
        "src/data.json": '{"a":1}\n',
        "gitignored.txt": "should be ignored by default\n",
    }
    doc_files: dict[Path, str] = {
        "docs/readme.md": "# Docs\n",
        "docs/guide.rst": "RST content\n",
    }

    empty_files: dict[Path, str] = {
        "empty.txt": "",
        "empty.py": "",
        "semantically_empty.py": '"""Module docstring"""\n# a comment line\nimport os\nfrom sys import version as _v\n__all__ = ["x"]\n',
    }

    binary_files: dict[Path, str] = {
        "image.png": "PNG",
    }

    hidden_files: dict[Path, str] = {
        ".env": "SECRET=1\n",
        ".gitignore": "gitignored.txt\n",
        # ".venv/something": "SOMETHING\n",  # This makes the tests fail (it should work)
    }
    test_files: dict[Path, str] = {
        "tests/test_mod.py": "def test_x():\n    assert True\n",
        "tests/spec.ts": "it('should pass', () => { expect(1).toBe(1); });\n",
        "app/test_mod.py": "def test_x():\n    assert True\n",
        "app/mod.test.py": "def test_x():\n    assert True\n",
    }
    dependency_files: dict[Path, str] = {
        "node_modules/pkg/index.js": "console.log('x');\n",
    }
    artifact_files: dict[Path, str] = {
        "build/artifact.o": "OBJ\n",
        "cache/tmp.txt": "cache file\n",
        "vendor/vendorlib.py": "def v():\n    pass\n",
    }
    cache_files: dict[Path, str] = {
        "__pycache__/junk.pyc": "PYC\n",
    }
    log_files: dict[Path, str] = {
        "logs/app.log": "log entry\n",
    }
    secret_files: dict[Path, str] = {
        "secrets/key.pem": "KEY\n",
    }
    lock_files: dict[Path, str] = {
        "poetry.lock": "poetry-lock-content-unique\n",
        "package-lock.json": '{\n  "name": "unique-package-lock"\n}\n',
        "uv.lock": "uv-lock-content-unique\n",
    }
    for regular_file, content in regular_files.items():
        write_file(root / regular_file, content)
    for doc_file, content in doc_files.items():
        write_file(root / doc_file, content)
    for empty_file, content in empty_files.items():
        write_file(root / empty_file, content)
    for binary_file, content in binary_files.items():
        write_file(root / binary_file, content)
    for hidden_file, content in hidden_files.items():
        write_file(root / hidden_file, content)
    for test_file, content in test_files.items():
        write_file(root / test_file, content)
    for dependency_file, content in dependency_files.items():
        write_file(root / dependency_file, content)
    for artifact_file, content in artifact_files.items():
        write_file(root / artifact_file, content)
    for cache_file, content in cache_files.items():
        write_file(root / cache_file, content)
    for log_file, content in log_files.items():
        write_file(root / log_file, content)
    for secret_file, content in secret_files.items():
        write_file(root / secret_file, content)
    for lock_file, content in lock_files.items():
        write_file(root / lock_file, content)

    # Build a traversal-ordered list of file paths and a content mapping
    rel_paths: list[str] = []
    contents: dict[str, str] = {}

    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        with os.scandir(current) as it:
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
        yield VFS(
            root=root,
            paths=rel_paths,
            contents=contents,
            regular_files=regular_files,
            doc_files=doc_files,
            empty_files=empty_files,
            binary_files=binary_files,
            hidden_files=hidden_files,
            test_files=test_files,
            dependency_files=dependency_files,
            artifact_files=artifact_files,
            cache_files=cache_files,
            log_files=log_files,
            secret_files=secret_files,
            lock_files=lock_files,
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def prin_tmp_path():
    """Create a temporary directory with 'prin' prefix, avoiding test-related substrings."""
    import shutil
    import tempfile

    # Equivalent to `mktemp -t prin` - creates temp dir with 'prin' prefix
    temp_dir = Path(tempfile.mkdtemp(prefix="prin."))
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def pytest_addoption(parser):
    parser.addoption(
        "--no-network",
        action="store_true",
        default=False,
        help="Skip tests that require network access (marked with @pytest.mark.network)",
    )
    parser.addoption(
        "--website",
        action="store_true",
        default=False,
        help="Run only tests targeting the website adapter",
    )
    parser.addoption(
        "--no-website",
        action="store_true",
        default=False,
        help="Skip tests targeting the website adapter",
    )
    parser.addoption(
        "--repo",
        action="store_true",
        default=False,
        help="Run only tests targeting repository (GitHub) adapter",
    )
    parser.addoption(
        "--no-repo",
        action="store_true",
        default=False,
        help="Skip tests targeting repository (GitHub) adapter",
    )


def pytest_configure(config):
    # Redundant with pyproject markers, but safe if running in isolation
    config.addinivalue_line("markers", "network: tests that require network access")
    config.addinivalue_line("markers", "website: tests that target website adapter")
    config.addinivalue_line("markers", "repo: tests that target repository adapter")


def pytest_collection_modifyitems(config, items):
    # Handle network skipping first
    if config.getoption("--no-network"):
        skip_network = pytest.mark.skip(reason="network disabled via --no-network")
        for item in items:
            if "network" in item.keywords:
                item.add_marker(skip_network)

    # Apply adapter-based filtering if requested
    want_website = config.getoption("--website")
    want_repo = config.getoption("--repo")
    no_website = config.getoption("--no-website")
    no_repo = config.getoption("--no-repo")

    # If no include/exclude flags are provided, do nothing
    if not (want_website or want_repo or no_website or no_repo):
        return

    skip_filtered_includes = pytest.mark.skip(reason="filtered by --website/--repo")
    skip_filtered_excludes = pytest.mark.skip(reason="disabled by --no-website/--no-repo")

    for item in items:
        # Prefer explicit markers when present; fall back to filename heuristics if none
        has_website_marker = "website" in item.keywords
        has_repo_marker = "repo" in item.keywords or "github" in item.keywords

        if has_website_marker or has_repo_marker:
            is_website = has_website_marker
            is_repo = has_repo_marker
        else:
            nodeid = item.nodeid.lower()
            is_website = "website" in nodeid
            is_repo = ("repo" in nodeid) or ("github" in nodeid)
            if is_website or is_repo:
                warnings.warn(
                    f"Test selected by name-based fallback; please add an explicit marker: {item.nodeid}",
                    UserWarning,
                )

        # Inclusion mode has precedence when specified
        if want_website or want_repo:
            keep = (want_website and is_website) or (want_repo and is_repo)
            if not keep:
                item.add_marker(skip_filtered_includes)
            continue

        # Otherwise apply exclusion-only mode
        should_skip = (no_website and is_website) or (no_repo and is_repo)
        if should_skip:
            item.add_marker(skip_filtered_excludes)
