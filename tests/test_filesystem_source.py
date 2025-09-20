import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest

from prin.adapters.filesystem import FileSystemSource
from tests.utils import write_file


def test_is_empty_returns_true_for_semantically_empty_python_file(prin_tmp_path: Path):
    content = textwrap.dedent("""
	#!/usr/bin/env python
	from foo import bar
	import baz
	import qux.blabla
	
	# Define the __all__ variable
	__all__ = ["bar", "baz", "qux"]
	""")
    write_file(prin_tmp_path / "empty_python_file.py", content)
    fs_source = FileSystemSource(prin_tmp_path)
    actual_is_empty = fs_source.is_empty(prin_tmp_path / "empty_python_file.py")
    assert actual_is_empty


def test_is_empty_returns_false_for_non_empty_python_file(prin_tmp_path: Path):
    write_file(prin_tmp_path / "non_empty_python_file.py", "print('non_empty_python_file.py')\n")
    fs_source = FileSystemSource(prin_tmp_path)
    actual_is_empty = fs_source.is_empty(prin_tmp_path / "non_empty_python_file.py")
    assert not actual_is_empty


def test_is_empty_returns_true_for_truly_empty_text_file(prin_tmp_path: Path):
    write_file(prin_tmp_path / "empty_text_file.txt", "")
    fs_source = FileSystemSource(prin_tmp_path)
    actual_is_empty = fs_source.is_empty(prin_tmp_path / "empty_text_file.txt")
    assert actual_is_empty


def test_is_empty_returns_false_for_non_empty_text_file_with_python_syntax(prin_tmp_path: Path):
    python_comment = "# This looks like a python comment\n"
    write_file(prin_tmp_path / "python_comment.md", python_comment)
    fs_source = FileSystemSource(prin_tmp_path)
    actual_is_empty = fs_source.is_empty(prin_tmp_path / "python_comment.md")
    assert not actual_is_empty


@dataclass(frozen=True)
class _Tree:
    anchor: str
    inside_directory_relative: str
    inside_directory_relative_dots: str
    inside_directory_absolute: str
    inside_file_relative: str
    inside_file_relative_dots: str
    inside_file_absolute: str
    missing_inside_dir_relative: str
    missing_inside_dir_relative_dots: str
    outside_dir_relative: str
    outside_dir_absolute: str
    outside_file_relative: str
    outside_file_absolute: str

    def __getitem__(self, key: str) -> str:
        return self.__getattribute__(key)


def _setup_tree(anchor: Path) -> _Tree:
    tmp_dir1 = anchor / "dir1"
    tmp_file1 = anchor / "file1.txt"
    tmp_dir1.mkdir(parents=True, exist_ok=True)
    write_file(tmp_file1, "file1.txt hello\n")
    outside_dir = anchor.parent / "outside_dir"
    outside_dir.mkdir(parents=True, exist_ok=True)
    outside_file = outside_dir / "outside_file.txt"
    write_file(outside_file, "outside_file.txt hello\n")
    inside_empty_file = anchor / "empty_file.txt"
    write_file(inside_empty_file, "")
    outside_empty_file = outside_dir / "empty_file.txt"
    write_file(outside_empty_file, "")

    return _Tree(
        anchor=str(anchor),
        inside_directory_relative="dir1",
        inside_directory_relative_dots="./dir1",
        inside_directory_absolute=str(tmp_dir1),
        inside_file_relative="file1.txt",
        inside_file_relative_dots="./file1.txt",
        inside_file_absolute=str(tmp_file1),
        missing_inside_dir_relative="missing_dir",
        missing_inside_dir_relative_dots="./missing_dir",
        outside_dir_relative="../outside_dir",
        outside_dir_absolute=str(outside_dir),
        outside_file_relative="../outside_dir/outside_file.txt",
        outside_file_absolute=str(outside_file),
    )


@pytest.mark.parametrize(
    ("case_key", "expect"),
    [
        ("inside_directory_relative", "dir1"),
        ("inside_directory_relative_dots", "./dir1"),
        ("inside_directory_absolute", "{anchor}/dir1"),
        ("inside_file_relative", "file1.txt"),
        ("inside_file_relative_dots", "./file1.txt"),
        ("inside_file_absolute", "{anchor}/file1.txt"),
        ("missing_inside_dir_relative", "missing_dir"),
        ("missing_inside_dir_relative_dots", "./missing_dir"),
        ("outside_dir_relative", "../outside_dir"),
        ("outside_dir_absolute", "{outside_dir}"),
        ("outside_file_relative", "../outside_dir/outside_file.txt"),
        ("outside_file_absolute", "{outside_dir}/outside_file.txt"),
    ],
)
def test_resolve_display(prin_tmp_path: Path, case_key: str, expect):
    fs = FileSystemSource(prin_tmp_path)
    tree: _Tree = _setup_tree(prin_tmp_path)
    path = tree[case_key]
    expect = expect.format(anchor=tree.anchor, outside_dir=tree.outside_dir_absolute)
    resolved = fs.resolve_display(path)
    assert resolved == expect


