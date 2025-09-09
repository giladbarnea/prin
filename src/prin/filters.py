from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from .path_classifier import classify_pattern, is_extension, is_glob
from .types import TExclusion


def read_gitignore_file(gitignore_path: Path) -> list[TExclusion]:
    """Read a gitignore-like file and return list of exclusion patterns."""
    exclusions = []
    try:
        with gitignore_path.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    exclusions.append(stripped)
    except (FileNotFoundError, UnicodeDecodeError, PermissionError):
        pass
    return exclusions


def get_gitignore_exclusions(paths: list[str]) -> list[TExclusion]:
    """Get exclusions from gitignore files for given paths."""

    # Note: .gitignore is parked for now until we figure out how to exclude in development time.
    return []
    exclusions = []

    # Read global git ignore file
    home_config_ignore = Path.home() / ".config" / "git" / "ignore"
    exclusions.extend(read_gitignore_file(home_config_ignore))

    # Read gitignore files for each directory path
    for path_str in paths:
        p = Path(path_str)
        if p.is_dir():
            gitignore_path = p / ".gitignore"
            exclusions.extend(read_gitignore_file(gitignore_path))

            git_exclude_path = p / ".git" / "info" / "exclude"
            exclusions.extend(read_gitignore_file(git_exclude_path))

    return exclusions


def is_excluded(entry: Any, *, exclude: list[TExclusion]) -> bool:
    path = Path(getattr(entry, "path", entry))
    name = path.name
    stem = path.stem
    for _exclude in exclude:
        if callable(_exclude):
            if _exclude(name) or _exclude(stem) or _exclude(str(path)):
                return True
            continue
        # Handle extension excludes like ".py" (treated as text by classifier)
        if is_extension(_exclude) and name.endswith(_exclude):
            return True

        if not isinstance(_exclude, str):
            continue

        classification = classify_pattern(_exclude)

        # Globs and regex are handled via fnmatch (regex support is out of scope)
        if classification in ("glob", "regex"):
            p = path.as_posix()
            if fnmatch(name, _exclude) or fnmatch(stem, _exclude) or fnmatch(p, _exclude):
                return True
            continue

        # Text patterns: match by exact segment sequence, not substrings
        # Support multi-part tokens containing path separators (either '/' or '\\')
        token = _exclude.strip()
        if not token:
            continue
        # Normalize separators in the token to POSIX-style for comparison
        import re

        token_parts = [seg for seg in re.split(r"[\\/]+", token) if seg]
        path_parts = list(path.as_posix().split("/"))
        needed = len(token_parts)
        if needed == 0:
            continue
        # Slide a window over path_parts and compare joined POSIX strings
        for i in range(0, len(path_parts) - needed + 1):
            if path_parts[i : i + needed] == token_parts:
                return True
    return False
