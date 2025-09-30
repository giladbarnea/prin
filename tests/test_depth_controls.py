"""Tests for depth control features (--max-depth, --min-depth, --exact-depth)."""

import pytest

from prin.adapters.filesystem import FileSystemSource
from prin.cli_common import Context, parse_common_args
from prin.core import DepthFirstPrinter, StringWriter
from prin.formatters import HeaderFormatter
from tests.utils import write_file


@pytest.fixture
def depth_tree(prin_tmp_path):
    """
    Create a nested directory structure for testing depth controls.

    Structure:
    root/
      file0.txt          # depth 1
      dir1/
        file1.txt        # depth 2
        dir2/
          file2.txt      # depth 3
          dir3/
            file3.txt    # depth 4
      dirA/
        fileA.txt        # depth 2
        dirB/
          fileB.txt      # depth 3
    """
    root = prin_tmp_path
    write_file(root / "file0.txt", "depth 1\n")
    write_file(root / "dir1" / "file1.txt", "depth 2 in dir1\n")
    write_file(root / "dir1" / "dir2" / "file2.txt", "depth 3 in dir2\n")
    write_file(root / "dir1" / "dir2" / "dir3" / "file3.txt", "depth 4 in dir3\n")
    write_file(root / "dirA" / "fileA.txt", "depth 2 in dirA\n")
    write_file(root / "dirA" / "dirB" / "fileB.txt", "depth 3 in dirB\n")
    return root


class TestMaxDepth:
    """Test --max-depth functionality."""

    def test_max_depth_1(self, depth_tree):
        """With --max-depth 1, only files at depth 1 should be included."""
        ctx = Context(max_depth=1)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        assert "file0.txt" in output
        assert "file1.txt" not in output
        assert "file2.txt" not in output
        assert "file3.txt" not in output
        assert "fileA.txt" not in output
        assert "fileB.txt" not in output

    def test_max_depth_2(self, depth_tree):
        """With --max-depth 2, only files at depth 1 and 2 should be included."""
        ctx = Context(max_depth=2)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        assert "file0.txt" in output
        assert "file1.txt" in output
        assert "fileA.txt" in output
        assert "file2.txt" not in output
        assert "file3.txt" not in output
        assert "fileB.txt" not in output

    def test_max_depth_3(self, depth_tree):
        """With --max-depth 3, files at depth 1, 2, and 3 should be included."""
        ctx = Context(max_depth=3)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        assert "file0.txt" in output
        assert "file1.txt" in output
        assert "fileA.txt" in output
        assert "file2.txt" in output
        assert "fileB.txt" in output
        assert "file3.txt" not in output

    def test_max_depth_unlimited(self, depth_tree):
        """With no --max-depth, all files should be included."""
        ctx = Context(max_depth=None)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        assert "file0.txt" in output
        assert "file1.txt" in output
        assert "file2.txt" in output
        assert "file3.txt" in output
        assert "fileA.txt" in output
        assert "fileB.txt" in output


class TestMinDepth:
    """Test --min-depth functionality."""

    def test_min_depth_1(self, depth_tree):
        """With --min-depth 1, all files should be included (default behavior)."""
        ctx = Context(min_depth=1)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        assert "file0.txt" in output
        assert "file1.txt" in output
        assert "file2.txt" in output
        assert "file3.txt" in output

    def test_min_depth_2(self, depth_tree):
        """With --min-depth 2, only files at depth 2+ should be included."""
        ctx = Context(min_depth=2)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        assert "file0.txt" not in output
        assert "file1.txt" in output
        assert "fileA.txt" in output
        assert "file2.txt" in output
        assert "file3.txt" in output
        assert "fileB.txt" in output

    def test_min_depth_3(self, depth_tree):
        """With --min-depth 3, only files at depth 3+ should be included."""
        ctx = Context(min_depth=3)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        assert "file0.txt" not in output
        assert "file1.txt" not in output
        assert "fileA.txt" not in output
        assert "file2.txt" in output
        assert "fileB.txt" in output
        assert "file3.txt" in output

    def test_min_depth_4(self, depth_tree):
        """With --min-depth 4, only files at depth 4+ should be included."""
        ctx = Context(min_depth=4)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        assert "file0.txt" not in output
        assert "file1.txt" not in output
        assert "fileA.txt" not in output
        assert "file2.txt" not in output
        assert "fileB.txt" not in output
        assert "file3.txt" in output


