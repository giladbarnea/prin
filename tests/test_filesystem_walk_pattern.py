"""Test FileSystemSource.walk_pattern functionality"""

from pathlib import Path

import prin.cli_common
from prin.adapters.filesystem import FileSystemSource
from tests.utils import write_file


def test_walk_pattern_specific_file(prin_tmp_path: Path):
    """Test searching for a specific file by name"""
    write_file(prin_tmp_path / "a.py", "print('a')\n")
    write_file(prin_tmp_path / "b.py", "print('b')\n")

    src = FileSystemSource(prin_tmp_path)
    entries = list(src.walk_pattern("a.py", str(prin_tmp_path)))
    assert len(entries) == 1
    e = entries[0]
    # Absolute where token → display absolute
    assert e.path.as_posix() == str((prin_tmp_path / "a.py").resolve())
    assert Path(str(e.abs_path)).is_absolute()
    assert e.kind.name == "FILE"


def test_walk_pattern_glob(prin_tmp_path: Path):
    """Test glob pattern matching"""
    write_file(prin_tmp_path / "src" / "main.py", "print('main')\n")
    write_file(prin_tmp_path / "src" / "util.py", "print('util')\n")
    write_file(prin_tmp_path / "tests" / "test_main.py", "print('test')\n")
    write_file(prin_tmp_path / "readme.md", "# Readme\n")

    src = FileSystemSource(prin_tmp_path)
    src.configure(prin.cli_common.Context(include_tests=True))

    # Test glob for .py files
    entries = list(src.walk_pattern("**/*.py", str(prin_tmp_path)))
    expected_paths = {e.path.as_posix() for e in entries}
    assert expected_paths == {
        str((prin_tmp_path / "src" / "main.py").resolve()),
        str((prin_tmp_path / "src" / "util.py").resolve()),
        str((prin_tmp_path / "tests" / "test_main.py").resolve()),
    }


def test_walk_pattern_regex(prin_tmp_path: Path):
    """Test regex pattern matching"""
    write_file(prin_tmp_path / "test_unit.py", "print('unit')\n")
    write_file(prin_tmp_path / "test_integration.py", "print('integration')\n")
    write_file(prin_tmp_path / "main_test.py", "print('main test')\n")
    write_file(prin_tmp_path / "main.py", "print('main')\n")

    src = FileSystemSource(prin_tmp_path)

    # Test regex for files starting with test_
    entries = list(src.walk_pattern(r"^test_.*\.py$", str(prin_tmp_path)))
    paths = sorted([e.path.as_posix() for e in entries])
    assert paths == [
        str((prin_tmp_path / "test_integration.py").resolve()),
        str((prin_tmp_path / "test_unit.py").resolve()),
    ]


def test_walk_pattern_subdirectory(prin_tmp_path: Path):
    """Test pattern search within a subdirectory"""
    write_file(prin_tmp_path / "src" / "main.py", "print('main')\n")
    write_file(prin_tmp_path / "src" / "util.py", "print('util')\n")
    write_file(prin_tmp_path / "tests" / "test_main.py", "print('test')\n")
    write_file(prin_tmp_path / "readme.md", "# Readme\n")

    src = FileSystemSource(prin_tmp_path)

    # Search only in src subdirectory
    entries = list(src.walk_pattern("*.py", str(prin_tmp_path / "src")))
    paths = sorted([e.path.as_posix() for e in entries])
    assert paths == [
        str((prin_tmp_path / "src" / "main.py").resolve()),
        str((prin_tmp_path / "src" / "util.py").resolve()),
    ]


def test_walk_pattern_single_file_path(prin_tmp_path: Path):
    """Test when search_path is a file, not a directory"""
    write_file(prin_tmp_path / "specific.py", "print('specific')\n")

    src = FileSystemSource(prin_tmp_path)

    # When search_path is a file and pattern is empty, return just that file
    entries = list(src.walk_pattern("", str(prin_tmp_path / "specific.py")))
    assert len(entries) == 1
    e = entries[0]
    assert e.path.as_posix() == str((prin_tmp_path / "specific.py").resolve())
    assert e.explicit is True
