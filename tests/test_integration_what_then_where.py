"""
Integration tests for the new what-then-where design.
Tests the complete flow from CLI to output.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prin.core import StringWriter
from prin.prin import main
from tests.utils import write_file


def test_filesystem_integration():
    """Test filesystem pattern search end-to-end"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create test files
        write_file(tmp_path / "src" / "main.py", "print('main')")
        write_file(tmp_path / "src" / "util.py", "print('util')")
        write_file(tmp_path / "src" / "test_util.py", "# test util")
        write_file(tmp_path / "docs" / "readme.md", "# Readme")
        write_file(tmp_path / "docs" / "guide.md", "# Guide")
        
        # Test 1: Pattern search in specific directory
        writer = StringWriter()
        main(argv=["*.py", str(tmp_path / "src")], writer=writer)
        output = writer.text()
        
        print(f"Output: {output}")
        
        assert "<main.py>" in output
        assert "<util.py>" in output
        # Note: test files are excluded by default, so test_util.py won't appear
        assert "test_util.py" not in output
        assert "readme.md" not in output
        
        # Test 2: Regex pattern (with --include-tests to see test files)
        writer = StringWriter()
        main(argv=["--include-tests", r"test_.*\.py$", str(tmp_path)], writer=writer)
        output = writer.text()
        
        assert "<src/test_util.py>" in output or "<test_util.py>" in output
        assert "main.py" not in output
        assert "util.py" not in output
        
        # Test 3: All markdown files
        writer = StringWriter()
        main(argv=["*.md", str(tmp_path)], writer=writer)
        output = writer.text()
        
        assert "readme.md" in output
        assert "guide.md" in output
        assert ".py" not in output


def test_no_pattern_lists_all():
    """Test that no pattern lists all files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        write_file(tmp_path / "a.txt", "content a")
        write_file(tmp_path / "b.py", "content b")
        write_file(tmp_path / "sub" / "c.md", "content c")
        
        writer = StringWriter()
        main(argv=["", str(tmp_path)], writer=writer)
        output = writer.text()
        
        assert "<a.txt>" in output
        assert "<b.py>" in output
        assert "c.md" in output


def test_pattern_without_path_uses_cwd():
    """Test that pattern without path searches current directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create files in temp dir
        write_file(tmp_path / "test1.py", "# test 1")
        write_file(tmp_path / "test2.py", "# test 2")
        write_file(tmp_path / "main.py", "# main")
        
        # Change to temp dir
        import os
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            writer = StringWriter()
            main(argv=["test*.py"], writer=writer)
            output = writer.text()
            
            assert "<test1.py>" in output
            assert "<test2.py>" in output
            assert "main.py" not in output
        finally:
            os.chdir(old_cwd)


def test_exact_file_pattern():
    """Test that exact file paths still work"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        write_file(tmp_path / "exact_file.py", "# exact content")
        write_file(tmp_path / "other_file.py", "# other content")
        
        writer = StringWriter()
        main(argv=[str(tmp_path / "exact_file.py")], writer=writer)
        output = writer.text()
        
        assert "<exact_file.py>" in output
        assert "# exact content" in output
        assert "other_file.py" not in output


def test_github_pattern_integration():
    """Test GitHub repository pattern search"""
    # Skip if no network or GitHub mock not available
    import os
    if os.getenv("PRIN_NO_NETWORK") or not os.getenv("PRIN_GH_MOCK_ROOT"):
        pytest.skip("Network disabled or GitHub mock not available")
    
    # This would test something like:
    # prin "*.md" github.com/owner/repo
    pytest.skip("GitHub integration test pending mock setup")