class TestExactDepth:
    """Test --exact-depth functionality."""

    def test_exact_depth_1(self, depth_tree):
        """With --exact-depth 1, only files at exactly depth 1 should be included."""
        ctx = Context(exact_depth=1)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        assert "file0.txt" in output
        assert "file1.txt" not in output
        assert "fileA.txt" not in output
        assert "file2.txt" not in output

    def test_exact_depth_2(self, depth_tree):
        """With --exact-depth 2, only files at exactly depth 2 should be included."""
        ctx = Context(exact_depth=2)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        assert "file0.txt" not in output
        assert "file1.txt" in output
        assert "fileA.txt" in output
        assert "file2.txt" not in output
        assert "fileB.txt" not in output

    def test_exact_depth_3(self, depth_tree):
        """With --exact-depth 3, only files at exactly depth 3 should be included."""
        ctx = Context(exact_depth=3)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        assert "file0.txt" not in output
        assert "file1.txt" not in output
        assert "fileA.txt" not in output
        assert "file2.txt" in output
        assert "fileB.txt" in output
        assert "file3.txt" not in output

    def test_exact_depth_overrides_min_max(self, depth_tree):
        """--exact-depth should override --min-depth and --max-depth."""
        ctx = Context(exact_depth=2, min_depth=1, max_depth=4)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        # Should behave same as exact_depth=2 alone
        assert "file0.txt" not in output
        assert "file1.txt" in output
        assert "fileA.txt" in output
        assert "file2.txt" not in output


class TestCombinedDepthControls:
    """Test combinations of min and max depth."""

    def test_min_2_max_3(self, depth_tree):
        """With --min-depth 2 --max-depth 3, only files at depth 2 and 3 should be included."""
        ctx = Context(min_depth=2, max_depth=3)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        assert "file0.txt" not in output
        assert "file1.txt" in output
        assert "fileA.txt" in output
        assert "file2.txt" in output
        assert "fileB.txt" in output
        assert "file3.txt" not in output

    def test_min_3_max_3(self, depth_tree):
        """With --min-depth 3 --max-depth 3, only files at exactly depth 3 (same as exact-depth 3)."""
        ctx = Context(min_depth=3, max_depth=3)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("", None, writer)

        output = writer.text()
        assert "file0.txt" not in output
        assert "file1.txt" not in output
        assert "file2.txt" in output
        assert "fileB.txt" in output
        assert "file3.txt" not in output


class TestCLIDepthParsing:
    """Test that CLI arguments are properly parsed."""

    def test_max_depth_cli_parsing(self):
        """Test --max-depth CLI argument parsing."""
        ctx = parse_common_args(["--max-depth", "2"])
        assert ctx.max_depth == 2

    def test_min_depth_cli_parsing(self):
        """Test --min-depth CLI argument parsing."""
        ctx = parse_common_args(["--min-depth", "3"])
        assert ctx.min_depth == 3

    def test_exact_depth_cli_parsing(self):
        """Test --exact-depth CLI argument parsing."""
        ctx = parse_common_args(["--exact-depth", "1"])
        assert ctx.exact_depth == 1

    def test_combined_depth_cli_parsing(self):
        """Test combined depth arguments."""
        ctx = parse_common_args(["--min-depth", "2", "--max-depth", "4"])
        assert ctx.min_depth == 2
        assert ctx.max_depth == 4

    def test_default_depth_values(self):
        """Test that default depth values are None."""
        ctx = parse_common_args([])
        assert ctx.max_depth is None
        assert ctx.min_depth is None
        assert ctx.exact_depth is None


class TestDepthWithPatterns:
    """Test depth controls with pattern matching."""

    def test_max_depth_with_pattern(self, depth_tree):
        """Depth controls should work with pattern matching."""
        ctx = Context(max_depth=2)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        printer.run_pattern("*.txt", None, writer)

        output = writer.text()
        assert "file0.txt" in output
        assert "file1.txt" in output
        assert "fileA.txt" in output
        # These should be excluded by max_depth
        assert "file2.txt" not in output
        assert "file3.txt" not in output

    def test_exact_depth_with_pattern(self, depth_tree):
        """Exact depth with pattern should only match at specified depth."""
        ctx = Context(exact_depth=3)
        source = FileSystemSource(anchor=depth_tree)
        source.configure(ctx)

        writer = StringWriter()
        printer = DepthFirstPrinter(source, HeaderFormatter(), ctx)
        # Use regex pattern that matches filenames containing 'file' or 'B'
        printer.run_pattern(".*file.*\\.txt$|.*B\\.txt$", None, writer)

        output = writer.text()
        assert "file0.txt" not in output
        assert "file1.txt" not in output
        assert "file2.txt" in output
        assert "fileB.txt" in output
        assert "file3.txt" not in output
