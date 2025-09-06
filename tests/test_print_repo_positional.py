from __future__ import annotations

from prin.core import StringWriter
from prin.prin import main as prin_main


def test_repo_explicit_ignored_file_is_printed():
    # LICENSE has no extension; treat it as ignored by default, but explicit path must print it
    url = "https://github.com/TypingMind/awesome-typingmind/LICENSE"
    buf = StringWriter()
    prin_main(argv=[url], writer=buf)  # Path embedded in URL
    out = buf.text()
    assert "<LICENSE>" in out


def test_pass_two_repositories_positionally_print_both():
    url1 = "https://github.com/TypingMind/awesome-typingmind"
    url2 = "https://github.com/trouchet/rust-hello"
    buf = StringWriter()
    # Use the top-level CLI entry which supports multiple positionals naturally
    prin_main(argv=[url1, url2, ""], writer=buf)
    out = buf.text()
    assert "logos/README.md" in out
    assert "<Cargo.toml>" in out


def test_repo_dir_and_explicit_ignored_file():
    # Embed LICENSE in URL, and also traverse repo root by adding an empty root
    url = "https://github.com/TypingMind/awesome-typingmind/LICENSE"
    buf = StringWriter()
    prin_main(argv=[url, ""], writer=buf)  # default root + embedded explicit path
    out = buf.text()
    assert "<README.md>" not in out  # normal traversal doesn't print repo files
    assert "<LICENSE>" in out  # explicit inclusion prints extensionless file
