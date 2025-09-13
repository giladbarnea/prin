from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

from .path_classifier import classify_pattern, is_extension, is_glob
from .types import TExclusion, TGlob

if TYPE_CHECKING:
    from prin.core import Entry


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


def is_excluded(entry: "Entry", *, exclude: list[TExclusion]) -> bool:
    path = entry.path
    name = path.name
    stem = path.stem
    for _exclude in exclude:
        if callable(_exclude):
            if _exclude(name) or _exclude(stem) or _exclude(str(path)):
                return True
            continue
        token = _exclude.strip()
        # Handle extension excludes like ".py" (treated as text by classifier)
        if is_extension(token) and extension_match(entry, extensions=[token]):
            return True

        classification = classify_pattern(token)

        # Globs and regex are handled via fnmatch (regex support is out of scope)
        if classification in ("glob", "regex"):
            p = path.as_posix()
            if fnmatch(name, token) or fnmatch(stem, token) or fnmatch(p, token):
                return True
            continue

        # Text patterns: match by exact segment sequence, not substrings
        # Support multi-part tokens containing path separators (either '/' or '\\')
        if not token:
            continue
        # Normalize separators in the token to POSIX-style for comparison
        import re

        token_parts = [seg for seg in re.split(r"[\\/]+", token) if seg]
        path_parts = list(path.as_posix().split("/"))
        needed = len(token_parts)
        if needed == 0:
            continue
        # Special-case simple tokens with no separators: also match file/directory name or stem equal to token
        if needed == 1 and (name == token or stem == token):
            return True
        # Slide a window over path_parts and compare joined POSIX strings
        for i in range(0, len(path_parts) - needed + 1):
            if path_parts[i : i + needed] == token_parts:
                return True
    return False


def extension_match(entry: "Entry", *, extensions: list[TGlob]) -> bool:
    if not extensions:
        return True
    filename = entry.name
    for pattern in extensions:
        if is_glob(pattern):
            if fnmatch(filename, pattern):
                return True
        else:
            # Guaranteed no glob in 'pattern', so check exact extension match.
            if filename.endswith("." + pattern.removeprefix(".")):
                return True
    return False
