from __future__ import annotations

from pathlib import Path
from typing import Literal

from prin.adapters.filesystem import FileSystemSource
from prin.cli_common import Context, derive_filters_and_print_flags
from prin.core import DepthFirstPrinter, Formatter, SourceAdapter, StringWriter
from prin.defaults import (
    DEFAULT_EXCLUSIONS,
    DEFAULT_EXTENSIONS_FILTER,
    DEFAULT_INCLUDE_BINARY,
    DEFAULT_INCLUDE_EMPTY,
    DEFAULT_INCLUDE_HIDDEN,
    DEFAULT_INCLUDE_LOCK,
    DEFAULT_INCLUDE_TESTS,
    DEFAULT_NO_DOCS,
    DEFAULT_NO_EXCLUDE,
    DEFAULT_NO_IGNORE,
    DEFAULT_ONLY_HEADERS,
    DEFAULT_TAG,
)
from prin.formatters import XmlFormatter
from prin.types import TExclusion
from tests.utils import touch_file, write_file


def _run(
    source: SourceAdapter,
    roots: list[str],
    formatter: Formatter = None,
    *,
    # Parameter list should match CLI options.
    include_tests: bool = DEFAULT_INCLUDE_TESTS,
    include_lock: bool = DEFAULT_INCLUDE_LOCK,
    include_binary: bool = DEFAULT_INCLUDE_BINARY,
    no_docs: bool = DEFAULT_NO_DOCS,
    include_empty: bool = DEFAULT_INCLUDE_EMPTY,
    only_headers: bool = DEFAULT_ONLY_HEADERS,
    extensions: list[str] = DEFAULT_EXTENSIONS_FILTER,
    exclude: list[TExclusion] = DEFAULT_EXCLUSIONS,
    no_exclude: bool = DEFAULT_NO_EXCLUDE,
    no_ignore: bool = DEFAULT_NO_IGNORE,
    include_hidden: bool = DEFAULT_INCLUDE_HIDDEN,
    tag: Literal["xml", "md"] = DEFAULT_TAG,
    max_files: int | None = None,
) -> str:
    # The StringWriter and XmlFormatter defaults make sense here before they're required for testing purposes (yet they are still configurable if needed).
    buf = StringWriter()
    formatter = formatter or XmlFormatter()

    # The other parameters are completely inconsequential for testing purposes, therefore should be a transparent pass-through. Individual tests can override them if needed.
    ctx = Context(
        include_tests=include_tests,
        include_lock=include_lock,
        include_binary=include_binary,
        no_docs=no_docs,
        include_empty=include_empty,
        only_headers=only_headers,
        extensions=extensions,
        exclude=exclude,
        no_exclude=no_exclude,
        no_ignore=no_ignore,
        include_hidden=include_hidden,
        tag=tag,
        max_files=max_files,
    )
    extensions, exclusions, include_empty, only_headers = derive_filters_and_print_flags(ctx)

    printer = DepthFirstPrinter(
        source,
        formatter,
        include_empty=include_empty,
        only_headers=only_headers,
        extensions=extensions,
        exclude=exclusions,
    )
    printer.run(roots, buf)
    return buf.text()


def test_explicit_single_ignored_file_is_printed(tmp_path: Path):
    # Create an ignored-by-default file (e.g., binary-like or lock)
    lock = tmp_path / "poetry.lock"
    write_file(lock, "poetry-lock-content-unique\n")
    out = _run(FileSystemSource(root_cwd=tmp_path), [str(lock)])
    assert "<poetry.lock>" in out


def test_two_sibling_directories(tmp_path: Path):
    # dirA and dirB siblings, each with printable files
    write_file(tmp_path / "dirA" / "a.py", "print('dirA/a.py')\n")
    write_file(tmp_path / "dirB" / "b.md", "# dirB/b.md\n")
    out = _run(
        FileSystemSource(root_cwd=tmp_path), [str(tmp_path / "dirA"), str(tmp_path / "dirB")]
    )
    # Paths are relative to each provided root
    assert "<dirA/a.py>" in out
    assert "<dirB/b.md>" in out


def test_directory_and_explicit_ignored_file_inside(tmp_path: Path):
    # directory contains mixed files; specify dir and an otherwise-ignored file
    write_file(tmp_path / "work" / "keep.py", "print('work/keep.py')\n")
    touch_file(tmp_path / "work" / "__pycache__" / "junk.pyc")
    # Explicitly pass both the directory and the ignored file path
    out = _run(
        FileSystemSource(root_cwd=tmp_path),
        [str(tmp_path / "work"), str(tmp_path / "work" / "__pycache__" / "junk.pyc")],
    )
    # Paths are relative to the directory root when provided
    assert "<work/keep.py>" in out
    # Even though *.pyc is excluded by default, explicit root forces print
    assert "<work/__pycache__/junk.pyc>" in out
