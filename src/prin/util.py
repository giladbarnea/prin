from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

GITHUB_URL_PATTERNS: tuple[str, ...] = (
    "https://github.com/",
    "http://github.com/",
    "git+https://github.com/",
)


def is_github_url(token: str) -> bool:
    tok = token.strip().lower()
    if tok.startswith("-"):
        return False
    if any(tok.startswith(p) for p in GITHUB_URL_PATTERNS):
        return True
    # Also accept scheme-less github.com/owner/repo[...] tokens
    return tok.startswith("github.com/") or tok.startswith("www.github.com/")


def is_http_url(token: str) -> bool:
    tok = token.strip().lower()
    if tok.startswith("-"):
        return False
    return tok.startswith("http://") or tok.startswith("https://")


def find_github_url(argv: Iterable[str]) -> tuple[int, str] | None:
    for i, tok in enumerate(argv):
        if is_github_url(tok):
            return i, tok
    return None


def extract_in_repo_subpath(url: str) -> str:
    """
    Return the path inside the repo from a GitHub URL.

    Examples accepted (equivalent for subpath extraction):
    - https://github.com/<owner>/<repo>/blob/<branch>/dir/file
    - https://github.com/<owner>/<repo>/<branch>/dir/file
    - https://github.com/<owner>/<repo>/blob/dir/file
    - https://github.com/<owner>/<repo>/dir/file

    Rules:
    - Strip an initial 'blob/' segment if present.
    - Strip an initial 'main/' or 'master/' segment if present.
    - Everything after these optional segments is the subpath (may be empty).
    """
    parsed = urlparse(url)
    raw_path = (parsed.path or "").strip("/")
    if not raw_path:
        return ""
    segments = raw_path.split("/")
    if len(segments) < 2:
        return ""
    rest = segments[2:]
    if not rest:
        return ""
    if rest and rest[0] == "blob":
        rest = rest[1:]
    if rest and rest[0] in {"main", "master"}:
        rest = rest[1:]
    return "/".join(rest)
