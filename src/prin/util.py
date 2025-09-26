from __future__ import annotations

from typing import Iterable

from prin.adapters import github


def is_github_url(token: str) -> bool:
    try:
        # Accept common GitHub hosts/forms, including raw and ssh
        hostish = (
            ("github.com" in token)
            or ("raw.githubusercontent.com" in token)
            or token.startswith("git@github.com:")
        )
        return bool(hostish and github.parse_github_url(token))
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


# ---[ Functional ]---
