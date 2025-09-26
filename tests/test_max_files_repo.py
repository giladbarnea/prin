from __future__ import annotations

import pytest

from prin.core import StringWriter
from prin.prin import main as prin_main
from tests.utils import count_md_headers

pytestmark = pytest.mark.repo


@pytest.mark.network
def test_repo_max_files_one():
    url = "https://github.com/TypingMind/awesome-typingmind"
    buf = StringWriter()
    prin_main(argv=[url, "--max-files", "1", "--tag", "md"], writer=buf)
    out = buf.text()
    assert count_md_headers(out) == 1
