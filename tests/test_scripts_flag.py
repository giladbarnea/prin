"""Tests for --no-scripts flag."""

from prin.adapters.filesystem import FileSystemSource
from prin.cli_common import Context, parse_common_args
from prin.core import DepthFirstPrinter, StringWriter
from prin.defaults import DEFAULT_SCRIPT_EXCLUSIONS
from prin.formatters import XmlFormatter


def _run_prin(ctx, root):
    source = FileSystemSource(anchor=root)
    source.configure(ctx)
    writer = StringWriter()
    printer = DepthFirstPrinter(source, XmlFormatter(), ctx)
    printer.run_pattern("", None, writer)
    return writer.text()


def test_scripts_included_by_default(fs_root):
    ctx = parse_common_args(["", str(fs_root.root)])
    assert ctx.no_scripts is False
    for pattern in DEFAULT_SCRIPT_EXCLUSIONS:
        assert pattern not in ctx.exclusions

    output = _run_prin(ctx, fs_root.root)
    for path in fs_root.script_files:
        assert path in output


def test_no_scripts_flag_excludes_scripts(fs_root):
    ctx = parse_common_args(["--no-scripts", "", str(fs_root.root)])
    assert ctx.no_scripts is True
    for pattern in DEFAULT_SCRIPT_EXCLUSIONS:
        assert pattern in ctx.exclusions

    output = _run_prin(ctx, fs_root.root)
    for path in fs_root.script_files:
        assert path not in output


def test_scripts_directory_excluded(fs_root):
    ctx = parse_common_args(["--no-scripts", "", str(fs_root.root)])
    output = _run_prin(ctx, fs_root.root)

    assert "scripts/deploy.sh" not in output
    assert "scripts/setup.ps1" not in output


def test_explicit_script_is_included(fs_root):
    explicit_path = fs_root.root / "scripts/deploy.sh"
    ctx = Context(no_scripts=True)
    source = FileSystemSource(anchor=explicit_path)
    source.configure(ctx)
    writer = StringWriter()
    printer = DepthFirstPrinter(source, XmlFormatter(), ctx)
    printer.run_pattern("", explicit_path, writer)
    output = writer.text()

    assert "scripts/deploy.sh" in output
    assert "echo 'deploy'" in output


def test_no_exclude_overrides_no_scripts(fs_root):
    ctx = parse_common_args(["--no-scripts", "--no-exclude", "", str(fs_root.root)])
    assert ctx.no_exclude is True
    assert ctx.exclusions == []

    output = _run_prin(ctx, fs_root.root)
    for path in fs_root.script_files:
        assert path in output
