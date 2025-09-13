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
from typing import Any, Dict, Iterable, Optional, TypedDict

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


class GitHubURL(TypedDict, total=False):
    owner: str
    repo: str
    subpath: str
    # Optional git ref (branch, tag, or commit SHA) if present in the URL
    ref: str


def parse_github_url(url: str) -> GitHubURL:
    """
    Parse a GitHub URL into owner, repo, optional ref, and subpath.

    Supports common forms:
    - https://github.com/{owner}/{repo}
    - https://github.com/{owner}/{repo}/tree/{ref}/{path?}
    - https://github.com/{owner}/{repo}/blob/{ref}/{path}
    - https://github.com/{owner}/{repo}/commit/{sha}
    - https://api.github.com/repos/{owner}/{repo}/...

    Raises ValueError if the URL is not a valid GitHub URL.
    """
    raw = (
        url.strip()
        .removeprefix("git+")
        .removeprefix("http://")
        .removeprefix("https://")
        .removeprefix("www.")
        .removeprefix("api.")
        .removeprefix("github.com/")
        .removeprefix("repos/")
        .removesuffix("/")
    )

    # Split into path segments once normalized
    parts = [p for p in raw.split("/") if p]
    if len(parts) < 2:
        msg = f"Unrecognized GitHub URL: {url}"
        raise ValueError(msg)

    owner, repo = parts[0], parts[1]
    rest = parts[2:]

    ref: str | None = None
    subpath_parts: list[str] = []

    # Handle special patterns if present
    if rest[:1] == ["commit"] and len(rest) >= 2:
        # owner/repo/commit/<sha>
        ref = rest[1]
        subpath_parts = []
    elif rest[:1] == ["tree"] and len(rest) >= 2:
        # owner/repo/tree/<ref>/optional/sub/path
        ref = rest[1]
        subpath_parts = rest[2:]
    elif rest[:1] == ["blob"] and len(rest) >= 2:
        # owner/repo/blob/<ref>/file/or/path
        ref = rest[1]
        subpath_parts = rest[2:]
    else:
        # Treat everything after repo as a subpath. No explicit ref.
        subpath_parts = rest

    data: GitHubURL = {
        "owner": owner,
        "repo": repo,
        "subpath": "/".join(subpath_parts),
    }
    if ref:
        data["ref"] = ref
    return data


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
        parsed_github_url: GitHubURL = parse_github_url(url)
        owner, repo = parsed_github_url["owner"], parsed_github_url["repo"]
        # Prefer explicit ref from URL (commit sha, tag, branch). Fallback to default branch.
        ref = parsed_github_url.get("ref") or self._fetch_default_branch(owner, repo)
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
        file_contents_response = _get(
            self._session,
            f"{API_BASE}/repos/{owner}/{repo}/contents/{str(file_path)}",
            params={"ref": ref},
        )
        info = file_contents_response.json()
        if info.get("encoding") == "base64" and info.get("content"):
            with suppress(Exception):
                return base64.b64decode(info["content"], validate=False)
        download_url = info.get("download_url")
        if download_url:
            # Reuse shared GET with rate-limit/backoff handling
            downloaded_file_response = _get(self._session, download_url)
            return downloaded_file_response.content
        # Fallback to blob by sha
        sha = info.get("sha")
        if sha:
            blob_response = _get(self._session, f"{API_BASE}/repos/{owner}/{repo}/git/blobs/{sha}")
            data = blob_response.json()
            if data.get("encoding") == "base64" and data.get("content"):
                return base64.b64decode(data["content"], validate=False)
        return b""

    def is_empty(self, file_path: PurePosixPath) -> bool:
        # We need content to decide emptiness; download and apply the shared check.
        blob = self.read_file_bytes(file_path)
        from ..core import is_blob_semantically_empty

        return is_blob_semantically_empty(blob, file_path)
