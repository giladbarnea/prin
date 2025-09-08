from __future__ import annotations

import base64
import functools
import hashlib
import json
import os
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, Optional

import requests

from ..core import Entry, NodeKind, SourceAdapter

API_BASE = "https://api.github.com"
MAX_WAIT_SECONDS = 180
_GET_CACHE_DIR = Path("~/.cache").expanduser() / "prin" / "gh_get"


def _auth_headers() -> Dict[str, str]:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_owner_repo(url: str) -> tuple[str, str]:
    owner_repo = (
        url.strip()
        .removeprefix("git+")
        .removeprefix("http://")
        .removeprefix("https://")
        .removeprefix("www.")
        .removeprefix("api.")
        .removeprefix("github.com/")
        .removeprefix("repos/")
    )
    try:
        owner, repo, *_ = owner_repo.split("/")
    except ValueError:
        msg = f"Unrecognized GitHub URL: {url}"
        raise ValueError(msg) from None
    return owner, repo


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


def _get_cache_key(url: str, *, params: Any) -> tuple:
    return (url, _make_hashable(params))


def _get(session: requests.Session, url: str, *, params=None) -> requests.Response:
    # Fast path: serve from disk cache
    Path(_GET_CACHE_DIR).mkdir(exist_ok=True, parents=True)
    key = repr(_get_cache_key(url, params=params)).encode("utf-8")
    cache_hash = hashlib.sha256(key).hexdigest()
    body_path = _GET_CACHE_DIR / f"{cache_hash}.body"
    meta_path = _GET_CACHE_DIR / f"{cache_hash}.meta.json"
    if Path(body_path).exists():
        try:
            with open(body_path, "rb") as f:
                data = f.read()
            status = 200
            enc = "utf-8"
            if Path(meta_path).exists():
                with open(meta_path, "r", encoding="utf-8") as mf:
                    m = json.load(mf)
                    status = int(m.get("status", 200))
                    enc = m.get("encoding", "utf-8")
            resp = requests.Response()
            resp._content = data
            resp.status_code = status
            resp.url = url
            resp.encoding = enc
            return resp
        except Exception:
            with suppress(Exception):
                Path(body_path).unlink()
            with suppress(Exception):
                Path(meta_path).unlink()

    for attempt in range(2):
        resp = session.get(url, params=params)
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
            # Cache successful responses only (bytes to disk)
            try:
                data = resp.content
                with open(body_path, "wb") as f:
                    f.write(data)
                meta = {"status": int(resp.status_code), "encoding": resp.encoding or "utf-8"}
                with open(meta_path, "w", encoding="utf-8") as mf:
                    json.dump(meta, mf, separators=(",", ":"))
            except Exception:
                with suppress(Exception):
                    Path(body_path).unlink()
                with suppress(Exception):
                    Path(meta_path).unlink()
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
            r2 = _get(self._session, dl)
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
