"""
Test the new what-then-where design pattern (pattern first, then path).
This follows fd's interface: fd [pattern] [path]
"""

from __future__ import annotations

from pathlib import Path

import pytest

from prin.adapters.filesystem import FileSystemSource
from prin.cli_common import Context
from tests.utils import write_file


def test_pattern_then_path_basic(prin_tmp_path: Path):
    """Test basic pattern-then-path: 'prin "*.py" .' lists all py files"""
    # Setup files
    write_file(prin_tmp_path / "src" / "main.py", "print('main')")
    write_file(prin_tmp_path / "src" / "util.py", "print('util')")
    write_file(prin_tmp_path / "src" / "readme.md", "# Readme")
    write_file(prin_tmp_path / "foo" / "foo_main.py", "print('foo')")
    write_file(prin_tmp_path / "tests" / "test_main.py", "print('test')")

    # The new design: pattern first, path second
    pattern = "*.py"
    search_path = str(prin_tmp_path)

    src = FileSystemSource(prin_tmp_path)
    src.configure(Context())

    # New interface: walk takes pattern and path separately
    # For now, test that we get the right files
    actual_entries = list(src.walk_pattern(pattern, search_path))

    actual_paths = {str(e.path) for e in actual_entries}
    # Should not include test_main.py from tests/ or readme.md because they are excluded by default
    assert actual_paths == {"src/main.py", "src/util.py", "foo/foo_main.py"}


def test_pattern_then_path_basic_with_path(prin_tmp_path: Path):
    """Test basic pattern-then-path: 'prin "*.py" src/' limits search to src/"""
    # Setup files
    write_file(prin_tmp_path / "src" / "main.py", "print('main')")
    write_file(prin_tmp_path / "src" / "util.py", "print('util')")
    write_file(prin_tmp_path / "src" / "readme.md", "# Readme")
    write_file(prin_tmp_path / "foo" / "foo_main.py", "print('foo')")
    write_file(prin_tmp_path / "tests" / "test_main.py", "print('test')")

    # The new design: pattern first, path second
    pattern = "*.py"
    search_path = str(prin_tmp_path / "src")

    src = FileSystemSource(prin_tmp_path)
    src.configure(Context())

    # New interface: walk takes pattern and path separately
    # For now, test that we get the right files
    actual_entries = list(src.walk_pattern(pattern, search_path))

    actual_paths = {str(e.path) for e in actual_entries}
    # Should not include test_main.py from tests/ or readme.md because they are excluded by default
    assert actual_paths == {"src/main.py", "src/util.py"}


def test_regex_pattern_then_path(prin_tmp_path: Path):
    r"""Test regex pattern: 'prin "foo_.*\.py$" .'"""
    write_file(prin_tmp_path / "test_unit.py", "print('unit test')")
    write_file(prin_tmp_path / "test_integration.py", "print('integration test')")
    write_file(prin_tmp_path / "main_test.py", "print('not matched')")
    write_file(prin_tmp_path / "src" / "test_helper.py", "print('helper')")
    write_file(prin_tmp_path / "src" / "foo_helper.py", "print('foo helper')")
    write_file(prin_tmp_path / "foo" / "foo_main.py", "print('foo')")

    pattern = r"test_.*\.py$"
    search_path = str(prin_tmp_path)

    # First, test that no files are matched by default
    src = FileSystemSource(prin_tmp_path)
    src.configure(Context())

    actual_entries = list(src.walk_pattern(pattern, search_path))
    assert not actual_entries  # all test files are excluded by default

    # Then, test that files are matched when include_tests is True
    src.configure(Context(include_tests=True))
    actual_entries = list(src.walk_pattern(pattern, search_path))
    actual_paths = {str(e.path) for e in actual_entries}

    assert actual_paths == {"test_unit.py", "test_integration.py", "src/test_helper.py"}


def test_no_pattern_lists_all_in_path(prin_tmp_path: Path):
    """When no pattern given, list all files in path: 'prin . ' or 'prin "" .'"""
    write_file(prin_tmp_path / "a.txt", "a")
    write_file(prin_tmp_path / "b.py", "b")
    write_file(prin_tmp_path / "sub" / "c.md", "c")

    src = FileSystemSource(prin_tmp_path)
    src.configure(Context())

    # Empty pattern means all files
    entries = list(src.walk_pattern("", str(prin_tmp_path)))
    actual_paths = {str(e.path) for e in entries}

    assert actual_paths == {"a.txt", "b.py", "sub/c.md"}


def test_pattern_no_path_searches_cwd(prin_tmp_path: Path):
    """When path not given, search current directory: 'prin "*.md"'"""
    # Change to tmp path as cwd
    import os

    old_cwd = Path.cwd()
    os.chdir(prin_tmp_path)

    try:
        write_file(prin_tmp_path / "README.md", "# Readme")
        write_file(prin_tmp_path / "docs" / "guide.md", "# Guide")
        write_file(prin_tmp_path / "src" / "code.py", "print('Code')")

        src = FileSystemSource()  # No anchor = cwd
        src.configure(Context())

        # Pattern without path = search cwd
        entries = list(src.walk_pattern("*.md", None))
        actual_paths = {str(e.path) for e in entries}

        assert actual_paths == {"README.md", "docs/guide.md"}
    finally:
        os.chdir(old_cwd)


def test_github_pattern_then_path():
    """Test GitHub URL with pattern: 'prin "*.rs" github.com/rust-lang/book'"""
    # This will be implemented when we update the GitHub adapter
    pytest.skip("GitHub adapter update pending")


def test_explicit_file_path_overrides_defaults(prin_tmp_path: Path):
    """Explicit file paths should override default exclusions: 'prin tests/test_main.py' prints tests/test_main.py"""
    write_file(prin_tmp_path / "tests" / "test_main.py", "print('test')")

    src = FileSystemSource(prin_tmp_path)
    src.configure(Context(include_tests=False))

    # When given an exact existing file, it should be treated as explicit
    actual_entries = list(src.walk_pattern(str(prin_tmp_path / "tests" / "test_main.py"), None))

    assert actual_entries
    assert actual_entries[0].explicit is True
    assert "tests/test_main.py" in str(actual_entries[0].path)
