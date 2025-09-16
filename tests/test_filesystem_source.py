import textwrap
from pathlib import Path

import pytest

from prin.adapters.errors import NotExistingSubpath
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
    fs_source = FileSystemSource(root=prin_tmp_path)
    actual_is_empty = fs_source.is_empty(prin_tmp_path / "empty_python_file.py")
    assert actual_is_empty


def test_is_empty_returns_false_for_non_empty_python_file(prin_tmp_path: Path):
    write_file(prin_tmp_path / "non_empty_python_file.py", "print('non_empty_python_file.py')\n")
    fs_source = FileSystemSource(root=prin_tmp_path)
    actual_is_empty = fs_source.is_empty(prin_tmp_path / "non_empty_python_file.py")
    assert not actual_is_empty


def test_is_empty_returns_true_for_truly_empty_text_file(prin_tmp_path: Path):
    write_file(prin_tmp_path / "empty_text_file.txt", "")
    fs_source = FileSystemSource(root=prin_tmp_path)
    actual_is_empty = fs_source.is_empty(prin_tmp_path / "empty_text_file.txt")
    assert actual_is_empty


def test_is_empty_returns_false_for_non_empty_text_file_with_python_syntax(prin_tmp_path: Path):
    python_comment = "# This looks like a python comment\n"
    write_file(prin_tmp_path / "python_comment.md", python_comment)
    fs_source = FileSystemSource(root=prin_tmp_path)
    actual_is_empty = fs_source.is_empty(prin_tmp_path / "python_comment.md")
    assert not actual_is_empty


@pytest.mark.parametrize(
    ("root_arg", "expect_exc"),
    [
        (lambda tmp: tmp / "does_not_exist", FileNotFoundError),
        pytest.param(
            lambda tmp: (tmp / "just_a_file.txt"),
            NotADirectoryError,
            marks=pytest.mark.xfail(reason="NotADirectoryError not enforced in __init__ yet"),
        ),
        (lambda tmp: tmp, None),
    ],
)
def test_init_semantics(prin_tmp_path: Path, root_arg, expect_exc):
    if (prin_tmp_path / "just_a_file.txt").exists() is False:
        write_file(prin_tmp_path / "just_a_file.txt", "x\n")
    root = root_arg(prin_tmp_path)
    if expect_exc is None:
        FileSystemSource(root=root)
    else:
        with pytest.raises(expect_exc):
            FileSystemSource(root=root)


def _setup_tree(tmp: Path) -> dict[str, Path]:
    # real dirs/files
    d1 = tmp / "dir1"
    f1 = tmp / "file1.txt"
    d1.mkdir(parents=True, exist_ok=True)
    write_file(f1, "hello\n")
    # symlink to outside (parent)
    link_out = tmp / "link_out"
    try:
        if link_out.exists() or link_out.is_symlink():
            link_out.unlink()
        link_out.symlink_to(tmp.parent)
    except (OSError, NotImplementedError):
        # If symlinks not supported, skip creating; tests that depend on it will skip
        link_out = None
    return {
        "dir_rel": Path("dir1"),
        "dir_abs": d1,
        "file_rel": Path("file1.txt"),
        "file_abs": f1,
        "missing_rel": Path("missing_dir"),
        "not_sub_rel": Path(".."),
        "not_sub_abs": tmp.parent,
        "symlink_out": link_out,
    }


@pytest.mark.parametrize(
    ("case_key", "expected"),
    [
        ("not_sub_rel", False),
        ("not_sub_abs", False),
        ("dir_rel", True),
        ("dir_abs", True),
        ("missing_rel", False),
        ("file_rel", True),
        ("file_abs", True),
        ("symlink_out", False),
    ],
)
def test_subpath_exists_cases(prin_tmp_path: Path, case_key: str, expected: bool):
    fs = FileSystemSource(root=prin_tmp_path)
    paths = _setup_tree(prin_tmp_path)
    p = paths[case_key]
    if p is None and case_key == "symlink_out":
        pytest.skip("Symlinks not supported on this platform")
    assert fs.subpath_exists(p) is expected


