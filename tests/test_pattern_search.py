"""Test pattern searching functionality"""

from __future__ import annotations

from pathlib import Path

from prin.adapters.filesystem import FileSystemSource
from prin.cli_common import Context
from prin.core import DepthFirstPrinter, SourceAdapter, StringWriter
from prin.formatters import Formatter, XmlFormatter
from tests.utils import touch_file, write_file


def _run(
    source: SourceAdapter,
    pattern: str,
    search_path: str | None,
    formatter: Formatter = None,
    ctx: Context = None,
) -> str:
    buf = StringWriter()
    formatter = formatter or XmlFormatter()
    ctx = ctx or Context()

    source.configure(ctx)
    printer = DepthFirstPrinter(
        source,
        formatter,
        ctx=ctx,
    )
    printer.run_pattern(pattern, search_path, buf)
    return buf.text()


def test_search_specific_file_by_name(prin_tmp_path: Path):
    """Test searching for a specific file by name"""
    write_file(prin_tmp_path / "specific.py", "print('found me')\n")
    write_file(prin_tmp_path / "other.txt", "other content\n")

    out = _run(FileSystemSource(prin_tmp_path), "specific.py", str(prin_tmp_path))
    assert f"<{(prin_tmp_path / 'specific.py').resolve()}>" in out
    assert "other.txt" not in out


def test_search_in_subdirectory(prin_tmp_path: Path):
    """Test searching within a specific subdirectory"""
    write_file(prin_tmp_path / "dirA" / "a.py", "print('dirA/a.py')\n")
    write_file(prin_tmp_path / "dirB" / "b.md", "# dirB/b.md\n")
    write_file(prin_tmp_path / "c.py", "print('root c.py')\n")

    # Search for .py files only in dirA
    out = _run(FileSystemSource(prin_tmp_path), "*.py", str(prin_tmp_path / "dirA"))
    # When searching in dirA subdirectory, the path is shown relative to the search path (absolute because where is absolute)
    assert f"<{(prin_tmp_path / 'dirA' / 'a.py').resolve()}>" in out
    assert "b.md" not in out
    assert "c.py" not in out


def test_glob_pattern_search(prin_tmp_path: Path):
    """Test glob pattern searching"""
    write_file(prin_tmp_path / "src" / "main.py", "print('main')")
    write_file(prin_tmp_path / "src" / "util.py", "print('util')")
    write_file(prin_tmp_path / "docs" / "readme.md", "# readme")

    # Search for all .py files
    out = _run(FileSystemSource(prin_tmp_path), "**/*.py", str(prin_tmp_path))
    print(f"Glob output: {out}")
    assert f"<{(prin_tmp_path / 'src' / 'main.py').resolve()}>" in out
    assert f"<{(prin_tmp_path / 'src' / 'util.py').resolve()}>" in out
    assert "readme.md" not in out


def test_regex_pattern_search(prin_tmp_path: Path):
    """Test regex pattern searching"""
    write_file(prin_tmp_path / "test_unit.py", "print('unit tests')")
    write_file(prin_tmp_path / "test_integration.py", "print('integration tests')")
    write_file(prin_tmp_path / "main_test.py", "print('not matched')")
    write_file(prin_tmp_path / "main.py", "print('main')")

    # Search for files starting with 'test_' or 'test'
    out = _run(
        FileSystemSource(prin_tmp_path),
        r"test_?.*\.py$",
        str(prin_tmp_path),
        ctx=Context(include_tests=False),
    )
    assert f"<{(prin_tmp_path / 'test_unit.py').resolve()}>" not in out
    assert f"<{(prin_tmp_path / 'test_integration.py').resolve()}>" not in out
    assert "main_test.py" in out
    assert "main.py" not in out


def test_empty_pattern_lists_all(prin_tmp_path: Path):
    """Test that empty pattern lists all files"""
    write_file(prin_tmp_path / "a.py", "print('a')")
    write_file(prin_tmp_path / "b.md", "# b")
    write_file(prin_tmp_path / "sub" / "c.txt", "content c")

    out = _run(FileSystemSource(prin_tmp_path), "", str(prin_tmp_path))
    assert f"<{(prin_tmp_path / 'a.py').resolve()}>" in out
    assert f"<{(prin_tmp_path / 'b.md').resolve()}>" in out
    assert f"<{(prin_tmp_path / 'sub' / 'c.txt').resolve()}>" in out


def test_search_with_exclusions(prin_tmp_path: Path):
    """Test that default exclusions still apply during pattern search"""
    write_file(prin_tmp_path / "keep.py", "print('keep')\n")
    touch_file(prin_tmp_path / "junk.pyc")
    write_file(prin_tmp_path / "src" / "test_something.py", "print('test')")

    # Search for all files - binary files should be excluded by default
    ctx = Context(include_binary=False)
    out = _run(FileSystemSource(prin_tmp_path), "", str(prin_tmp_path), ctx=ctx)
    assert f"<{(prin_tmp_path / 'keep.py').resolve()}>" in out
    assert "junk.pyc" not in out
    # test files excluded by default (matches /test_*.py pattern)
    assert "test_something.py" not in out
