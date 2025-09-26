from __future__ import annotations

import re
import typing as t
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Sequence

from .path_classifier import classify_pattern, is_glob
from .types import Pattern

if TYPE_CHECKING:
    from prin.core import Entry


def read_gitignore_file(gitignore_path: Path) -> list[Pattern]:
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


def get_gitignore_exclusions(paths: list[str]) -> list[Pattern]:
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


def is_excluded(entry: "Entry", *, exclude: Sequence[Pattern]) -> bool:
    path = entry.path
    # Match against full POSIX path only (relative to traversal base)
    target = path.as_posix()
    for _exclude in exclude:
        kind: Literal["regex", "glob"] = classify_pattern(_exclude)
        if kind == "glob":
            if fnmatch(target, t.cast(str, _exclude).strip()):
                return True
            continue

        # Handle extension excludes like ".py" (treated as text by classifier)
        # if is_extension(_exclude) and extension_match(entry, extensions=[_exclude]):
        #     return True

        # regex by default
        try:
            if re.search(_exclude, target):
                return True
        except re.error as e:
            # Invalid regex: treat as no match (alternatively, raise a CLI error upstream)
            import logging

            logging.getLogger(__name__).warning(
                f"[WARNING] [filters.is_excluded] Invalid regex: {_exclude!r}: {e}"
            )

    return False


def extension_match(entry: "Entry", *, extensions: Sequence[Pattern]) -> bool:
    if not extensions:
        return True
    filename = entry.name
    for pattern in extensions:
        if is_glob(pattern):
            if fnmatch(filename, pattern):
                return True
        else:
            # Guaranteed no glob in 'pattern', so check exact extension match.
            import logging

            logging.getLogger(__name__).warning(
                "[WARNING][filters.extension_match] 'pattern' is not a glob: {pattern!r}.This shouldn't happen. 'extensions' should only contain globs by now. CLI normalizes user values and defaults.py also has no bare string extensions."
            )
            if filename.endswith("." + t.cast(str, pattern).removeprefix(".")):
                return True
    return False
