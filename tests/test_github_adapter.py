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
