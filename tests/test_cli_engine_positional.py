from __future__ import annotations

import tempfile
from pathlib import Path

from prin.adapters.filesystem import FileSystemSource
from prin.cli_common import Context
from prin.core import DepthFirstPrinter, SourceAdapter, StringWriter
from prin.formatters import Formatter, XmlFormatter
from tests.utils import touch_file, write_file


def _run(
    source: SourceAdapter,
    roots: list[str],
    formatter: Formatter = None,
    ctx: Context = None,
) -> str:
    # The StringWriter and XmlFormatter defaults make sense here before they're required for testing purposes (yet they are still configurable if needed).
    buf = StringWriter()
    formatter = formatter or XmlFormatter()
    ctx = ctx or Context()

    printer = DepthFirstPrinter(
        source,
        formatter,
        ctx=ctx,
    )
    printer.run(roots, buf)
    return buf.text()


def test_explicit_single_ignored_file_is_printed(prin_tmp_path: Path):
    # Create an ignored-by-default file (e.g., binary-like or lock)
    lock = prin_tmp_path / "poetry.lock"
    write_file(lock, "poetry-lock-content-unique\n")
    out = _run(FileSystemSource(root_cwd=prin_tmp_path), [str(lock)])
    assert "<poetry.lock>" in out


def test_two_sibling_directories_both_subdirs_of_root_print_relative_paths_to_cwd(
    prin_tmp_path: Path,
):
    # dirA and dirB siblings, each with printable files
    write_file(prin_tmp_path / "dirA" / "a.py", "print('dirA/a.py')\n")
    write_file(prin_tmp_path / "dirB" / "b.md", "# dirB/b.md\n")
    out = _run(
        FileSystemSource(root_cwd=prin_tmp_path),
        [str(prin_tmp_path / "dirA"), str(prin_tmp_path / "dirB")],
    )
    # Paths are relative to each provided root
    assert "<dirA/a.py>" in out
    assert "<dirB/b.md>" in out


def test_one_dir_outside_root_assumes_root_and_subdir_of_root_prints_relative_path_to_root(
    prin_tmp_path,
):
    """
    Given root: /foo
    Scripts is passed two positional arguments: /foo/dirA /entirely-different-dir/dirB
    Expect files in /foo/dirA to be printed relative to /foo, and files in /entirely-different-dir/dirB to be printed relative to /entirely-different-dir/dirB
    """
    source = FileSystemSource(root_cwd=prin_tmp_path)
    subdir_to_source = prin_tmp_path / "dirA"
    dir_outside_source = Path(tempfile.mkdtemp(prefix="outside_source"))
    write_file(subdir_to_source / "a.py", "print('dirA/a.py')\n")
    write_file(dir_outside_source / "dirX" / "b.txt", "outside_source/dirX/b.txt\n")
    out = _run(source, [str(subdir_to_source), str(dir_outside_source)])
    # Paths are relative to each provided root
    assert "<dirA/a.py>" in out
    assert "<dirX/b.txt>" in out


def test_directory_and_explicit_ignored_file_inside(prin_tmp_path: Path):
    # directory contains mixed files; specify dir and an otherwise-ignored file
    write_file(prin_tmp_path / "keep.py", "print('work/keep.py')\n")
    touch_file(prin_tmp_path / "junk.pyc")
    # Explicitly pass both the directory and the ignored file path
    out = _run(
        FileSystemSource(root_cwd=prin_tmp_path),
        [str(prin_tmp_path), str(prin_tmp_path / "junk.pyc")],
        ctx=Context(include_binary=False),
    )
    # Paths are relative to the directory root when provided
    assert "<keep.py>" in out
    # Even though *.pyc is excluded by default, explicit root forces print
    assert "<junk.pyc>" in out
