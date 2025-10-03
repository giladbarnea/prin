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
    paths: list[str]
    contents: dict[str, str]
    regular_files: dict[str, str]
    doc_files: dict[str, str]
    empty_files: dict[str, str]
    binary_files: dict[str, str]
    hidden_files: dict[str, str]
    test_files: dict[str, str]
    build_dependency_files: dict[str, str]
    dependency_spec_files: dict[str, str]
    stylesheet_files: dict[str, str]
    script_files: dict[str, str]
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
    hidden, cache/vendor/build, empty/semantically-empty files, etc.

    As a continuous maintenance responsibility, any inevitable gap between the DEFAULT_* consts and the actual tree should be filled in. Consequently, tests that assert hardcoded assumed paths should be updated accordingly.
    """
    # Use a neutral temp directory name that won't be excluded by default rules
    # (avoid substrings like "test" or "tests"). Ensure cleanup after the session.
    # Ensure unique non-empty contents across files to avoid incidental substring collisions
    root = Path(tempfile.mkdtemp(prefix="prinfs_"))

    # Regular files are included by default, regardless of whether they fit one of the (non-exclusion) categories.
    regular_files: dict[str, str] = {
        "README.md": "# Root readme\n",
        "notes.rst": "Doc rst\n",
        "foo.py": "def foo():\n    return 1\n",
        "src/app.py": "def app():\n    return 'ok'\n",
        "src/util.py": "def util():\n    pass\n",
        "src/data.json": '{"a":1}\n',
        "install.sh": "echo 'install'\n",
        "app/testing/assess_students.py": "def assess_students():\n    ...\n",  # Should be included.
        # This is a regular code file under docs/, not a docs file by extension
        "docs/build.py": "def build_docs():\n    ...\n",
        # "gitignored.txt": "should be ignored by default\n",
    }
    doc_files: dict[str, str] = {
        "docs/readme.md": "# Docs\n",
        "docs/guide.rst": "RST content\n",
        "CONTRIBUTING.md": "# Contributing\n",
        "foo/share/man/man1/foo.1": "foo(1)\n",
    }

    empty_files: dict[str, str] = {
        "empty.txt": "",
        "empty.py": "",
        "semantically_empty.py": '"""Module docstring"""\n# a comment line\nimport os\nfrom sys import version as _v\n__all__ = ["x"]\n',
        "regular_dirname/empty.txt": "",
        "regular_dirname/empty.py": "",
        "regular_dirname/semantically_empty.py": '"""Module docstring2"""\n# a comment line\nimport os\nfrom sys import version as _v\n__all__ = ["x"]\n',
    }

    binary_files: dict[str, str] = {
        "image.png": "PNG",
        "something/bin/python": "PYTHON\n",  # Should be excluded because of the bin/ dir.
    }

    hidden_files: dict[str, str] = {
        ".env": "SECRET=1\n",
        # ".gitignore": "gitignored.txt\n",
        ".venv/something": "SOMETHING\n",
        # represent hidden directories via a file inside them (we print files only)
        ".github/config": "GITHUB\n",
        "app/submodule/.git/config": "GIT\n",
    }
    test_files: dict[str, str] = {
        "tests/test_mod.py": "def test_x():\n    assert True\n",
        "tests/spec.ts": "it('should pass', () => { expect(1).toBe(1); });\n",
        "app/test_mod.py": "def test_mod():\n    assert True\n",
        "app/mod.test.py": "def mod_test():\n    assert True\n",
        "tests/howto.txt": "How to run tests\n",  # Should be excluded because the tests/ dir.
    }
    build_dependency_files: dict[str, str] = {
        "node_modules/pkg/index.js": "console.log('x');\n",
        ".venv/lib/python3.13/site-packages/decorator.py": "POS = inspect.Parameter.POSITIONAL_OR_KEYWORD\n",
    }
    dependency_spec_files: dict[str, str] = {
        "package.json": '{"name": "test-pkg", "version": "1.0.0"}\n',
        "pyproject.toml": '[project]\nname = "test-project"\n',
        "requirements.txt": "requests==2.31.0\n",
        "requirements-dev.txt": "pytest==8.0.0\n",
        "pom.xml": '<?xml version="1.0"?>\n<project></project>\n',
        "build.gradle": 'plugins { id "java" }\n',
        "Cargo.toml": '[package]\nname = "test"\n',
        "go.mod": "module example.com/test\n",
        "Gemfile": 'source "https://rubygems.org"\n',
        "composer.json": '{"name": "test/pkg"}\n',
        "Podfile": 'platform :ios, "14.0"\n',
        "pubspec.yaml": "name: test_app\n",
    }
    stylesheet_files: dict[str, str] = {
        "assets/styles/main.css": "body { color: red; }\n",
        "assets/styles/theme.scss": "$primary: #00f;\n",
        "assets/styles/legacy.sass": "body\n  color: #0f0\n",
        "assets/styles/vars.less": "@primary: #333;\n",
        "assets/styles/editor.styl": "body\n  color #fff\n",
        "assets/styles/layout.stylus": "body\n  background #000\n",
        "assets/styles/custom.pcss": ":root {\n  --gap: 1rem;\n}\n",
        "assets/styles/postcss.postcss": ":root {\n  --font: 'Inter';\n}\n",
        "assets/styles/sugar.sss": ":root\n  color: #123\n",
    }
    script_files: dict[str, str] = {
        "scripts/deploy.sh": "#!/usr/bin/env bash\necho 'deploy'\n",
        "scripts/setup.ps1": "Write-Host 'setup'\n",
        "scripts/windows/install.bat": "@echo off\necho install\n",
        "tools/run.nu": "echo 'nu script'\n",
    }
    artifact_files: dict[str, str] = {
        "build/artifact.o": "OBJ\n",
        "dist/regular.js": "console.log('dist/regular.js');\n",  # Should be excluded because of the dist/ dir.
        "regular_dirname/foo.min.js": "console.log('regular_dirname/foo.min.js');\n",  # Should be excluded because of *.min.js extension.
        "vendor/vendorlib.py": "def vendorlib():\n    pass\n",
    }
    cache_files: dict[str, str] = {
        "__pycache__/DIR.TAG": "Signature: 8a477f597d28d172799f06886806bc55\n",
        ".ruff_cache/DIR.TAG": "Signature: 8a477f597d28d172899f06886806bc55\n",
        "regular_dirname/cached.txt": "cache file\n",
    }
    log_files: dict[str, str] = {
        "debug/app.log": "log entry\n",
        "logs/app.txt": "log entry2\n",
    }
    secret_files: dict[str, str] = {
        "secrets/key.pem": "KEY1\n",
        "key.pem": "KEY2\n",
    }
    lock_files: dict[str, str] = {
        "poetry.lock": "poetry-lock-content-unique\n",
        "package-lock.json": '{\n  "name": "unique-package-lock"\n}\n',
        "uv.lock": "uv-lock-content-unique\n",
    }
    # Ensure all keys (file paths) are unique across all dictionaries
    all_dicts = [
        regular_files,
        doc_files,
        empty_files,
        binary_files,
        hidden_files,
        test_files,
        build_dependency_files,
        dependency_spec_files,
        stylesheet_files,
        script_files,
        artifact_files,
        cache_files,
        log_files,
        secret_files,
        lock_files,
    ]
    all_keys = [key for d in all_dicts for key, value in d.items() if value]
    assert sorted(all_keys) == sorted(list(set(all_keys))), "Not all keys are unique"

    # Ensure all values (file contents) are unique across all dictionaries
    all_values = [value for d in all_dicts for value in d.values() if value]
    assert sorted(all_values) == sorted(list(set(all_values))), "Not all values are unique"

    all_files = {
        **regular_files,
        **doc_files,
        **empty_files,
        **binary_files,
        **hidden_files,
        **test_files,
        **build_dependency_files,
        **dependency_spec_files,
        **stylesheet_files,
        **script_files,
        **artifact_files,
        **cache_files,
        **log_files,
        **secret_files,
        **lock_files,
    }

    for regular_file, content in all_files.items():
        write_file(root / regular_file, content)

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
            build_dependency_files=build_dependency_files,
            dependency_spec_files=dependency_spec_files,
            stylesheet_files=stylesheet_files,
            script_files=script_files,
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
    temp_dir = Path(tempfile.mkdtemp(prefix="prin.")).resolve()
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
