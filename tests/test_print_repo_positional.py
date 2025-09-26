from __future__ import annotations

import pytest

from prin.core import StringWriter
from prin.prin import main as prin_main

pytestmark = pytest.mark.repo


@pytest.mark.network
def test_repo_explicit_ignored_file_is_printed():
    # LICENSE has no extension; treat it as ignored by default, but explicit path must print it
    url = "https://github.com/TypingMind/awesome-typingmind/LICENSE"
    buf = StringWriter()
    prin_main(argv=[url], writer=buf)  # Path embedded in URL
    out = buf.text()
    assert "<LICENSE>" in out


@pytest.mark.network
def test_pass_two_repositories_positionally_print_both():
    url1 = "https://github.com/TypingMind/awesome-typingmind"
    url2 = "https://github.com/trouchet/rust-hello"
    buf = StringWriter()
    # Use the top-level CLI entry which supports multiple positionals naturally
    prin_main(argv=[url1, url2, ""], writer=buf)
    out = buf.text()
    assert "logos/README.md" in out
    assert "<Cargo.toml>" in out


@pytest.mark.network
def test_repo_dir_and_explicit_ignored_file():
    # Embed LICENSE in URL, and also traverse repo root by adding an empty root
    url = "https://github.com/TypingMind/awesome-typingmind/LICENSE"
    buf = StringWriter()
    prin_main(argv=[url, ""], writer=buf)  # default root + embedded explicit path
    out = buf.text()
    assert "<README.md>" not in out  # normal traversal doesn't print repo files
    assert "<LICENSE>" in out  # explicit inclusion prints extensionless file


@pytest.mark.network
def test_repo_raw_and_api_and_ssh_forms_all_work_headers_only():
    from prin.core import StringWriter
    from prin.prin import main as prin_main

    # raw.githubusercontent.com at specific ref
    raw_url = (
        "https://raw.githubusercontent.com/TypingMind/awesome-typingmind/"
        "d4ce90b21bc6c04642ebcf448f96357a8b474624/README.md"
    )
    # API contents with ref
    api_contents_url = (
        "https://api.github.com/repos/TypingMind/awesome-typingmind/contents/README.md"
        "?ref=d4ce90b21bc6c04642ebcf448f96357a8b474624"
    )
    # SSH repo root (no ref)
    ssh_url = "git@github.com:TypingMind/awesome-typingmind.git"

    buf = StringWriter()
    prin_main(argv=["--only-headers", raw_url, api_contents_url, ssh_url], writer=buf)
    out = buf.text()
    # raw/api should produce exactly README.md entries; ssh root should include LICENSE or README.md
    assert "README.md" in out
