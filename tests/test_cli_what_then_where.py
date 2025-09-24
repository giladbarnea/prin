"""
Test the CLI interface for the new what-then-where design.
"""

from __future__ import annotations

import pytest

from prin.cli_common import parse_common_args


def test_cli_pattern_then_path():
    """Test CLI parsing: 'prin "*.py" src/'"""
    args = parse_common_args(["*.py", "src/"])
    assert args.pattern == "*.py"
    assert args.search_path == "src/"
    assert args.paths == []  # Old paths field should be empty


def test_cli_pattern_only():
    """Test CLI parsing with pattern only: 'prin "*.md"'"""
    args = parse_common_args(["*.md"])
    assert args.pattern == "*.md"
    assert args.search_path is None  # Default to None (cwd)
    assert args.paths == []


def test_cli_no_args():
    """Test CLI parsing with no arguments: 'prin'"""
    args = parse_common_args([])
    assert args.pattern == ""  # Empty pattern means all files
    assert args.search_path is None  # Default to cwd
    assert args.paths == []


def test_cli_explicit_file():
    """Test CLI parsing with explicit file: 'prin exact_file.py'"""
    # This is a special case - single arg that's an existing file
    args = parse_common_args(["exact_file.py"])
    assert args.pattern == "exact_file.py"
    assert args.search_path is None
    assert args.paths == []


def test_cli_regex_pattern():
    r"""Test CLI parsing with regex pattern: 'prin "^test_.*\.py$" .'"""
    args = parse_common_args(["^test_.*\\.py$", "."])
    assert args.pattern == "^test_.*\\.py$"
    assert args.search_path == "."
    assert args.paths == []


def test_cli_github_url_pattern():
    """Test CLI parsing with GitHub URL: 'prin "*.rs" github.com/rust-lang/book'"""
    args = parse_common_args(["*.rs", "github.com/rust-lang/book"])
    assert args.pattern == "*.rs"
    assert args.search_path == "github.com/rust-lang/book"
    assert args.paths == []


def test_cli_backwards_compatibility():
    """Test that we maintain some backwards compatibility during transition"""
    # For now, we'll handle the old style by detecting it
    # If there's more than 2 positional args, it's old style
    pytest.skip("Backwards compatibility strategy TBD")