@pytest.mark.parametrize(
    ("case_key", "expect"),
    [
        ("not_sub_rel", NotExistingSubpath),
        ("not_sub_abs", NotExistingSubpath),
        ("missing_rel", NotExistingSubpath),
        ("symlink_out", NotExistingSubpath),
        ("dir_rel", None),
        ("dir_abs", None),
        ("file_rel", None),
        ("file_abs", None),
    ],
)
def test_resolve_pattern_ensure_cases(prin_tmp_path: Path, case_key: str, expect):
    fs = FileSystemSource(root=prin_tmp_path)
    paths = _setup_tree(prin_tmp_path)
    p = paths[case_key]
    if p is None and case_key == "symlink_out":
        pytest.skip("Symlinks not supported on this platform")
    if expect is None:
        resolved = fs.resolve_pattern(p)
        assert Path(str(resolved)).is_absolute()
        # Round-trip back to same path
        assert Path(str(resolved)).exists()
    else:
        with pytest.raises(expect):
            fs.resolve_pattern(p)


@pytest.mark.parametrize(
    ("case_key", "expect"),
    [
        ("not_sub_rel", NotExistingSubpath),
        ("not_sub_abs", NotExistingSubpath),
        ("missing_rel", NotExistingSubpath),
        ("symlink_out", NotExistingSubpath),
        ("dir_rel", None),
        ("dir_abs", None),
        ("file_rel", NotADirectoryError),
        ("file_abs", NotADirectoryError),
    ],
)
def test_list_dir_ensure_and_type_cases(prin_tmp_path: Path, case_key: str, expect):
    fs = FileSystemSource(root=prin_tmp_path)
    paths = _setup_tree(prin_tmp_path)
    p = paths[case_key]
    if p is None and case_key == "symlink_out":
        pytest.skip("Symlinks not supported on this platform")
    if expect is None:
        entries = list(fs.list_dir(p))
        assert isinstance(entries, list)
    else:
        with pytest.raises(expect):
            list(fs.list_dir(p))


def test_list_dir_symlink_kinds(prin_tmp_path: Path):
    fs = FileSystemSource(root=prin_tmp_path)
    # make directory with symlinks inside
    dir_main = prin_tmp_path / "d"
    dir_main.mkdir(exist_ok=True)
    target_dir = prin_tmp_path / "d2"
    target_dir.mkdir(exist_ok=True)
    target_file = prin_tmp_path / "f2.txt"
    write_file(target_file, "content\n")
    link_dir = dir_main / "ld"
    link_file = dir_main / "lf"
    try:
        if link_dir.exists() or link_dir.is_symlink():
            link_dir.unlink()
        if link_file.exists() or link_file.is_symlink():
            link_file.unlink()
        link_dir.symlink_to(target_dir)
        link_file.symlink_to(target_file)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this platform")

    entries = list(fs.list_dir(dir_main))
    kinds = {e.name: e.kind for e in entries}
    from prin.core import NodeKind

    assert kinds.get("ld") == NodeKind.OTHER
    assert kinds.get("lf") == NodeKind.OTHER


@pytest.mark.parametrize(
    ("case_key", "expect"),
    [
        ("not_sub_rel", NotExistingSubpath),
        ("not_sub_abs", NotExistingSubpath),
        ("missing_rel", NotExistingSubpath),
        ("symlink_out", NotExistingSubpath),
        ("file_rel", None),
        ("file_abs", None),
        ("dir_rel", IsADirectoryError),
        ("dir_abs", IsADirectoryError),
    ],
)
def test_read_file_bytes_ensure_and_type_cases(prin_tmp_path: Path, case_key: str, expect):
    fs = FileSystemSource(root=prin_tmp_path)
    paths = _setup_tree(prin_tmp_path)
    p = paths[case_key]
    if p is None and case_key == "symlink_out":
        pytest.skip("Symlinks not supported on this platform")
    if expect is None:
        data = fs.read_file_bytes(p)
        assert isinstance(data, (bytes, bytearray))
        assert data
    else:
        with pytest.raises(expect):
            fs.read_file_bytes(p)


@pytest.mark.parametrize(
    ("case_key", "expected"),
    [
        ("not_sub_rel", NotExistingSubpath),
        ("not_sub_abs", NotExistingSubpath),
        ("missing_rel", NotExistingSubpath),
        ("symlink_out", NotExistingSubpath),
        ("file_rel", False),
        ("file_abs", False),
        ("dir_rel", False),
        ("dir_abs", False),
    ],
)
def test_is_empty_ensure_and_semantics(prin_tmp_path: Path, case_key: str, expected):
    fs = FileSystemSource(root=prin_tmp_path)
    paths = _setup_tree(prin_tmp_path)
    p = paths[case_key]
    if p is None and case_key == "symlink_out":
        pytest.skip("Symlinks not supported on this platform")
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            fs.is_empty(p)
    else:
        assert fs.is_empty(p) is expected
