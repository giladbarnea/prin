from __future__ import annotations

import re

import pytest

from prin.core import DepthFirstPrinter, StringWriter
from prin.formatters import HeaderFormatter
from prin.prin import Context
from prin.adapters.github import GitHubRepoSource


pytestmark = [pytest.mark.repo, pytest.mark.network]


def _run_headers(url: str, token: str) -> str:
    src = GitHubRepoSource(url)
    printer = DepthFirstPrinter(
        src,
        HeaderFormatter(),
        ctx=Context(only_headers=True),
    )
    buf = StringWriter()
    printer.run([token], buf)
    return buf.text()


def test_repo_regex_root_matches_readme_headers_only():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run_headers(url, r"^README\\.md$")
    assert re.search(r"^README\\.md$", out, re.MULTILINE)


def test_repo_glob_root_matches_md_headers_only():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run_headers(url, "*.md")
    # Should at least include README.md somewhere
    assert re.search(r"(^|/)README\\.md$", out, re.MULTILINE)


def test_repo_regex_with_slash_matches_full_path():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run_headers(url, r"logos/README\\.md$")
    assert re.search(r"^logos/README\\.md$", out, re.MULTILINE)


def test_repo_subpath_base_relativity_pattern_simple():
    # When starting traversal at a subpath, pattern anchors and printed paths are relative to that base
    url = "https://github.com/TypingMind/awesome-typingmind/logos"
    out = _run_headers(url, r"^README\\.md$")
    assert re.search(r"^README\\.md$", out, re.MULTILINE)
    assert "logos/README.md" not in out


def test_repo_commit_regex_matches_readme_headers_only():
    # Specific commit for stability (same SHA used elsewhere in tests)
    url = (
        "https://github.com/TypingMind/awesome-typingmind/tree/"
        "d4ce90b21bc6c04642ebcf448f96357a8b474624"
    )
    out = _run_headers(url, r"^README\\.md$")
    assert re.search(r"^README\\.md$", out, re.MULTILINE)


def test_repo_pattern_no_match_yields_empty():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run_headers(url, r"^ZZZ_DOES_NOT_EXIST_12345$")
    assert out.strip() == ""

