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
    """Test basic pattern-then-path: 'prin "*.py" src/'"""
    # Setup files
    write_file(prin_tmp_path / "src" / "main.py", "print('main')")
    write_file(prin_tmp_path / "src" / "util.py", "print('util')")
    write_file(prin_tmp_path / "src" / "readme.md", "# Readme")
    write_file(prin_tmp_path / "tests" / "test_main.py", "# test")

    # The new design: pattern first, path second
    pattern = "*.py"
    search_path = str(prin_tmp_path / "src")

    src = FileSystemSource(prin_tmp_path)
    src.configure(Context())

    # New interface: walk takes pattern and path separately
    # For now, test that we get the right files
    entries = list(src.walk_pattern(pattern, search_path))

    paths = [str(e.path) for e in entries]
    assert len(paths) == 2
    assert "src/main.py" in paths[0]
    assert "src/util.py" in paths[1]
    # Should not include test_main.py from tests/ or readme.md


def test_regex_pattern_then_path(prin_tmp_path: Path):
    r"""Test regex pattern: 'prin "test_.*\.py$" .'"""
    write_file(prin_tmp_path / "test_unit.py", "# unit test")
    write_file(prin_tmp_path / "test_integration.py", "# integration test")
    write_file(prin_tmp_path / "main_test.py", "# not matched")
    write_file(prin_tmp_path / "src" / "test_helper.py", "# helper")

    pattern = r"test_.*\.py$"
    search_path = str(prin_tmp_path)

    src = FileSystemSource(prin_tmp_path)
    src.configure(Context())

    entries = list(src.walk_pattern(pattern, search_path))
    paths = [str(e.path) for e in entries]

    assert len(paths) == 3
    assert "test_unit.py" in " ".join(paths)
    assert "test_integration.py" in " ".join(paths)
    assert "src/test_helper.py" in " ".join(paths)
    assert "main_test.py" not in " ".join(paths)


def test_no_pattern_lists_all_in_path(prin_tmp_path: Path):
    """When no pattern given, list all files in path: 'prin . ' or 'prin "" .'"""
    write_file(prin_tmp_path / "a.txt", "a")
    write_file(prin_tmp_path / "b.py", "b")
    write_file(prin_tmp_path / "sub" / "c.md", "c")

    src = FileSystemSource(prin_tmp_path)
    src.configure(Context())

    # Empty pattern means all files
    entries = list(src.walk_pattern("", str(prin_tmp_path)))
    paths = [str(e.path) for e in entries]

    assert len(paths) == 3
    assert any("a.txt" in p for p in paths)
    assert any("b.py" in p for p in paths)
    assert any("sub/c.md" in p for p in paths)


def test_pattern_no_path_searches_cwd(prin_tmp_path: Path):
    """When path not given, search current directory: 'prin "*.md"'"""
    # Change to tmp path as cwd
    import os

    old_cwd = Path.cwd()
    os.chdir(prin_tmp_path)

    try:
        write_file(prin_tmp_path / "readme.md", "# Readme")
        write_file(prin_tmp_path / "docs" / "guide.md", "# Guide")
        write_file(prin_tmp_path / "src" / "code.py", "# Code")

        src = FileSystemSource()  # No anchor = cwd
        src.configure(Context())

        # Pattern without path = search cwd
        entries = list(src.walk_pattern("*.md", None))
        paths = [str(e.path) for e in entries]

        assert len(paths) == 2
        assert any("readme.md" in p for p in paths)
        assert any("docs/guide.md" in p for p in paths)
        assert not any("code.py" in p for p in paths)
    finally:
        os.chdir(old_cwd)


def test_github_pattern_then_path():
    """Test GitHub URL with pattern: 'prin "*.rs" github.com/rust-lang/book'"""
    # This will be implemented when we update the GitHub adapter
    pytest.skip("GitHub adapter update pending")


def test_explicit_file_path_still_works(prin_tmp_path: Path):
    """Explicit file paths should still work: 'prin exact_file.py'"""
    write_file(prin_tmp_path / "exact_file.py", "# exact")
    write_file(prin_tmp_path / "other.py", "# other")

    src = FileSystemSource(prin_tmp_path)
    src.configure(Context())

    # When given an exact existing file, it should be treated as explicit
    entries = list(src.walk_pattern(str(prin_tmp_path / "exact_file.py"), None))

    assert len(entries) == 1
    assert entries[0].explicit is True
    assert "exact_file.py" in str(entries[0].path)
