from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from .path_classifier import is_extension, is_glob
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
        if (
            name == _exclude
            or str(path) == _exclude
            or stem == _exclude
            or (is_extension(_exclude) and name.endswith(_exclude))
        ):
            return True

        if is_glob(_exclude):
            if fnmatch(name, _exclude) or fnmatch(str(path), _exclude) or fnmatch(stem, _exclude):
                return True
            continue
        # Tighten plain-text matching: match exact path segments only
        # Avoid substring-based exclusions like excluding 'outside_source' because of 'out'.
        # If the exclusion is a simple token (no glob, no path separator), exclude when any path part equals it.
        try:
            if _exclude and not any(ch in _exclude for ch in "*?[]") and ("/" not in _exclude and "\\" not in _exclude):
                if _exclude in path.parts:
                    return True
        except TypeError:
            # Non-string tokens are ignored here
            pass
    return False
