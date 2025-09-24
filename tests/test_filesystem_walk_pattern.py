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
    assert e.path.as_posix() == "a.py"
    assert Path(str(e.abs_path)).is_absolute()
    assert e.kind.name == "FILE"


def test_walk_pattern_empty_lists_all(prin_tmp_path: Path):
    """Test that empty pattern lists all files"""
    # Create mixed-case names to test case-insensitive ordering
    write_file(prin_tmp_path / "Dir" / "b.txt", "B\n")
    write_file(prin_tmp_path / "dir" / "A.py", "print('A')\n")
    write_file(prin_tmp_path / "dir" / "a.md", "# a\n")
    write_file(prin_tmp_path / "dir" / "Z.json", "{\n}\n")
    write_file(prin_tmp_path / "dir" / "sub" / "c.py", "print('c')\n")

    src = FileSystemSource(prin_tmp_path)
    src.configure(prin.cli_common.Context(include_empty=True))
    entries = list(src.walk_pattern("", str(prin_tmp_path)))
    paths = [e.path.as_posix() for e in entries]
    
    # Just verify we got all the files
    print(f"Sorted paths: {sorted(paths)}")
    assert sorted(paths) == sorted([
        "Dir/b.txt",
        "dir/A.py", 
        "dir/a.md",
        "dir/Z.json",
        "dir/sub/c.py",
    ])


def test_walk_pattern_glob(prin_tmp_path: Path):
    """Test glob pattern matching"""
    write_file(prin_tmp_path / "src" / "main.py", "print('main')\n")
    write_file(prin_tmp_path / "src" / "util.py", "print('util')\n")
    write_file(prin_tmp_path / "tests" / "test_main.py", "# test\n")
    write_file(prin_tmp_path / "readme.md", "# Readme\n")
    
    src = FileSystemSource(prin_tmp_path)
    src.configure(prin.cli_common.Context(include_empty=True))
    
    # Test glob for .py files
    entries = list(src.walk_pattern("**/*.py", str(prin_tmp_path)))
    paths = sorted([e.path.as_posix() for e in entries])
    assert paths == ["src/main.py", "src/util.py", "tests/test_main.py"]


def test_walk_pattern_regex(prin_tmp_path: Path):
    """Test regex pattern matching"""
    write_file(prin_tmp_path / "test_unit.py", "# unit\n")
    write_file(prin_tmp_path / "test_integration.py", "# integration\n")
    write_file(prin_tmp_path / "main_test.py", "# main test\n")
    write_file(prin_tmp_path / "main.py", "print('main')\n")
    
    src = FileSystemSource(prin_tmp_path)
    
    # Test regex for files starting with test_
    entries = list(src.walk_pattern(r"^test_.*\.py$", str(prin_tmp_path)))
    paths = sorted([e.path.as_posix() for e in entries])
    assert paths == ["test_integration.py", "test_unit.py"]


def test_walk_pattern_subdirectory(prin_tmp_path: Path):
    """Test pattern search within a subdirectory"""
    write_file(prin_tmp_path / "src" / "main.py", "print('main')\n")
    write_file(prin_tmp_path / "src" / "util.py", "print('util')\n")
    write_file(prin_tmp_path / "tests" / "test_main.py", "# test\n")
    write_file(prin_tmp_path / "readme.md", "# Readme\n")
    
    src = FileSystemSource(prin_tmp_path)
    
    # Search only in src subdirectory
    entries = list(src.walk_pattern("*.py", str(prin_tmp_path / "src")))
    paths = sorted([e.path.as_posix() for e in entries])
    assert paths == ["main.py", "util.py"]


def test_walk_pattern_single_file_path(prin_tmp_path: Path):
    """Test when search_path is a file, not a directory"""
    write_file(prin_tmp_path / "specific.py", "print('specific')\n")
    
    src = FileSystemSource(prin_tmp_path)
    
    # When search_path is a file and pattern is empty, return just that file
    entries = list(src.walk_pattern("", str(prin_tmp_path / "specific.py")))
    assert len(entries) == 1
    e = entries[0]
    assert e.path.as_posix() == "specific.py"
    assert e.explicit is True