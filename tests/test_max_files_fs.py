from __future__ import annotations

from pathlib import Path

from prin.core import StringWriter
from prin.prin import main as prin_main
from tests.utils import count_opening_xml_tags, write_file


def test_max_files_limits_printed_files_all_included(tmp_path: Path):
    # Build a small tree with 5 printable files
    write_file(tmp_path / "a.py", "print('a')\n")
    write_file(tmp_path / "b.py", "print('b')\n")
    write_file(tmp_path / "dir" / "c.py", "print('c')\n")
    write_file(tmp_path / "dir" / "d.py", "print('d')\n")
    write_file(tmp_path / "dir" / "sub" / "e.py", "print('e')\n")

    buf = StringWriter()
    prin_main(argv=["--include-tests", "--max-files", "4", str(tmp_path)], writer=buf)
    out = buf.text()
    assert count_opening_xml_tags(out) == 4


def test_max_files_skips_non_matching_and_still_prints_four(tmp_path: Path):
    # 4 printable files and one .lock that should not match by default extensions
    write_file(tmp_path / "a.lock", "dummy\n")  # ensure it sorts early among files
    write_file(tmp_path / "a.py", "print('a')\n")
    write_file(tmp_path / "dir" / "b.py", "print('b')\n")
    write_file(tmp_path / "dir" / "c.py", "print('c')\n")
    write_file(tmp_path / "dir" / "sub" / "d.py", "print('d')\n")

    buf = StringWriter()
    prin_main(argv=["--include-tests", "--max-files", "4", str(tmp_path)], writer=buf)
    out = buf.text()
    assert count_opening_xml_tags(out) == 4
