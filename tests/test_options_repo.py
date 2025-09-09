from __future__ import annotations

import re

import pytest

from prin.core import StringWriter
from prin.prin import main as prin_main
from tests.utils import count_md_headers


def _run(argv: list[str]) -> str:
    buf = StringWriter()
    prin_main(argv=argv, writer=buf)
    return buf.text()


@pytest.mark.network
def test_repo_defaults_readme_present_binaries_excluded():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run(["--tag", "xml", url])

    # Defaults should include README.md
    assert "<README.md>" in out

    # Defaults should exclude binary-like files (e.g., PNGs)
    assert "<logos/made_for_typingmind.png>" not in out
    assert "<logos/made_for_typingmind_transparent.png>" not in out


@pytest.mark.network
def test_repo_include_binary_includes_pngs():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run(["--include-binary", url])
    # Binary files are emitted as self-closing tags in XML format
    assert (
        "<logos/made_for_typingmind.png" in out
        or "<logos/made_for_typingmind_transparent.png" in out
    )


@pytest.mark.network
def test_repo_no_docs_excludes_markdown_and_rst():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run(["--no-docs", url])
    assert "README.md" not in out


@pytest.mark.network
def test_repo_only_headers_prints_headers_only():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run(["--only-headers", url])
    # Expect plaintext list of file paths, one per line
    assert re.search(r"^README\.md$", out, re.MULTILINE)
    assert re.search(r"^LICENSE$", out, re.MULTILINE)
    assert re.search(r"^logos/README\.md$", out, re.MULTILINE)
    # Ensure XML tags and bodies are not present
    assert "<README.md>" not in out
    assert "</README.md>" not in out
    assert "Awesome TypingMind" not in out


@pytest.mark.network
def test_repo_extension_filters():
    rust_repo = "https://github.com/trouchet/rust-hello"
    out_rs = _run(["-e", "rs", rust_repo])
    assert "<src/main.rs>" in out_rs
    assert "<Cargo.toml>" not in out_rs
    assert "<README.md>" not in out_rs

    tm_repo = "https://github.com/TypingMind/awesome-typingmind"
    out_md = _run(["-e", "md", tm_repo])
    assert "<README.md>" in out_md
    assert "<logos/made_for_typingmind.png" not in out_md


@pytest.mark.network
def test_repo_exclude_glob_and_literal():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run(["-E", "logos", "-E", "*.md", url])
    assert "<logos/README.md>" not in out
    assert "<README.md>" not in out


@pytest.mark.network
def test_repo_no_exclude_disables_all_default_exclusions():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run(["--no-exclude", url])
    assert (
        "<logos/made_for_typingmind.png" in out
        or "<logos/made_for_typingmind_transparent.png" in out
    )


@pytest.mark.network
def test_repo_tag_md_outputs_markdown_format():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run(["--tag", "md", url])
    assert count_md_headers(out) > 0
    assert "# FILE: README.md" in out


@pytest.mark.network
def test_repo_include_empty():
    # Use a repo that has a file with only a comment and an import
    # The file "__init__.py.py" contains a comment and an import, which should be semantically empty
    url = "https://github.com/mahin-mushfique/scrapers"
    out = _run(["--include-empty", url])
    assert "<__init__.py.py>" in out


@pytest.mark.network
def test_repo_include_lock():
    url = "https://github.com/trouchet/rust-hello"
    out = _run(["--include-lock", url])
    assert "<Cargo.lock>" in out


@pytest.mark.skip("Not supported ATM")
def test_repo_no_ignore():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run(["--no-ignore", url])
    assert isinstance(out, str)