@pytest.mark.parametrize(
    ("case_key", "expect"),
    [
        ("inside_directory_relative", "{anchor}/dir1"),
        ("inside_directory_relative_dots", "{anchor}/dir1"),
        ("inside_directory_absolute", "{anchor}/dir1"),
        ("inside_file_relative", "{anchor}/file1.txt"),
        ("inside_file_relative_dots", "{anchor}/file1.txt"),
        ("inside_file_absolute", "{anchor}/file1.txt"),
        ("missing_inside_dir_relative", "{anchor}/missing_dir"),
        ("missing_inside_dir_relative_dots", "{anchor}/missing_dir"),
        ("outside_dir_relative", "{outside_dir}"),
        ("outside_dir_absolute", "{outside_dir}"),
        ("outside_file_relative", "{outside_dir}/outside_file.txt"),
        ("outside_file_absolute", "{outside_dir}/outside_file.txt"),
    ],
)
def test_resolve(prin_tmp_path: Path, case_key: str, expect):
    fs = FileSystemSource(prin_tmp_path)
    tree: _Tree = _setup_tree(prin_tmp_path)
    path = tree[case_key]
    expect = expect.format(anchor=tree.anchor, outside_dir=tree.outside_dir_absolute)
    resolved = fs.resolve(path)
    assert resolved == Path(expect)


@pytest.mark.parametrize(
    ("case_key", "expect"),
    [
        ("inside_directory_relative", IsADirectoryError),
        ("inside_directory_relative_dots", IsADirectoryError),
        ("inside_directory_absolute", IsADirectoryError),
        ("inside_file_relative", b"file1.txt hello\n"),
        ("inside_file_relative_dots", b"file1.txt hello\n"),
        ("inside_file_absolute", b"file1.txt hello\n"),
        ("missing_inside_dir_relative", FileNotFoundError),
        ("missing_inside_dir_relative_dots", FileNotFoundError),
        ("outside_dir_relative", IsADirectoryError),
        ("outside_dir_absolute", IsADirectoryError),
        ("outside_file_relative", b"outside_file.txt hello\n"),
        ("outside_file_absolute", b"outside_file.txt hello\n"),
    ],
)
def test_read_file_bytes(prin_tmp_path: Path, case_key: str, expect):
    fs = FileSystemSource(prin_tmp_path)
    tree: _Tree = _setup_tree(prin_tmp_path)
    path = tree[case_key]
    if isinstance(expect, type) and issubclass(expect, Exception):
        with pytest.raises(expect):
            fs.read_file_bytes(path)
    else:
        resolved = fs.read_file_bytes(path)
        assert resolved == expect


@pytest.mark.parametrize(
    ("case_key", "expect"),
    [
        ("inside_directory_relative", True),
        ("inside_directory_relative_dots", True),
        ("inside_directory_absolute", True),
        ("inside_file_relative", True),
        ("inside_file_relative_dots", True),
        ("inside_file_absolute", True),
        ("missing_inside_dir_relative", False),
        ("missing_inside_dir_relative_dots", False),
        ("outside_dir_relative", True),
        ("outside_dir_absolute", True),
        ("outside_file_relative", True),
        ("outside_file_absolute", True),
    ],
)
def test_exists_cases(prin_tmp_path: Path, case_key: str, expect: bool):
    fs = FileSystemSource(prin_tmp_path)
    paths = _setup_tree(prin_tmp_path)
    p = paths[case_key]
    assert fs.exists(p) is expect


@pytest.mark.parametrize(
    ("case_key", "expect"),
    [
        ("inside_directory_relative", IsADirectoryError),
        ("inside_directory_relative_dots", IsADirectoryError),
        ("inside_directory_absolute", IsADirectoryError),
        ("inside_file_relative", False),
        ("inside_file_relative_dots", False),
        ("inside_file_absolute", False),
        ("missing_inside_dir_relative", FileNotFoundError),
        ("missing_inside_dir_relative_dots", FileNotFoundError),
        ("outside_dir_relative", IsADirectoryError),
        ("outside_dir_absolute", IsADirectoryError),
        ("outside_file_relative", False),
        ("outside_file_absolute", False),
    ],
)
def test_is_empty(prin_tmp_path: Path, case_key: str, expect):
    fs = FileSystemSource(prin_tmp_path)
    paths = _setup_tree(prin_tmp_path)
    p = paths[case_key]
    if isinstance(expect, type) and issubclass(expect, Exception):
        with pytest.raises(expect):
            fs.is_empty(p)
    else:
        assert fs.is_empty(p) is expect


@pytest.mark.parametrize(
    ("case_key", "expect"),
    [
        ("outside_dir_relative", None),
        ("outside_dir_absolute", None),
        ("missing_inside_dir_relative", FileNotFoundError),
        ("inside_directory_relative", None),
        ("inside_directory_absolute", None),
        ("inside_file_relative", NotADirectoryError),
        ("inside_file_absolute", NotADirectoryError),
    ],
)
def test_list_dir_ensure_and_type_cases(prin_tmp_path: Path, case_key: str, expect):
    fs = FileSystemSource(prin_tmp_path)
    paths = _setup_tree(prin_tmp_path)
    p = paths[case_key]
    if expect is None:
        # list_dir expects resolved (absolute) paths
        entries = list(fs.list_dir(fs.resolve(p)))
        assert isinstance(entries, list)
    else:
        with pytest.raises(expect):
            list(fs.list_dir(fs.resolve(p)))
