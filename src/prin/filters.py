from __future__ import annotations

import re
import typing as t
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Sequence

from pathspec.gitignore import GitIgnoreSpec

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
    """
    Backward-compat shim for callers that expect a list of exclusions from VCS ignore files.

    Now returns an empty list and VCS ignore handling is performed by a dedicated engine
    integrated at the adapter layer. Kept to preserve the call site in Context.__post_init__.
    """
    return []


class GitIgnoreEngine:
    """
    Git-ignore style matcher that aggregates patterns from:
    - ~/.config/git/ignore (global)
    - Per-directory: .fdignore, .ignore, .gitignore
    - Repo-specific: .git/info/exclude (if present under the root)

    Semantics:
    - Patterns are interpreted using Git's wildmatch rules (via pathspec)
    - Deeper directories override ancestor patterns (last match wins)
    - Negations ("!") are honored
    - Matching is done against paths relative to the configured root
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self._dir_spec_cache: dict[Path, GitIgnoreSpec] = {}
        self._global_spec: GitIgnoreSpec | None = self._load_global_spec()

    def _load_global_spec(self) -> GitIgnoreSpec | None:
        global_path = Path.home() / ".config" / "git" / "ignore"
        if not global_path.exists():
            return None
        try:
            lines = global_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            return None
        return GitIgnoreSpec.from_lines(lines)

    @staticmethod
    def _prefixed_lines(lines: list[str], prefix: str) -> list[str]:
        """
        Prefix every non-comment, non-empty pattern line with the directory prefix so
        that patterns are evaluated relative to the engine root while keeping the
        per-file scoping semantics.
        """
        if prefix and not prefix.endswith("/"):
            prefix = prefix + "/"
        out: list[str] = []
        for raw in lines:
            line = raw.rstrip("\n")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            negate = stripped.startswith("!")
            body = stripped[1:] if negate else stripped
            if body.startswith("/"):
                body = body[1:]
            # Scope to directory
            scoped = f"{prefix}{body}" if prefix else body
            out.append(("!" + scoped) if negate else scoped)
        return out

    def _load_dir_spec(self, directory: Path) -> GitIgnoreSpec:
        # Compose spec from ancestor directory specs + current directory ignores
        if directory in self._dir_spec_cache:
            return self._dir_spec_cache[directory]

        parent = directory.parent
        spec_lines: list[str] = []
        if directory != self.root:
            parent_spec = self._load_dir_spec(parent)
            # Start from parent's compiled patterns
            base_patterns = list(parent_spec.patterns)  # type: ignore[attr-defined]
            spec = GitIgnoreSpec(base_patterns)
        else:
            # Root starts from global spec if any
            spec = self._global_spec or GitIgnoreSpec.from_lines([])

        # Aggregate current directory ignore files
        try:
            rel_dir = directory.relative_to(self.root).as_posix()
        except Exception:
            rel_dir = ""

        def read_lines(p: Path) -> list[str]:
            try:
                return p.read_text(encoding="utf-8").splitlines()
            except Exception:
                return []

        lines_here: list[str] = []
        lines_here += self._prefixed_lines(read_lines(directory / ".fdignore"), rel_dir)
        lines_here += self._prefixed_lines(read_lines(directory / ".ignore"), rel_dir)
        lines_here += self._prefixed_lines(read_lines(directory / ".gitignore"), rel_dir)
        # Repo-specific excludes (usually only under repo root)
        lines_here += self._prefixed_lines(read_lines(directory / ".git" / "info" / "exclude"), rel_dir)

        if lines_here:
            spec += GitIgnoreSpec.from_lines(lines_here)

        self._dir_spec_cache[directory] = spec
        return spec

    def is_ignored(self, abs_path: Path) -> bool:
        """Return True if abs_path should be ignored according to aggregated patterns."""
        file_path = Path(abs_path)
        try:
            rel = file_path.relative_to(self.root).as_posix()
        except ValueError:
            # Outside root: treat as not ignored by this engine
            return False
        dir_path = file_path.parent if file_path.is_absolute() else (self.root / file_path).parent
        # If not under root, use root for directory-scoped rules
        try:
            dir_path.relative_to(self.root)
        except ValueError:
            dir_path = self.root

        spec = self._load_dir_spec(dir_path)
        res = spec.check_file(rel)
        # res.include is True → include, False → exclude, None → no match
        return bool(res.include is False)


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
