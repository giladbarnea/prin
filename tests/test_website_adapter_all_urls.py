from __future__ import annotations

import re
from collections import defaultdict

import pytest
import requests

from prin.core import StringWriter
from prin.prin import main as prin_main

LLMS_TXT = """# FastHTML

> FastHTML is a python library which brings together Starlette, Uvicorn, HTMX, and fastcore's `FT` "FastTags" into a library for creating server-rendered hypermedia applications. The `FastHTML` class itself inherits from `Starlette`, and adds decorator-based routing with many additions, Beforeware, automatic `FT` to HTML rendering, and much more.

Things to remember when writing FastHTML apps:

- Although parts of its API are inspired by FastAPI, it is *not* compatible with FastAPI syntax and is not targeted at creating API services
- FastHTML includes support for Pico CSS and the fastlite sqlite library, although using both are optional; sqlalchemy can be used directly or via the fastsql library, and any CSS framework can be used. Support for the Surreal and css-scope-inline libraries are also included, but both are optional
- FastHTML is compatible with JS-native web components and any vanilla JS library, but not with React, Vue, or Svelte
- Use `serve()` for running uvicorn (`if __name__ == "__main__"` is not needed since it's automatic)
- When a title is needed with a response, use `Titled`; note that that already wraps children in `Container`, and already includes both the meta title as well as the H1 element.

## Docs

- [FastHTML concise guide](https://www.fastht.ml/docs/ref/concise_guide.html.md): A brief overview of idiomatic FastHTML apps
- [HTMX reference](https://raw.githubusercontent.com/bigskysoftware/htmx/master/www/content/reference.md): Brief description of all HTMX attributes, CSS classes, headers, events, extensions, js lib methods, and config options
- [Starlette quick guide](https://gist.githubusercontent.com/jph00/e91192e9bdc1640f5421ce3c904f2efb/raw/61a2774912414029edaf1a55b506f0e283b93c46/starlette-quick.md): A quick overview of some Starlette features useful to FastHTML devs.

## API

- [API List](https://www.fastht.ml/docs/apilist.txt): A succint list of all functions and methods in fasthtml.
- [MonsterUI API List](https://raw.githubusercontent.com/AnswerDotAI/MonsterUI/refs/heads/main/docs/apilist.txt): Complete API Reference for Monster UI, a component framework similar to shadcn, but for FastHTML


## Examples

- [Websockets application](https://raw.githubusercontent.com/AnswerDotAI/fasthtml/main/examples/basic_ws.py): Very brief example of using websockets with HTMX and FastHTML
- [Todo list application](https://raw.githubusercontent.com/AnswerDotAI/fasthtml/main/examples/adv_app.py): Detailed walk-thru of a complete CRUD app in FastHTML showing idiomatic use of FastHTML and HTMX patterns.

## Optional

- [Surreal](https://raw.githubusercontent.com/AnswerDotAI/surreal/main/README.md): Tiny jQuery alternative for plain Javascript with inline Locality of Behavior, providing `me` and `any` functions
- [Starlette full documentation](https://gist.githubusercontent.com/jph00/809e4a4808d4510be0e3dc9565e9cbd3/raw/9b717589ca44cedc8aaf00b2b8cacef922964c0f/starlette-sml.md): A subset of the Starlette documentation useful for FastHTML development.
- [JS App Walkthrough](https://www.fastht.ml/docs/tutorials/e2e.html.md): An end-to-end walkthrough of a complete FastHTML app, including deployment to railway.
- [FastHTML by Example](https://www.fastht.ml/docs/tutorials/by_example.html.md): A collection of 4 FastHTML apps showcasing idiomatic use of FastHTML and HTMX patterns.
- [Using Jupyter to write FastHTML](https://www.fastht.ml/docs/tutorials/jupyter_and_fasthtml.html.md): A guide to developing FastHTML apps inside Jupyter notebooks.
- [FT Components](https://www.fastht.ml/docs/explains/explaining_xt_components.html.md): Explanation of the `FT` components, which are a way to write HTML in a Pythonic way.
- [FAQ](https://www.fastht.ml/docs/explains/faq.html.md): Answers to common questions about FastHTML.
- [MiniDataAPI Spec](https://www.fastht.ml/docs/explains/minidataapi.html.md): Explanation of the MiniDataAPI specification, which allows us to use the same API for many different database engines.
- [OAuth](https://www.fastht.ml/docs/explains/oauth.html.md): Tutorial and explanation of how to use OAuth in FastHTML apps.
- [Routes](https://www.fastht.ml/docs/explains/routes.html.md): Explanation of how routes work in FastHTML.
- [WebSockets](https://www.fastht.ml/docs/explains/websockets.html.md): Explanation of websockets and how they work in FastHTML.
- [Custom Components](https://www.fastht.ml/docs/ref/defining_xt_component.md): Explanation of how to create custom components in FastHTML.
- [Handling Handlers](https://www.fastht.ml/docs/ref/handlers.html.md): Explanation of how to request and response handlers work in FastHTML as routes.
- [Live Reloading](https://www.fastht.ml/docs/ref/live_reload.html.md): Explanation of how to use live reloading for FastHTML development.
"""


