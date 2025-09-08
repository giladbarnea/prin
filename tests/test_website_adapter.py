from __future__ import annotations

from prin.core import StringWriter
from prin.prin import main as prin_main


def test_website_llms_txt_presence_and_one_file_md_output():
    base = "https://www.fastht.ml/docs"
    buf = StringWriter()
    prin_main(argv=[base, "--max-files", "1", "--tag", "md", "--no-exclude"], writer=buf)
    out = buf.text()
    # We expect at least one markdown header for a file listed in llms.txt
    assert "# FILE: " in out or "<" in out
