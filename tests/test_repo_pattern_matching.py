from __future__ import annotations

import re

import pytest

from prin.core import StringWriter
from prin.prin import main as prin_main


pytestmark = [pytest.mark.repo, pytest.mark.network]


def _run_headers_single_arg(arg: str) -> str:
    buf = StringWriter()
    prin_main(argv=["--only-headers", arg], writer=buf)
    return buf.text()


def test_repo_regex_root_matches_readme_headers_only():
    arg = "github.com/TypingMind/awesome-typingmind/^README\\.md$"
    out = _run_headers_single_arg(arg)
    assert re.search(r"^README\\.md$", out, re.MULTILINE)


def test_repo_glob_root_matches_md_headers_only():
    arg = "github.com/TypingMind/awesome-typingmind/*.md"
    out = _run_headers_single_arg(arg)
    assert re.search(r"(^|/)README\\.md$", out, re.MULTILINE)


def test_repo_regex_with_slash_matches_full_path():
    arg = r"github.com/TypingMind/awesome-typingmind/logos/README\\.md$"
    out = _run_headers_single_arg(arg)
    assert re.search(r"^logos/README\\.md$", out, re.MULTILINE)


def test_repo_subpath_base_relativity_pattern_simple():
    arg = r"github.com/TypingMind/awesome-typingmind/logos/^README\\.md$"
    out = _run_headers_single_arg(arg)
    assert re.search(r"^README\\.md$", out, re.MULTILINE)
    assert "logos/README.md" not in out


def test_repo_commit_regex_matches_readme_headers_only():
    arg = (
        r"github.com/TypingMind/awesome-typingmind/tree/"
        r"d4ce90b21bc6c04642ebcf448f96357a8b474624/^README\\.md$"
    )
    out = _run_headers_single_arg(arg)
    assert re.search(r"^README\\.md$", out, re.MULTILINE)


def test_repo_pattern_no_match_yields_empty():
    arg = r"github.com/TypingMind/awesome-typingmind/^ZZZ_DOES_NOT_EXIST_12345$"
    out = _run_headers_single_arg(arg)
    assert out.strip() == ""

