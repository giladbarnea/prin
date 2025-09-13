# Parametrize with pytest:
import pytest

from prin.adapters.github import GitHubURL, parse_github_url


@pytest.mark.parametrize(
    "url",
    [
        "http://www.github.com/TypingMind/awesome-typingmind",
        "https://www.github.com/TypingMind/awesome-typingmind",
        "http://github.com/TypingMind/awesome-typingmind",
        "https://github.com/TypingMind/awesome-typingmind",
        "www.github.com/TypingMind/awesome-typingmind",
        "github.com/TypingMind/awesome-typingmind",
        "github.com/TypingMind/awesome-typingmind/",
        "github.com/TypingMind/awesome-typingmind/README.md",
        "github.com/TypingMind/awesome-typingmind/blob/README.md",
        "github.com/TypingMind/awesome-typingmind/logos/logo.png",
        "github.com/TypingMind/awesome-typingmind/blob/logos/logo.png",
        # Ensure optional branch prefixes after blob/ are stripped
        "github.com/TypingMind/awesome-typingmind/blob/master/logos/logo.png",
        "github.com/TypingMind/awesome-typingmind/blob/main/logos/logo.png",
        "https://api.github.com/repos/TypingMind/awesome-typingmind/git/trees/master",
        "git+https://github.com/TypingMind/awesome-typingmind",
    ],
)
def test_parse_owner_repo(url):
    parsed_github_url: GitHubURL = parse_github_url(url)
    owner = parsed_github_url["owner"]
    repo = parsed_github_url["repo"]
    assert owner == "TypingMind"
    assert repo == "awesome-typingmind"


@pytest.mark.parametrize(
    "url, exp_ref, exp_subpath",
    [
        # tree at ref (root and with subpath)
        (
            "https://github.com/TypingMind/awesome-typingmind/tree/d4ce90b21bc6c04642ebcf448f96357a8b474624",
            "d4ce90b21bc6c04642ebcf448f96357a8b474624",
            "",
        ),
        (
            "https://github.com/TypingMind/awesome-typingmind/tree/d4ce90b21bc6c04642ebcf448f96357a8b474624/logos",
            "d4ce90b21bc6c04642ebcf448f96357a8b474624",
            "logos",
        ),
        # blob at ref (with query and fragment)
        (
            "https://github.com/TypingMind/awesome-typingmind/blob/d4ce90b21bc6c04642ebcf448f96357a8b474624/README.md?plain=1#L1-L10",
            "d4ce90b21bc6c04642ebcf448f96357a8b474624",
            "README.md",
        ),
        # blob at ref with fragment-only line range (strip #Lstart-Lend)
        (
            "https://github.com/TypingMind/awesome-typingmind/blob/d4ce90b21bc6c04642ebcf448f96357a8b474624/README.md#L5-L20",
            "d4ce90b21bc6c04642ebcf448f96357a8b474624",
            "README.md",
        ),
        # blob at ref with single-line fragment (strip #Lnum)
        (
            "https://github.com/TypingMind/awesome-typingmind/blob/d4ce90b21bc6c04642ebcf448f96357a8b474624/README.md#L12",
            "d4ce90b21bc6c04642ebcf448f96357a8b474624",
            "README.md",
        ),
        # commit with short SHA (parsing only)
        (
            "https://github.com/TypingMind/awesome-typingmind/commit/d4ce90b",
            "d4ce90b",
            "",
        ),
        # API contents with ref query param
        (
            "https://api.github.com/repos/TypingMind/awesome-typingmind/contents/README.md?ref=d4ce90b21bc6c04642ebcf448f96357a8b474624",
            "d4ce90b21bc6c04642ebcf448f96357a8b474624",
            "README.md",
        ),
        # API contents at root with ref
        (
            "https://api.github.com/repos/TypingMind/awesome-typingmind/contents?ref=d4ce90b21bc6c04642ebcf448f96357a8b474624",
            "d4ce90b21bc6c04642ebcf448f96357a8b474624",
            "",
        ),
        # API git trees with ref
        (
            "https://api.github.com/repos/TypingMind/awesome-typingmind/git/trees/d4ce90b21bc6c04642ebcf448f96357a8b474624",
            "d4ce90b21bc6c04642ebcf448f96357a8b474624",
            "",
        ),
        # Raw content URL
        (
            "https://raw.githubusercontent.com/TypingMind/awesome-typingmind/d4ce90b21bc6c04642ebcf448f96357a8b474624/README.md",
            "d4ce90b21bc6c04642ebcf448f96357a8b474624",
            "README.md",
        ),
        # Strip trailing slash and .git
        (
            "https://github.com/TypingMind/awesome-typingmind.git/",
            None,
            "",
        ),
        # SSH/clone form
        (
            "git@github.com:TypingMind/awesome-typingmind.git",
            None,
            "",
        ),
    ],
)
def test_parse_ref_and_subpath(url, exp_ref, exp_subpath):
    parsed: GitHubURL = parse_github_url(url)
    assert parsed["owner"] == "TypingMind"
    assert parsed["repo"] == "awesome-typingmind"
    # ref key should always exist (may be None)
    assert "ref" in parsed
    assert parsed["ref"] == exp_ref
    assert parsed["subpath"] == exp_subpath
