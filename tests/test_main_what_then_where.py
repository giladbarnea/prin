"""
Test the main dispatcher with the new what-then-where design.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from prin.core import StringWriter
from prin.prin import main
from tests.utils import write_file


def test_main_pattern_then_path(prin_tmp_path: Path):
    """Test main with pattern and path: 'prin "*.py" src/'"""
    write_file(prin_tmp_path / "src" / "main.py", "print('main')")
    write_file(prin_tmp_path / "src" / "util.py", "print('util')")
    write_file(prin_tmp_path / "src" / "readme.md", "# Readme")
    write_file(prin_tmp_path / "tests" / "test_main.py", "# test")
    
    writer = StringWriter()
    main(argv=["*.py", str(prin_tmp_path / "src")], writer=writer)
    output = writer.text()
    
    assert "<main.py>" in output or "<src/main.py>" in output
    assert "<util.py>" in output or "<src/util.py>" in output
    assert "readme.md" not in output
    assert "test_main.py" not in output


def test_main_pattern_only(prin_tmp_path: Path):
    """Test main with pattern only (searches cwd): 'prin "*.md"'"""
    import os
    old_cwd = os.getcwd()
    os.chdir(prin_tmp_path)
    
    try:
        write_file(prin_tmp_path / "readme.md", "# Readme")
        write_file(prin_tmp_path / "docs" / "guide.md", "# Guide")
        write_file(prin_tmp_path / "src" / "code.py", "# Code")
        
        writer = StringWriter()
        main(argv=["*.md"], writer=writer)
        output = writer.text()
        
        assert "<readme.md>" in output
        assert "<docs/guide.md>" in output or "<guide.md>" in output
        assert "code.py" not in output
    finally:
        os.chdir(old_cwd)


def test_main_no_args(prin_tmp_path: Path):
    """Test main with no args (lists all in cwd): 'prin'"""
    import os
    old_cwd = os.getcwd()
    os.chdir(prin_tmp_path)
    
    try:
        write_file(prin_tmp_path / "a.txt", "a")
        write_file(prin_tmp_path / "b.py", "b")
        
        writer = StringWriter()
        main(argv=[], writer=writer)
        output = writer.text()
        
        assert "<a.txt>" in output
        assert "<b.py>" in output
    finally:
        os.chdir(old_cwd)


def test_main_backwards_compatibility(prin_tmp_path: Path):
    """Test that old style with multiple paths still works"""
    write_file(prin_tmp_path / "a.txt", "a")
    write_file(prin_tmp_path / "b.txt", "b")
    write_file(prin_tmp_path / "c.txt", "c")
    
    writer = StringWriter()
    # Old style: multiple file paths
    main(argv=[
        str(prin_tmp_path / "a.txt"),
        str(prin_tmp_path / "b.txt"),
        str(prin_tmp_path / "c.txt")
    ], writer=writer)
    output = writer.text()
    
    assert "<a.txt>" in output
    assert "<b.txt>" in output
    assert "<c.txt>" in output