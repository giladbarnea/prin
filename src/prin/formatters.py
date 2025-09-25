from __future__ import annotations

from typing import Protocol


class Formatter(Protocol):
    def format(self, path: str, text: str) -> str: ...
    def binary(self, path: str) -> str: ...


class XmlFormatter(Formatter):
    def format(self, path: str, text: str) -> str:
        if not text.endswith("\n"):
            text = text + "\n"
        # Avoid duplicate closing tags when path already includes a leading '<' from previous formatting
        return f"<{path}>\n{text}</{path}>\n"

    def binary(self, path: str) -> str:
        return f"<{path}/>\n"


class MarkdownFormatter(Formatter):
    def _sep(self, path: str) -> str:
        return "=" * max(len(path) + 8, 20)

    def format(self, path: str, text: str) -> str:
        sep = self._sep(path)
        return f"## FILE: {path}\n{sep}\n{text}\n\n---\n"

    def binary(self, path: str) -> str:
        sep = self._sep(path)
        return f"## FILE: {path}\n{sep}\n\n---\n"


class HeaderFormatter(Formatter):
    """Used by the CLI when the -l,--only-headers flag is passed. Doesn't print the file contents."""

    def format(self, path: str, _: str) -> str:
        return path.removesuffix("\n") + "\n"

    def binary(self, path: str) -> str:
        return path.removesuffix("\n") + "\n"
