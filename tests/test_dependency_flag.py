"""Tests for --no-dependencies flag."""

from prin.adapters.filesystem import FileSystemSource
from prin.cli_common import Context, parse_common_args
from prin.core import DepthFirstPrinter, StringWriter
from prin.defaults import DEFAULT_DEPENDENCY_EXCLUSIONS
from prin.formatters import XmlFormatter


def test_include_dependencies_default(fs_root):
    """By default, dependency spec files are included."""
    ctx = parse_common_args(["", str(fs_root.root)])
    assert ctx.include_dependencies is True
    # Dependency exclusions should not be in the exclusions list
    for dep_pattern in DEFAULT_DEPENDENCY_EXCLUSIONS:
        assert dep_pattern not in ctx.exclusions

    # Run prin and check that dependency spec files are in output
    source = FileSystemSource(anchor=fs_root.root)
    source.configure(ctx)
    writer = StringWriter()
    printer = DepthFirstPrinter(source, XmlFormatter(), ctx)
    printer.run_pattern("", None, writer)
    output = writer.text()

    # Check that some dependency files are present
    assert "package.json" in output
    assert "pyproject.toml" in output
    assert "requirements.txt" in output


def test_no_dependencies_flag_excludes_dependency_files(fs_root):
    """--no-dependencies excludes dependency specification files."""
    ctx = parse_common_args(["--no-dependencies", "", str(fs_root.root)])
    assert ctx.include_dependencies is False
    # Dependency exclusions should be in the exclusions list
    for dep_pattern in DEFAULT_DEPENDENCY_EXCLUSIONS:
        assert dep_pattern in ctx.exclusions

    # Run prin with --no-dependencies
    source = FileSystemSource(anchor=fs_root.root)
    source.configure(ctx)
    writer = StringWriter()
    printer = DepthFirstPrinter(source, XmlFormatter(), ctx)
    printer.run_pattern("", None, writer)
    output = writer.text()

    # Check that dependency spec files are excluded
    assert "package.json" not in output
    assert "pyproject.toml" not in output
    assert "requirements.txt" not in output
    assert "requirements-dev.txt" not in output
    assert "pom.xml" not in output
    assert "build.gradle" not in output
    assert "Cargo.toml" not in output
    assert "go.mod" not in output
    assert "Gemfile" not in output
    assert "composer.json" not in output
    assert "Podfile" not in output
    assert "pubspec.yaml" not in output


def test_no_dependencies_does_not_exclude_lock_files(fs_root):
    """--no-dependencies does not exclude lock files (they have their own flag)."""
    # Run with --no-dependencies but without --include-lock
    ctx = parse_common_args(["--no-dependencies", "", str(fs_root.root)])
    source = FileSystemSource(anchor=fs_root.root)
    source.configure(ctx)
    writer = StringWriter()
    printer = DepthFirstPrinter(source, XmlFormatter(), ctx)
    printer.run_pattern("", None, writer)
    output = writer.text()

    # Lock files should still be excluded by default (not included without --include-lock)
    assert "poetry.lock" not in output
    assert "package-lock.json" not in output


def test_no_dependencies_with_include_lock(fs_root):
    """--no-dependencies with --include-lock includes lock files but not spec files."""
    ctx = parse_common_args(["--no-dependencies", "--include-lock", "", str(fs_root.root)])
    source = FileSystemSource(anchor=fs_root.root)
    source.configure(ctx)
    writer = StringWriter()
    printer = DepthFirstPrinter(source, XmlFormatter(), ctx)
    printer.run_pattern("", None, writer)
    output = writer.text()

    # Lock files should be included
    assert "poetry.lock" in output
    assert "package-lock.json" in output
    assert "uv.lock" in output

    # Spec files should still be excluded
    assert "package.json" not in output
    assert "pyproject.toml" not in output


def test_no_dependencies_does_not_exclude_regular_files(fs_root):
    """--no-dependencies does not exclude regular code files."""
    ctx = parse_common_args(["--no-dependencies", "", str(fs_root.root)])
    source = FileSystemSource(anchor=fs_root.root)
    source.configure(ctx)
    writer = StringWriter()
    printer = DepthFirstPrinter(source, XmlFormatter(), ctx)
    printer.run_pattern("", None, writer)
    output = writer.text()

    # Regular files should still be present
    assert "foo.py" in output
    assert "src/app.py" in output
    assert "src/util.py" in output


def test_explicit_dependency_file_included(fs_root):
    """Explicitly specified dependency file is included even with --no-dependencies."""
    package_json = fs_root.root / "package.json"
    ctx = Context(include_dependencies=False)
    source = FileSystemSource(anchor=package_json)
    source.configure(ctx)
    writer = StringWriter()
    printer = DepthFirstPrinter(source, XmlFormatter(), ctx)
    printer.run_pattern("", package_json, writer)
    output = writer.text()

    # Explicitly specified file should be included
    assert "package.json" in output
    assert '"name": "test-pkg"' in output


def test_no_exclude_overrides_no_dependencies(fs_root):
    """--no-exclude / --include-all overrides --no-dependencies."""
    ctx = parse_common_args(["--no-dependencies", "--no-exclude", "", str(fs_root.root)])
    source = FileSystemSource(anchor=fs_root.root)
    source.configure(ctx)
    writer = StringWriter()
    printer = DepthFirstPrinter(source, XmlFormatter(), ctx)
    printer.run_pattern("", None, writer)
    output = writer.text()

    # Everything should be included
    assert "package.json" in output
    assert "pyproject.toml" in output
    assert "requirements.txt" in output
