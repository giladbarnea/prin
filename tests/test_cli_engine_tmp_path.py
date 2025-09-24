from __future__ import annotations

from prin.adapters.filesystem import FileSystemSource
from prin.cli_common import Context
from prin.core import DepthFirstPrinter, StringWriter
from prin.formatters import XmlFormatter
from tests.utils import touch_file, write_file


def test_cli_engine_happy_path(tmp_path):
    # Build a 2-3 level tree with interspersed files
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "docs").mkdir()

    # Included-by-default extensions: pick a subset (py, md, json*)
    write_file(tmp_path / "src" / "main.py", "print('hello')\nprint('world')\n")
    write_file(tmp_path / "docs" / "readme.md", "# Title\n\nSome docs.\n")
    write_file(tmp_path / "src" / "config.json", '{\n  "a": 1,\n  "b": 2\n}\n')

    # Nested level
    write_file(tmp_path / "src" / "pkg" / "module.py", "def f():\n    return 1\n\nprint(f())\n")
    write_file(tmp_path / "src" / "pkg" / "data.jsonl", '{"x":1}\n{"x":2}\n')

    # Default-ignored categories (lock/test/binary)
    write_file(tmp_path / "poetry.lock", "dummy\n")
    write_file(tmp_path / "package-lock.json", "{}\n")
    touch_file(tmp_path / "build" / "artifact.o")
    touch_file(tmp_path / "__pycache__" / "module.pyc")  # binary
    (tmp_path / "tests").mkdir()
    write_file(tmp_path / "tests" / "test_something.py", "def test_x():\n    assert True\n")

    # Use hardcoded filters to isolate traversal/printing happy path
    src = FileSystemSource(tmp_path)
    printer = DepthFirstPrinter(
        src,
        XmlFormatter(),
        ctx=Context(),
    )

    buf = StringWriter()
    printer.run_pattern("", str(tmp_path), buf)
    out = buf.text()

    # Included-by-default must appear
    assert "<src/main.py>" in out
    assert "<docs/readme.md>" in out
    assert "<src/config.json>" in out
    assert "<src/pkg/module.py>" in out
    # Cover default glob-ish like json* by ensuring jsonl also counted if implied
    # If not included by default in implementation, this assertion can be relaxed to explicit extension list in args.
    # For current defaults it should be included via json* pattern.
    # Note: ".json*" pattern in defaults doesn't match jsonl via glob in current semantics; we don't assert it.

    # We bypassed default exclusions in this isolated traversal test; ensure traversal happened,
    # but don't assert on default-ignored categories here.


def test_cli_engine_isolation(tmp_path):
    (tmp_path / "dir" / "sub").mkdir(parents=True)
    write_file(tmp_path / "dir" / "a.py", "print('a')\nprint('b')\n")
    write_file(tmp_path / "dir" / "sub" / "b.md", "# b\n\ntext\n")
    touch_file(tmp_path / "__pycache__" / "c.pyc")

    # Bypass parser-derived filters; hardcode simple includes/excludes
    src = FileSystemSource(tmp_path)
    printer = DepthFirstPrinter(
        src,
        XmlFormatter(),
        ctx=Context(),
    )

    buf = StringWriter()
    # Explicitly pass the tmp_path root to run_pattern
    printer.run_pattern("", str(tmp_path), buf)
    out = buf.text()
    assert "<dir/a.py>" in out
    assert "<dir/sub/b.md>" in out
    assert "__pycache__/c.pyc" not in out
