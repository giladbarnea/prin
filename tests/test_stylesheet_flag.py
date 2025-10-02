"""Tests for --no-style / --no-css flags."""

from prin.adapters.filesystem import FileSystemSource
from prin.cli_common import Context, parse_common_args
from prin.core import DepthFirstPrinter, StringWriter
from prin.defaults import DEFAULT_STYLESHEET_EXTENSIONS
from prin.formatters import XmlFormatter


def _run_prin(ctx, root):
    source = FileSystemSource(anchor=root)
    source.configure(ctx)
    writer = StringWriter()
    printer = DepthFirstPrinter(source, XmlFormatter(), ctx)
    printer.run_pattern("", None, writer)
    return writer.text()


def test_stylesheets_included_by_default(fs_root):
    ctx = parse_common_args(["", str(fs_root.root)])
    assert ctx.no_stylesheets is False
    for pattern in DEFAULT_STYLESHEET_EXTENSIONS:
        assert pattern not in ctx.exclusions

    output = _run_prin(ctx, fs_root.root)
    assert "assets/styles/main.css" in output
    assert "assets/styles/theme.scss" in output
    assert "assets/styles/legacy.sass" in output


def test_no_style_flag_excludes_stylesheets(fs_root):
    ctx = parse_common_args(["--no-style", "", str(fs_root.root)])
    assert ctx.no_stylesheets is True
    for pattern in DEFAULT_STYLESHEET_EXTENSIONS:
        assert pattern in ctx.exclusions

    output = _run_prin(ctx, fs_root.root)
    for path in fs_root.stylesheet_files:
        assert path not in output


def test_no_css_alias_matches_no_style(fs_root):
    ctx_alias = parse_common_args(["--no-css", "", str(fs_root.root)])
    ctx_flag = parse_common_args(["--no-style", "", str(fs_root.root)])

    assert ctx_alias.no_stylesheets is True
    assert ctx_alias.exclusions == ctx_flag.exclusions


def test_explicit_stylesheet_is_included(fs_root):
    explicit_path = fs_root.root / "assets/styles/main.css"
    ctx = Context(no_stylesheets=True)
    source = FileSystemSource(anchor=explicit_path)
    source.configure(ctx)
    writer = StringWriter()
    printer = DepthFirstPrinter(source, XmlFormatter(), ctx)
    printer.run_pattern("", explicit_path, writer)
    output = writer.text()

    assert "assets/styles/main.css" in output
    assert "body { color: red; }" in output


def test_no_exclude_overrides_no_style(fs_root):
    ctx = parse_common_args(["--no-style", "--no-exclude", "", str(fs_root.root)])
    assert ctx.no_exclude is True
    assert ctx.exclusions == []

    output = _run_prin(ctx, fs_root.root)
    assert "assets/styles/main.css" in output
    assert "assets/styles/custom.pcss" in output
