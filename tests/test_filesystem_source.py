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


@pytest.mark.skip("resolve_display removed; adapter computes display internally in walk()")
def test_resolve_display():
    pass


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


def test_walk_file_under_anchor(prin_tmp_path: Path):
	from tests.utils import write_file
	from prin.adapters.filesystem import FileSystemSource

	write_file(prin_tmp_path / "a.py", "print('a')\n")
	src = FileSystemSource(prin_tmp_path)
	entries = list(src.walk(str(prin_tmp_path / "a.py")))
	assert len(entries) == 1
	e = entries[0]
	assert e.explicit is True
	# display path is relative to anchor (file under anchor)
	assert e.path.as_posix() == "a.py"
	# abs_path is absolute
	assert Path(str(e.abs_path)).is_absolute()
	assert e.kind.name == "FILE"


def test_walk_dir_under_anchor(prin_tmp_path: Path):
	from tests.utils import write_file
	from prin.adapters.filesystem import FileSystemSource

	# Create mixed-case names to test case-insensitive ordering
	write_file(prin_tmp_path / "Dir" / "b.txt", "B\n")
	write_file(prin_tmp_path / "dir" / "A.py", "print('A')\n")
	write_file(prin_tmp_path / "dir" / "a.md", "# a\n")
	write_file(prin_tmp_path / "dir" / "Z.json", "{\n}\n")
	write_file(prin_tmp_path / "dir" / "sub" / "c.py", "print('c')\n")

	src = FileSystemSource(prin_tmp_path)
	entries = list(src.walk(str(prin_tmp_path)))
	# Filter for our files under anchor and ensure only files are yielded
	paths = [e.path.as_posix() for e in entries if e.path.as_posix().startswith("dir/") or e.path.as_posix().startswith("Dir/")]
	assert all("/" in p or p.endswith((".py", ".md", ".json", ".txt")) for p in paths)
	# Check that display paths are relative to anchor
	assert "dir/A.py" in paths
	assert "dir/a.md" in paths
	assert "dir/Z.json" in paths
	assert "Dir/b.txt" in paths or "dir/b.txt" in paths  # depending on FS normalization
	assert "dir/sub/c.py" in paths
	# Ensure abs_path are absolute and kinds are FILE
	subset = [e for e in entries if e.path.as_posix() in {"dir/A.py", "dir/a.md", "dir/Z.json", "dir/sub/c.py"}]
	for e in subset:
		assert Path(str(e.abs_path)).is_absolute()
		assert e.kind.name == "FILE"


def test_walk_root_outside_anchor(prin_tmp_path: Path, tmp_path: Path):
	from tests.utils import write_file
	from prin.adapters.filesystem import FileSystemSource

	outside = tmp_path / "out"
	write_file(outside / "x" / "b.md", "b\n")
	write_file(outside / "x" / "a.py", "print('a')\n")

	src = FileSystemSource(prin_tmp_path)
	entries = list(src.walk(str(outside)))
	paths = [e.path.as_posix() for e in entries]
	# Display paths should be relative to 'outside' root, not to anchor
	assert "x/b.md" in paths
	assert "x/a.py" in paths
	for e in entries:
		p = e.path.as_posix()
		if p in {"x/b.md", "x/a.py"}:
			assert Path(str(e.abs_path)).is_absolute()
			assert e.kind.name == "FILE"


def test_walk_dfs_orders_dirs_then_files_case_insensitive(prin_tmp_path: Path):
	from tests.utils import write_file
	from prin.adapters.filesystem import FileSystemSource

	# Layout:
	# dir/
	#   b.txt
	#   A.py
	#   sub/
	#     c.md
	write_file(prin_tmp_path / "dir" / "b.txt", "b\n")
	write_file(prin_tmp_path / "dir" / "A.py", "print('A')\n")
	write_file(prin_tmp_path / "dir" / "sub" / "c.md", "# c\n")

	src = FileSystemSource(prin_tmp_path)
	# Use internal helper directly
	entries = list(src.walk_dfs(prin_tmp_path / "dir"))
	# Only files
	assert all(e.kind.name == "FILE" for e in entries)
	# Case-insensitive names at the same level and files yielded before descending into subdirs
	paths = [Path(str(e.path)).name for e in entries]
	# Root files 'A.py' then 'b.txt' (case-insensitive) appear before subtree 'c.md'
	assert paths.index("A.py") < paths.index("b.txt")
	assert paths.index("b.txt") < paths.index("c.md")


def test_read_body_text_text_and_binary(prin_tmp_path: Path):
	from tests.utils import write_file
	from prin.adapters.filesystem import FileSystemSource

	write_file(prin_tmp_path / "t.txt", "hello\n")
	# Create a binary-like file by writing a NUL byte
	(prin_tmp_path / "bin.dat").write_bytes(b"\x00\x01\x02")

	src = FileSystemSource(prin_tmp_path)
	# Build entries via walk to ensure fields populated
	entries = {e.path.as_posix(): e for e in src.walk(str(prin_tmp_path))}

	text_entry = entries["t.txt"]
	text, is_binary = src.read_body_text(text_entry)
	assert is_binary is False
	assert "hello" in (text or "")

	bin_entry = entries["bin.dat"]
	text2, is_binary2 = src.read_body_text(bin_entry)
	assert is_binary2 is True
	assert text2 is None


def test_entry_shape_guarantees(prin_tmp_path: Path):
	from tests.utils import write_file
	from prin.adapters.filesystem import FileSystemSource

	write_file(prin_tmp_path / "./dot/./ignored.txt", "x\n")
	write_file(prin_tmp_path / "plain.txt", "y\n")
	write_file(prin_tmp_path / "sub" / "z.py", "print('z')\n")

	src = FileSystemSource(prin_tmp_path)
	entries = list(src.walk(str(prin_tmp_path)))
	for e in entries:
		# path is POSIX
		p = e.path.as_posix()
		assert "\\" not in p
		# no leading './'
		assert not p.startswith("./")
		# abs_path is absolute when present
		assert e.abs_path is not None
		assert Path(str(e.abs_path)).is_absolute()
		# kind is FILE
		assert e.kind.name == "FILE"
