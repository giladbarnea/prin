from __future__ import annotations

from pathlib import Path

from prin.adapters.filesystem import FileSystemSource
from prin.core import DepthFirstPrinter, StringWriter
from prin.defaults import DEFAULT_BINARY_EXCLUSIONS, DEFAULT_EXCLUSIONS
from prin.formatters import XmlFormatter
from tests.utils import touch_file, write_file


def _run(src: FileSystemSource, roots: list[str]) -> str:
    buf = StringWriter()
    printer = DepthFirstPrinter(
        src,
        XmlFormatter(),
        include_empty=True,
        only_headers=False,
        extensions=[".py", ".md", ".json"],
        exclude=[*DEFAULT_EXCLUSIONS, *DEFAULT_BINARY_EXCLUSIONS],
    )
    printer.run(roots, buf)
    return buf.text()


def test_explicit_single_ignored_file_is_printed(tmp_path: Path):
    # Create an ignored-by-default file (e.g., binary-like or lock)
    lock = tmp_path / "poetry.lock"
    write_file(lock, "dummy\n")
    out = _run(FileSystemSource(root_cwd=tmp_path), [str(lock)])
    assert "<poetry.lock>" in out


def test_two_sibling_directories(tmp_path: Path):
    # dirA and dirB siblings, each with printable files
    write_file(tmp_path / "dirA" / "a.py", "print('a')\n")
    write_file(tmp_path / "dirB" / "b.md", "# b\n")
    out = _run(
        FileSystemSource(root_cwd=tmp_path), [str(tmp_path / "dirA"), str(tmp_path / "dirB")]
    )
    # Paths are relative to each provided root
    assert "<a.py>" in out
    assert "<b.md>" in out


def test_directory_and_explicit_ignored_file_inside(tmp_path: Path):
    # directory contains mixed files; specify dir and an otherwise-ignored file
    write_file(tmp_path / "work" / "keep.py", "print('ok')\n")
    touch_file(tmp_path / "work" / "__pycache__" / "junk.pyc")
    # Explicitly pass both the directory and the ignored file path
    out = _run(
        FileSystemSource(root_cwd=tmp_path),
        [str(tmp_path / "work"), str(tmp_path / "work" / "__pycache__" / "junk.pyc")],
    )
    # Paths are relative to the directory root when provided
    assert "<keep.py>" in out
    # Even though *.pyc is excluded by default, explicit root forces print
    assert "<junk.pyc>" in out or "<work/__pycache__/junk.pyc>" in out