def _extract_markdown_urls(text: str) -> list[str]:
    pat = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
    return [m.group(1) for m in pat.finditer(text)]


def _dedup_basename(basename: str, seen: dict[str, int]) -> str:
    seen[basename] += 1
    cnt = seen[basename]
    return basename if cnt == 1 else f"{basename}.{cnt}"


@pytest.mark.network
def test_all_llms_txt_markdown_urls_are_loaded(monkeypatch: pytest.MonkeyPatch):
    base = "https://www.fastht.ml/docs"
    expected_urls = _extract_markdown_urls(LLMS_TXT)

    # Monkeypatch the llms.txt fetch to use the pasted content and parse URLs exactly as expected
    import prin.adapters.website as website

    monkeypatch.setattr(website, "_parse_llms_txt", lambda text: expected_urls)

    def fake_get(self, url, *args, **kwargs):  # type: ignore[override]
        if url.rstrip("/") == (base.rstrip("/") + "/llms.txt"):

            class R:
                status_code = 200
                encoding = "utf-8"

                @property
                def text(self):
                    return LLMS_TXT

                @property
                def content(self):
                    return LLMS_TXT.encode("utf-8")

                def raise_for_status(self):
                    return None

            return R()  # type: ignore[return-value]

        # For any other URL, return a small deterministic body
        class R2:
            status_code = 200
            encoding = "utf-8"

            def __init__(self, u: str) -> None:
                self._u = u

            @property
            def text(self):
                from urllib.parse import urlparse

                name = urlparse(self._u).path.rstrip("/").split("/")[-1]
                return f"CONTENT:{name}"

            @property
            def content(self):
                return self.text.encode("utf-8")

            def raise_for_status(self):
                return None

        return R2(url)  # type: ignore[return-value]

    monkeypatch.setattr(requests.Session, "get", fake_get)

    buf = StringWriter()
    prin_main(argv=[base, "--tag", "md", "--no-exclude"], writer=buf)
    out = buf.text()

    seen: dict[str, int] = defaultdict(int)
    for url in expected_urls:
        basename = url.rstrip("/").split("/")[-1]
        expected_name = _dedup_basename(basename, seen)
        header = f"# FILE: {expected_name}"
        assert header in out, f"Missing header for {url}"
        idx = out.find(header)
        assert idx >= 0
        sep_start = out.find("\n", idx) + 1
        assert sep_start > 0
        sep_end = out.find("\n", sep_start)
        assert sep_end > sep_start
        body_start = sep_end + 1
        sample = out[body_start : body_start + 200]
        assert f"CONTENT:{basename}" in sample
