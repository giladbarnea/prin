from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import Any, TypeIs

from typeguard import typechecked

from .defaults import (
    DEFAULT_BINARY_EXCLUSIONS,
    DEFAULT_EXCLUSIONS,
    DEFAULT_DOC_EXTENSIONS,
    DEFAULT_LOCK_EXCLUSIONS,
    DEFAULT_TEST_EXCLUSIONS,
    HiddenFiles,
)
from .types import TExclusion, TExtension, TGlob, _is_extension
from .path_classifier import _is_glob


@typechecked
def is_glob(path) -> TypeIs[TGlob]:
    return _is_glob(path)


@typechecked
def is_extension(name: str) -> TypeIs[TExtension]:
    return _is_extension(name)


@typechecked
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


@typechecked
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


@typechecked
def resolve_exclusions( 
    *,
    no_exclude: bool,
    custom_excludes: list[TExclusion],
    include_tests: bool,
    include_lock: bool,
    include_binary: bool,
    no_docs: bool,
    no_ignore: bool,
    include_hidden: bool | None = None,
    paths: list[str],
) -> list[TExclusion]:
    """Resolve final exclusion list based on command line arguments."""
    if no_exclude:
        return []

    exclusions = DEFAULT_EXCLUSIONS.copy()
    # If hidden files should be included, drop the hidden predicate from defaults
    if include_hidden:
        try:
            exclusions.remove(HiddenFiles)
        except ValueError:
            # HiddenFiles predicate not present; nothing to remove
            pass
    exclusions.extend(custom_excludes)

    if not include_tests:
        exclusions.extend(DEFAULT_TEST_EXCLUSIONS)

    if not include_lock:
        exclusions.extend(DEFAULT_LOCK_EXCLUSIONS)

    if not include_binary:
        exclusions.extend(DEFAULT_BINARY_EXCLUSIONS)

    # Exclude documentation files when requested
    if no_docs:
        exclusions.extend(DEFAULT_DOC_EXTENSIONS)

    if not no_ignore:
        exclusions.extend(get_gitignore_exclusions(paths))
    return exclusions


@typechecked
def resolve_extensions(
    *,
    custom_extensions: list[str],
    no_docs: bool,  # no_docs is unused. Can be a subtle bug.
) -> list[str]:
    """Resolve final extension list based on command line arguments."""
    # New default behavior: no default inclusions. When no custom extensions
    # are provided, include all files by leaving the extensions list empty.
    if custom_extensions:
        return custom_extensions
    return []


@typechecked
def is_excluded(entry: Any, *, exclude: list[TExclusion]) -> bool:
    """Shared predicate implementing the legacy matching semantics."""

    path = Path(getattr(entry, "path", entry))
    name = path.name
    stem = path.stem
    entry_is_glob = is_glob(entry)
    for _exclude in exclude:
        excluded_is_glob = entry_is_glob or is_glob(_exclude)
        if callable(_exclude):
            if _exclude(name) or _exclude(stem) or _exclude(str(path)):
                return True
        elif excluded_is_glob:
            if fnmatch(name, _exclude) or fnmatch(str(path), _exclude) or fnmatch(stem, _exclude):
                return True
        elif (
            name == _exclude
            or str(path) == _exclude
            or stem == _exclude
            or (is_extension(_exclude) and name.endswith(_exclude))
        ):
            return True
        else:
            _exclude_glob = f"*{_exclude}" if is_extension(_exclude) else f"*{_exclude}*"
            if (
                fnmatch(name, _exclude_glob)
                or fnmatch(str(path), _exclude_glob)
                or fnmatch(stem, _exclude_glob)
            ):
                return True
    return False
