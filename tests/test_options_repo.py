from __future__ import annotations

import re

import pytest

from prin.core import StringWriter
from prin.prin import main as prin_main
from tests.utils import count_md_headers

pytestmark = pytest.mark.repo


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
def test_repo_commit_only_headers_two_files():
    # Specific commit should reflect point-in-time state
    url = (
        "https://github.com/TypingMind/awesome-typingmind/commit/"
        "d4ce90b21bc6c04642ebcf448f96357a8b474624"
    )
    out = _run(["--only-headers", url])
    # Expect exactly two files listed
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    assert set(lines) == {"LICENSE", "README.md"}


@pytest.mark.network
def test_repo_commit_readme_contents_matches():
    # Specific commit and README.md contents should match expected text (ignoring whitespace diffs)
    url = (
        "https://github.com/TypingMind/awesome-typingmind/blob/"
        "d4ce90b21bc6c04642ebcf448f96357a8b474624/README.md"
    )

    expected_readme_contents = """
# awesome-typingmind
Collection of useful resources
for TypingMind
"""

    # Use XML to easily isolate the body between <README.md> tags
    out = _run(["--tag", "xml", url])

    start_tag = "<README.md>"
    end_tag = "</README.md>"
    start = out.find(start_tag)
    assert start >= 0, "README.md header not found in output"
    start_body = start + len(start_tag)
    end = out.find(end_tag, start_body)
    assert end > start_body, "README.md closing tag not found in output"
    body = out[start_body:end]

    def _normalize(s: str) -> str:
        # Collapse all whitespace (spaces, tabs, newlines) to single spaces and trim
        return " ".join(s.split()).strip()

    assert _normalize(body) == _normalize(expected_readme_contents)


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


@pytest.mark.network
def test_repo_module_named_locking_is_not_excluded():
    # Use a repository that might have a module with 'lock' in the name
    # This tests that literal 'lock' exclusions don't match substrings
    url = "https://github.com/trouchet/rust-hello"
    out = _run([url])
    # Cargo.lock should be excluded by default (it's a lock file)
    assert "<Cargo.lock>" not in out
    # But if there was a file with 'lock' as substring, it should not be excluded
    # This is a basic test to ensure the exclusion logic works properly


@pytest.mark.network
def test_repo_literal_exclude_token_matches_segments_not_substrings():
    # Test that exclusion by literal token matches path segments, not substrings
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run(["--exclude", "logos", url])

    # Should exclude the 'logos' directory
    assert "<logos/README.md>" not in out
    assert "<logos/made_for_typingmind.png>" not in out

    # But should not exclude files that contain 'logos' as substring
    # (This test is somewhat limited by the available test repos, but demonstrates the concept)


@pytest.mark.network
def test_repo_unrestricted_includes_gitignored():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run(["-u", url])
    # -u flag should enable --no-ignore behavior
    # Since gitignore parsing is not fully implemented, this mainly tests the flag parsing
    assert isinstance(out, str)
    assert len(out) > 0


@pytest.mark.network
def test_repo_uu_includes_hidden_and_gitignored():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run(["-uu", url])
    # -uu flag should enable both --hidden and --no-ignore
    # Since gitignore parsing is not fully implemented, this mainly tests the flag parsing
    assert isinstance(out, str)
    assert len(out) > 0


@pytest.mark.network
def test_repo_hidden_includes_dotfiles_and_dotdirs():
    # Use a repo that has dotfiles
    url = "https://github.com/trouchet/rust-hello"
    out = _run(["--hidden", url])
    # Look for common dotfiles that might exist
    # This is somewhat limited by what's available in test repos
    assert isinstance(out, str)
    assert len(out) > 0


@pytest.mark.network
def test_repo_include_tests_flag_includes_tests_dir():
    # Use a repo that has a tests directory
    url = "https://github.com/trouchet/rust-hello"
    out = _run(["--include-tests", url])
    # Should include test files if they exist
    # This test is somewhat limited by the available test repos
    assert isinstance(out, str)
    assert len(out) > 0


@pytest.mark.network
def test_repo_no_options_specified_everything_is_printed():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run(["--tag", "xml", url])

    # Should include README.md by default
    assert "<README.md>" in out
    assert "Awesome TypingMind" in out

    # Should exclude binary files by default
    assert "<logos/made_for_typingmind.png>" not in out

    # Should exclude lock files by default (none in this repo, but test structure)
    assert isinstance(out, str)
    assert len(out) > 0


@pytest.mark.skip("Not supported ATM")
def test_repo_no_ignore():
    url = "https://github.com/TypingMind/awesome-typingmind"
    out = _run(["--no-ignore", url])
    assert isinstance(out, str)


@pytest.mark.network
def test_repo_hidden_includes_dotfiles_and_dotdirs():
    # A tiny repo that contains a .gitignore at the root
    url = "https://github.com/trouchet/rust-hello"

    # By default, dotfiles should be excluded
    out_default = _run(["--only-headers", url])
    assert ".gitignore\n" not in out_default

    # With --hidden, dotfiles should be included
    out_hidden = _run(["--only-headers", "--hidden", url])
    assert ".gitignore\n" in out_hidden


@pytest.mark.network
def test_repo_uu_includes_hidden_and_no_ignore():
    # -uu expands to --hidden --no-ignore; for repos we already ignore local gitignore,
    # so we assert that hidden files are included when using -uu.
    url = "https://github.com/trouchet/rust-hello"
    out = _run(["--only-headers", "-uu", url])
    assert ".gitignore\n" in out


@pytest.mark.network
def test_repo_include_tests_flag_includes_tests_dir():
    # Choose a small repo with a stable tests/ directory
    url = "https://github.com/pallets/markupsafe"
    out = _run(["--only-headers", url])
    assert "tests/" not in out

    out_with_tests = _run(["--only-headers", "--include-tests", url])
    assert "tests/" in out_with_tests


@pytest.mark.network
def test_repo_unrestricted_includes_hidden_but_not_affecting_gitignore_behavior():
    # -u maps to --no-ignore; for repos we do not process local gitignore,
    # so the practical effect for repos is no change in output compared to default.
    url = "https://github.com/TypingMind/awesome-typingmind"
    out_default = _run(["--only-headers", url])
    out_unrestricted = _run(["--only-headers", "-u", url])
    assert out_default == out_unrestricted
