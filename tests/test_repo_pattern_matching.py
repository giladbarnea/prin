from __future__ import annotations

import re

import pytest

from prin.core import StringWriter
from prin.prin import main as prin_main


pytestmark = [pytest.mark.repo, pytest.mark.network]


def _run_headers_single_arg(arg: str) -> str:
    buf = StringWriter()
    import os
    mock_root = os.path.join("tests", "data", "repo_mocks", "TypingMind", "awesome-typingmind")
    os.environ.setdefault("PRIN_GH_MOCK_ROOT", mock_root)
    prin_main(argv=["--only-headers", arg], writer=buf)
    return buf.text()


def test_repo_regex_root_matches_readme_headers_only():
    arg = "github.com/TypingMind/awesome-typingmind/^README\.md$"
    out = _run_headers_single_arg(arg)
    assert re.search(r"^README\.md$", out, re.MULTILINE)


def test_repo_glob_root_matches_md_headers_only():
    arg = "github.com/TypingMind/awesome-typingmind/*.md"
    out = _run_headers_single_arg(arg)
    assert re.search(r"(^|/)README\.md$", out, re.MULTILINE)


def test_repo_regex_with_slash_matches_full_path():
    arg = r"github.com/TypingMind/awesome-typingmind/logos/README\.md$"
    out = _run_headers_single_arg(arg)
    # When pattern includes a subpath base, printed paths are relative to that base
    assert re.search(r"^README\.md$", out, re.MULTILINE)


def test_repo_subpath_base_relativity_pattern_simple():
    arg = r"github.com/TypingMind/awesome-typingmind/logos/^README\.md$"
    out = _run_headers_single_arg(arg)
    assert re.search(r"^README\.md$", out, re.MULTILINE)
    assert "logos/README.md" not in out


def test_repo_commit_regex_matches_readme_headers_only():
    arg = (
        r"github.com/TypingMind/awesome-typingmind/tree/"
        r"d4ce90b21bc6c04642ebcf448f96357a8b474624/^README\.md$"
    )
    out = _run_headers_single_arg(arg)
    assert re.search(r"^README\.md$", out, re.MULTILINE)


def test_repo_pattern_no_match_yields_empty():
    arg = r"github.com/TypingMind/awesome-typingmind/^ZZZ_DOES_NOT_EXIST_12345$"
    out = _run_headers_single_arg(arg)
    assert out.strip() == ""


def test_repo_glob_under_subpath_matches():
    arg = "github.com/TypingMind/awesome-typingmind/logos/*.md"
    out = _run_headers_single_arg(arg)
    assert re.search(r"^README\.md$", out, re.MULTILINE)


def test_repo_exclusions_interplay_with_pattern_then_no_exclude_includes():
    # README.md is a docs file; with --no-docs it would be excluded, but default no-docs=False includes docs.
    # Use a default-excluded type instead: a PNG under logos should be excluded by default but included with --no-exclude.
    # First ensure it's excluded by default even if pattern matches (only headers)
    arg_png = r"github.com/TypingMind/awesome-typingmind/logos/.*\.png$"
    out_default = _run_headers_single_arg(arg_png)
    assert not re.search(r"\.png$", out_default, re.MULTILINE)
    # Now include everything
    buf = StringWriter()
    prin_main(argv=["--only-headers", "--no-exclude", arg_png], writer=buf)
    out_no_excl = buf.text()
    assert re.search(r"\.png$", out_no_excl, re.MULTILINE)


def test_repo_extensions_with_pattern_filters():
    # With -e md and a broad pattern, only md files should appear
    arg = r"github.com/TypingMind/awesome-typingmind/README"
    buf = StringWriter()
    prin_main(argv=["--only-headers", "-e", "md", arg], writer=buf)
    out = buf.text()
    assert re.search(r"^README\.md$", out, re.MULTILINE)

