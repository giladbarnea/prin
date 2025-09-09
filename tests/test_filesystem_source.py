import textwrap
from pathlib import Path

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
    fs_source = FileSystemSource(root_cwd=prin_tmp_path)
    actual_is_empty = fs_source.is_empty(prin_tmp_path / "empty_python_file.py")
    assert actual_is_empty


def test_is_empty_returns_false_for_non_empty_python_file(prin_tmp_path: Path):
    write_file(prin_tmp_path / "non_empty_python_file.py", "print('non_empty_python_file.py')\n")
    fs_source = FileSystemSource(root_cwd=prin_tmp_path)
    actual_is_empty = fs_source.is_empty(prin_tmp_path / "non_empty_python_file.py")
    assert not actual_is_empty


def test_is_empty_returns_true_for_truly_empty_text_file(prin_tmp_path: Path):
    write_file(prin_tmp_path / "empty_text_file.txt", "")
    fs_source = FileSystemSource(root_cwd=prin_tmp_path)
    actual_is_empty = fs_source.is_empty(prin_tmp_path / "empty_text_file.txt")
    assert actual_is_empty


def test_is_empty_returns_false_for_non_empty_text_file_with_python_syntax(prin_tmp_path: Path):
    python_comment = "# This looks like a python comment\n"
    write_file(prin_tmp_path / "python_comment.md", python_comment)
    fs_source = FileSystemSource(root_cwd=prin_tmp_path)
    actual_is_empty = fs_source.is_empty(prin_tmp_path / "python_comment.md")
    assert not actual_is_empty
