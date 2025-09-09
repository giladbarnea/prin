from __future__ import annotations

from typing import Iterable

from prin.adapters import github


def is_github_url(token: str) -> bool:
    try:
        return "github.com" in token and github.parse_github_url(token)
    except ValueError:
        return False


def is_http_url(token: str) -> bool:
    tok = token.strip().lower()
    return tok.startswith("http://") or tok.startswith("https://") or tok.startswith("www")


def find_github_url(argv: Iterable[str]) -> tuple[int, str] | None:
    for i, tok in enumerate(argv):
        if is_github_url(tok):
            return i, tok
    return None
