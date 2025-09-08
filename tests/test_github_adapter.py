# Parametrize with pytest:
import pytest

from prin.adapters.github import _parse_owner_repo


@pytest.mark.parametrize(
    "url",
    [
        "http://www.github.com/TypingMind/awesome-typingmind",
        "https://www.github.com/TypingMind/awesome-typingmind",
        "http://github.com/TypingMind/awesome-typingmind",
        "https://github.com/TypingMind/awesome-typingmind",
        "www.github.com/TypingMind/awesome-typingmind",
        "github.com/TypingMind/awesome-typingmind",
        "https://api.github.com/repos/TypingMind/awesome-typingmind/git/trees/master",
        "git+https://github.com/TypingMind/awesome-typingmind",
    ],
)
def test_parse_owner_repo(url):
    owner, repo = _parse_owner_repo(url)
    assert owner == "TypingMind"
    assert repo == "awesome-typingmind"
