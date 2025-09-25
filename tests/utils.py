import os
from pathlib import Path


def write_file(path: Path, content: str | None) -> None:
    path = Path(path)
    if content is None:
        path.mkdir(parents=True, exist_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def touch_file(path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def resolve_without_symlinks(path: Path) -> Path:
    return Path(os.path.normpath((Path(path)).absolute()))


def count_opening_xml_tags(text: str) -> int:
    return sum(
        1
        for line in text.splitlines()
        if line.startswith("<") and not line.startswith("</") and not line.endswith("/>")
    )


def count_md_headers(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("## FILE: "))
