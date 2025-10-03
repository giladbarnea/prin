"""Tests for --no-config flag."""

from prin.adapters.filesystem import FileSystemSource
from prin.cli_common import Context, parse_common_args
from prin.core import DepthFirstPrinter, StringWriter
from prin.defaults import DEFAULT_CONFIG_EXTENSIONS
from prin.formatters import XmlFormatter


def _run_prin(ctx, root):
    source = FileSystemSource(anchor=root)
    source.configure(ctx)
    writer = StringWriter()
    printer = DepthFirstPrinter(source, XmlFormatter(), ctx)
    printer.run_pattern("", None, writer)
    return writer.text()


def test_config_included_by_default(fs_root):
    ctx = parse_common_args(["", str(fs_root.root)])
    assert ctx.no_config is False
    for pattern in DEFAULT_CONFIG_EXTENSIONS:
        assert pattern not in ctx.exclusions

    output = _run_prin(ctx, fs_root.root)
    for path in fs_root.config_files:
        assert path in output


def test_no_config_flag_excludes_config_files(fs_root):
    ctx = parse_common_args(["--no-config", "", str(fs_root.root)])
    assert ctx.no_config is True
    for pattern in DEFAULT_CONFIG_EXTENSIONS:
        assert pattern in ctx.exclusions

    output = _run_prin(ctx, fs_root.root)
    for path in fs_root.config_files:
        assert path not in output


def test_explicit_config_file_is_included(fs_root):
    explicit_path = fs_root.root / "config/settings.yaml"
    ctx = Context(no_config=True)
    source = FileSystemSource(anchor=explicit_path)
    source.configure(ctx)
    writer = StringWriter()
    printer = DepthFirstPrinter(source, XmlFormatter(), ctx)
    printer.run_pattern("", explicit_path, writer)
    output = writer.text()

    assert "config/settings.yaml" in output
    assert "database: postgres" in output


def test_no_exclude_overrides_no_config(fs_root):
    ctx = parse_common_args(["--no-config", "--no-exclude", "", str(fs_root.root)])
    assert ctx.no_exclude is True
    assert ctx.exclusions == []

    output = _run_prin(ctx, fs_root.root)
    for path in fs_root.config_files:
        assert path in output
