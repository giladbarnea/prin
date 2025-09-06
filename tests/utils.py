from pathlib import Path


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def touch_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def count_opening_xml_tags(text: str) -> int:
    return sum(
        1
        for line in text.splitlines()
        if line.startswith("<") and not line.startswith("</") and not line.endswith("/>")
    )


def count_md_headers(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("# FILE: "))

