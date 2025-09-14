"""
Sep 9 2025 - known issues:
- [ ] `prin '/tmp/*bar*'` wouldn't match `/tmp/navbar.txt`.
- [ ] `prin github.com/rust-lang/book -l` errors with requests.exceptions.HTTPError: 404 Client Error: Not Found for url: https://api.github.com/repos/rust-lang/book/contents/book?ref=main
- [ ] `prin` matches *.min.js files by default.
- [ ] Test exclusions is very flimsy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from prin.adapters.filesystem import FileSystemSource
from prin.cli_common import Context
from prin.core import DepthFirstPrinter, StringWriter
from prin.formatters import HeaderFormatter


@pytest.mark.parametrize(
    "in_out",
    [
        {
            "ar": "foo/bar/",
            "az": "foo/bar/baz.txt",
            "bar": "foo/bar/",
            "baz.txt": "foo/bar/baz.txt",
            "ar/": "",
            "/bar": "",
            "/baz.txt": "",
            "ar/ba": "",
            "bar/baz.txt": "",
        }
    ],
)
def test_text_query(prin_tmp_path: Path, in_out: dict[str, str]):
    file = prin_tmp_path / "foo" / "bar" / "baz.txt"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.touch(exist_ok=True)
    file.write_text("hi baz.txt")
    src = FileSystemSource(root_cwd=prin_tmp_path)
    printer = DepthFirstPrinter(
        src,
        HeaderFormatter(),
        ctx=Context(paths=[str(prin_tmp_path)]),
    )
    buf = StringWriter()
    query, expected_match = list(in_out.items())[0]
    printer.run([query], buf)
    out = buf.text()
    if expected_match:
        assert expected_match in out, f"Expected match for {query!r}, but got {out!r}"
    else:
        assert not out, f"Expected no match for {query!r}, but got {out!r}"


@pytest.mark.parametrize(
    "in_out",
    [
        {
            "*ar*": "foo/bar/",
            "*az*": "foo/bar/baz.txt",
            "*bar*": "foo/bar/",
            "*baz.txt*": "foo/bar/baz.txt",
            "*ar/*": "",
            "*/bar*": "",
            "*/baz.txt*": "",
            "*ar/ba*": "",
            "*bar/baz.txt*": "",
        }
    ],
)
def test_glob_query(prin_tmp_path: Path, in_out: dict[str, str]):
    file = prin_tmp_path / "foo" / "bar" / "baz.txt"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.touch(exist_ok=True)
    file.write_text("hi baz.txt")
    src = FileSystemSource(root_cwd=prin_tmp_path)
    printer = DepthFirstPrinter(
        src,
        HeaderFormatter(),
        ctx=Context(paths=[str(prin_tmp_path)]),
    )
    buf = StringWriter()
    query, expected_match = list(in_out.items())[0]
    printer.run([query], buf)
    out = buf.text()
    if expected_match:
        assert expected_match in out, f"Expected match for {query!r}, but got {out!r}"
    else:
        assert not out, f"Expected no match for {query!r}, but got {out!r}"
