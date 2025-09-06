from __future__ import annotations

import base64
import functools
import os
import time
import random
from contextlib import suppress
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Dict, Iterable, Optional

import requests

from ..core import Entry, NodeKind, SourceAdapter

API_BASE = "https://api.github.com"
MAX_WAIT_SECONDS = 180
_GET_CACHE_MAX_BYTES = 64 * 1024 * 1024  # ~64 MiB rough cap

# Simple cache for non-streaming GET requests, keyed by (url, params, stream)
# Values are (response, size_in_bytes)
_GET_CACHE: Dict[tuple, tuple[requests.Response, int]] = {}
_GET_CACHE_TOTAL_BYTES = 0


def _auth_headers() -> Dict[str, str]:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_owner_repo(url: str) -> tuple[str, str]:
    import re

    raw = url.strip()
    if raw.startswith("git+"):
        raw = raw[4:]
    if not re.match(r"^[a-z]+://", raw):
        raw = "https://" + raw  # allow scheme-less inputs like github.com/owner/repo
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/|$)", raw)
    if not m:
        msg = f"Unrecognized GitHub URL: {url}"
        raise ValueError(msg)
    return m.group(1), m.group(2)


def _parse_rate_limit_wait_seconds(resp: requests.Response) -> Optional[int]:
    ra = resp.headers.get("Retry-After")
    if ra:
        with suppress(Exception):
            return int(float(ra))
    reset = resp.headers.get("X-RateLimit-Reset")
    if reset:
        with suppress(Exception):
            reset_ts = int(float(reset))
            now = int(time.time())
            return max(0, reset_ts - now)
    return None


def _make_hashable(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((k, _make_hashable(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_make_hashable(v) for v in value)
    if isinstance(value, set):
        return tuple(sorted(_make_hashable(v) for v in value))
    return value


def _get_cache_key(url: str, *, params: Any, stream: bool) -> tuple:
    return (url, _make_hashable(params), bool(stream))


def _get(session: requests.Session, url: str, *, params=None, stream=False) -> requests.Response:
    # Fast path: serve from cache for non-streaming requests
    cache_key = None
    global _GET_CACHE_TOTAL_BYTES
    if not stream:
        cache_key = _get_cache_key(url, params=params, stream=stream)
        cached = _GET_CACHE.get(cache_key)
        if cached is not None:
            return cached[0]

    for attempt in range(2):
        resp = session.get(url, params=params, stream=stream)
        if resp.status_code in (403, 429):
            wait = _parse_rate_limit_wait_seconds(resp)
            if wait is not None:
                if wait > MAX_WAIT_SECONDS:
                    resp.close()
                    msg = f"Rate limit wait {wait}s exceeds {MAX_WAIT_SECONDS}s"
                    raise RuntimeError(msg)
                if attempt == 0:
                    time.sleep(wait)
                    continue
        if 200 <= resp.status_code < 300:
            # Cache successful, non-streaming responses only
            if cache_key is not None:
                try:
                    resp_bytes = resp.content  # materialize bytes for sizing
                except Exception:
                    resp_bytes = b""
                size_bytes = len(resp_bytes)
                # Evict random entries until under cap
                if size_bytes > 0:
                    while _GET_CACHE_TOTAL_BYTES + size_bytes > _GET_CACHE_MAX_BYTES and _GET_CACHE:
                        rand_key = random.choice(list(_GET_CACHE.keys()))
                        _, evicted_size = _GET_CACHE.pop(rand_key)
                        _GET_CACHE_TOTAL_BYTES -= evicted_size
                    _GET_CACHE[cache_key] = (resp, size_bytes)
                    _GET_CACHE_TOTAL_BYTES += size_bytes
            return resp
        resp.raise_for_status()
    return resp


@dataclass
class _Ctx:
    owner: str
    repo: str
    ref: str


class GitHubRepoSource(SourceAdapter):
    def __init__(self, url: str, session: Optional[requests.Session] = None) -> None:
        self._session = session or requests.Session()
        self._session.headers.update(_auth_headers())
        owner, repo = _parse_owner_repo(url)
        ref = self._fetch_default_branch(owner, repo)
        self._ctx = _Ctx(owner=owner, repo=repo, ref=ref)

    @functools.lru_cache
    def _fetch_default_branch(self, owner: str, repo: str) -> str:
        r = _get(self._session, f"{API_BASE}/repos/{owner}/{repo}")
        return r.json()["default_branch"]

    def resolve_root(self, root_spec: str) -> PurePosixPath:
        # We treat the repo root as empty path
        return PurePosixPath(root_spec or "")

    def list_dir(self, dir_path: PurePosixPath) -> Iterable[Entry]:
        path = str(dir_path)
        owner, repo, ref = self._ctx.owner, self._ctx.repo, self._ctx.ref
        url = (
            f"{API_BASE}/repos/{owner}/{repo}/contents/{path}"
            if path
            else f"{API_BASE}/repos/{owner}/{repo}/contents"
        )
        r = _get(self._session, url, params={"ref": ref})
        items = r.json()
        # If the requested path is a file, emulate filesystem semantics and
        # raise NotADirectoryError so the engine treats it as an explicit file
        # root (force-include) rather than listing its contents.
        if isinstance(items, dict) and items.get("type") == "file":
            raise NotADirectoryError(path or ".")
        assert isinstance(items, list)
        entries: list[Entry] = []
        for it in items:
            it_type = it.get("type")
            it_name = it.get("name")
            it_path = it.get("path") or it_name
            kind = NodeKind.OTHER
            if it_type == "dir":
                kind = NodeKind.DIRECTORY
            elif it_type == "file":
                kind = NodeKind.FILE
            entries.append(Entry(path=PurePosixPath(it_path), name=it_name, kind=kind))
        return entries

    def read_file_bytes(self, file_path: PurePosixPath) -> bytes:
        owner, repo, ref = self._ctx.owner, self._ctx.repo, self._ctx.ref
        # Try contents API first
        r = _get(
            self._session,
            f"{API_BASE}/repos/{owner}/{repo}/contents/{str(file_path)}",
            params={"ref": ref},
        )
        info = r.json()
        if info.get("encoding") == "base64" and info.get("content"):
            with suppress(Exception):
                return base64.b64decode(info["content"], validate=False)
        dl = info.get("download_url")
        if dl:
            # Reuse shared GET with rate-limit/backoff handling
            r2 = _get(self._session, dl, stream=True)
            return r2.content
        # Fallback to blob by sha
        sha = info.get("sha")
        if sha:
            r3 = _get(self._session, f"{API_BASE}/repos/{owner}/{repo}/git/blobs/{sha}")
            data = r3.json()
            if data.get("encoding") == "base64" and data.get("content"):
                return base64.b64decode(data["content"], validate=False)
        return b""

    def is_empty(self, file_path: PurePosixPath) -> bool:
        # We need content to decide emptiness; download and apply the shared check.
        blob = self.read_file_bytes(file_path)
        from ..core import is_blob_semantically_empty

        return is_blob_semantically_empty(blob)

    # no __post_init__ needed; ref fetched during __init__
