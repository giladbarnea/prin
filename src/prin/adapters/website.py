from __future__ import annotations

import hashlib
import json
import os
import re
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, List
from urllib.parse import urljoin, urlparse

import requests

from ..core import Entry, NodeKind, SourceAdapter, _decode_text, _is_text_bytes
from ..filters import extension_match, is_excluded


def _ensure_trailing_slash(url: str) -> str:
    return url if url.endswith("/") else url + "/"


_GET_CACHE_DIR = Path("~/.cache").expanduser() / "prin" / "web_get"


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


def _get(
    session: requests.Session, url: str, *, params=None, timeout: int | float | None = None
) -> requests.Response:
    # Allow disabling cache via env (useful for tests that monkeypatch requests)
    disable_cache = os.getenv("PRIN_DISABLE_WEB_CACHE", "").lower() in {"1", "true", "yes"}
    # Disk cache: serve from local cache when available
    Path(_GET_CACHE_DIR).mkdir(exist_ok=True, parents=True)
    key = repr(_get_cache_key(url, params=params)).encode("utf-8")
    cache_hash = hashlib.sha256(key).hexdigest()
    body_path = _GET_CACHE_DIR / f"{cache_hash}.body"
    meta_path = _GET_CACHE_DIR / f"{cache_hash}.meta.json"
    if not disable_cache and Path(body_path).exists():
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

    resp = session.get(url, params=params, timeout=timeout)
    if 200 <= resp.status_code < 300:
        try:
            if not disable_cache:
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


def _parse_llms_txt(text: str) -> List[str]:
    urls: List[str] = []
    md_link_re = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
    raw_url_re = re.compile(r"https?://[^\s)]+")

    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#") or s.startswith(">"):
            continue
        # Strip common list markers
        for prefix in ("- ", "* ", "• "):
            if s.startswith(prefix):
                s = s[len(prefix) :].strip()
                break

        m = md_link_re.search(s)
        if m:
            urls.append(m.group(1))
            continue
        m2 = raw_url_re.search(s)
        if m2:
            urls.append(m2.group(0))
            continue
    return urls


@dataclass
class _Ctx:
    base_url: str
    urls: List[str]
    key_to_url: dict[str, str]


class WebsiteSource(SourceAdapter):
    """
    Website adapter that expects an llms.txt file under the provided base URL.
    - resolve: takes a base website URL (e.g., https://example.com/docs)
    - list_dir: returns entries corresponding to URLs listed in llms.txt as FILE nodes
    - read_file_bytes: downloads the content at the URL
    - is_empty: always False (emptiness determined later after download)
    """

    def __init__(self, base_url: str, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()
        self._ctx: _Ctx | None = None
        self._base_url = base_url
        # Adapter configuration (from Context)
        self._exclusions: list[str] = []
        self._extensions: list[str] = []
        self._include_empty: bool = False

    def _ensure_ctx(self) -> _Ctx:
        if self._ctx is not None:
            return self._ctx
        base = self._base_url.strip()
        if not base.startswith("http://") and not base.startswith("https://"):
            base = "https://" + base
        base = _ensure_trailing_slash(base)
        llms_url = base + "llms.txt"
        # If llms.txt is not found, raise FileNotFoundError as per spec (fails if doesn't exist)
        r = _get(self._session, llms_url, timeout=20)
        if r.status_code == 404:
            raise FileNotFoundError(llms_url)
        if r.status_code >= 400:
            r.raise_for_status()  # will raise HTTPError
        text = r.text
        urls = _parse_llms_txt(text)
        # Normalize to absolute URLs; if any entry is relative, resolve against base
        resolved: List[str] = []
        key_to_url: dict[str, str] = {}

        for u in urls:
            abs_u = urljoin(base, u)
            resolved.append(abs_u)
            # Create a stable display key (basename; if empty, use host)
            p = urlparse(abs_u)
            key = Path(p.path.rstrip("/")).name or p.netloc
            # Deduplicate keys if needed
            if key in key_to_url:
                i = 2
                while f"{key}.{i}" in key_to_url:
                    i += 1
                key = f"{key}.{i}"
            key_to_url[key] = abs_u

        self._ctx = _Ctx(base_url=base, urls=resolved, key_to_url=key_to_url)
        return self._ctx

    def resolve(self, root_spec: str) -> PurePosixPath:
        # Treat the list as a virtual directory root
        self._ensure_ctx()
        return PurePosixPath()

    # region --- Adapter SRP additions ---
    def configure(self, ctx) -> None:
        self._exclusions = ctx.exclusions
        self._extensions = ctx.extensions
        self._include_empty = ctx.include_empty

    def walk(self, token: str) -> Iterable[Entry]:
        ctx = self._ensure_ctx()
        # Flat list; yield in case-insensitive order
        for key in sorted(ctx.key_to_url.keys(), key=lambda s: s.casefold()):
            yield Entry(
                path=PurePosixPath(key),
                name=key,
                kind=NodeKind.FILE,
                abs_path=PurePosixPath(key),
            )

    def should_print(self, entry: Entry) -> bool:
        if entry.explicit:
            return True
        dummy = Entry(path=entry.path, name=entry.name, kind=entry.kind)
        if is_excluded(dummy, exclude=self._exclusions):
            return False
        if not extension_match(dummy, extensions=self._extensions):
            return False
        # Website emptiness is determined after fetch; include_empty gate is enforced in printer via our return here only if is_empty()==True, but website is_empty returns False pre-fetch. So we don't exclude by emptiness here.
        return True

    def read_body_text(self, entry: Entry) -> tuple[str | None, bool]:
        blob = self.read_file_bytes(entry.abs_path or entry.path)
        if _is_text_bytes(blob):
            return _decode_text(blob), False
        return None, True
    # endregion --- Adapter SRP additions ---

    def list_dir(self, dir_path: PurePosixPath) -> Iterable[Entry]:
        ctx = self._ensure_ctx()
        entries: list[Entry] = []
        for key in ctx.key_to_url:
            name = key
            # Use key as the logical path; actual URL is kept in mapping
            entries.append(Entry(path=PurePosixPath(key), name=name, kind=NodeKind.FILE))
        # No subdirectories; emulate NotADirectoryError if dir_path points to a specific URL
        if str(dir_path) and str(dir_path) not in (".", "/"):
            raise NotADirectoryError(str(dir_path))
        return entries

    def read_file_bytes(self, file_path: PurePosixPath) -> bytes:
        ctx = self._ensure_ctx()
        key = str(file_path)
        url = ctx.key_to_url.get(key)
        if not url:
            # Fallback: if key is a full URL by chance
            url = key
        r = _get(self._session, url, timeout=30)
        r.raise_for_status()
        return r.content

    def is_empty(self, file_path: PurePosixPath) -> bool:
        # Defer emptiness determination to shared semantic check after read
        return False
