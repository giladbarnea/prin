from __future__ import annotations

import argparse
import dataclasses
import os
import sys
import textwrap
from dataclasses import dataclass, field
from typing import Literal

from prin.defaults import (
    DEFAULT_BINARY_EXCLUSIONS,
    DEFAULT_CONFIG_EXTENSIONS,
    DEFAULT_DEPENDENCY_EXCLUSIONS,
    DEFAULT_DOC_EXTENSIONS,
    DEFAULT_EXACT_DEPTH,
    DEFAULT_EXCLUDE_FILTER,
    DEFAULT_EXCLUSIONS,
    DEFAULT_EXTENSIONS_FILTER,
    DEFAULT_INCLUDE_BINARY,
    DEFAULT_INCLUDE_DEPENDENCIES,
    DEFAULT_INCLUDE_EMPTY,
    DEFAULT_INCLUDE_HIDDEN,
    DEFAULT_INCLUDE_LOCK,
    DEFAULT_INCLUDE_TESTS,
    DEFAULT_LOCK_EXCLUSIONS,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MIN_DEPTH,
    DEFAULT_NO_CONFIG,
    DEFAULT_NO_DOCS,
    DEFAULT_NO_EXCLUDE,
    DEFAULT_NO_IGNORE,
    DEFAULT_NO_SCRIPTS,
    DEFAULT_NO_STYLESHEETS,
    DEFAULT_ONLY_HEADERS,
    DEFAULT_SCRIPT_EXCLUSIONS,
    DEFAULT_STYLESHEET_EXTENSIONS,
    DEFAULT_TAG,
    DEFAULT_TAG_CHOICES,
    DEFAULT_TEST_EXCLUSIONS,
    Hidden,
)
from prin.types import Glob, Pattern, TPath, _describe_predicate

# Map shorthand/alias flags to their canonical expanded forms.
# The expansion occurs before argparse parsing and preserves argument order.
CLI_OPTIONS_ALIASES: dict[str, tuple[str, ...]] = {
    "-uu": ("--hidden", "--no-ignore"),
}


def _expand_cli_aliases(argv: list[str] | None) -> list[str]:
    """
    Expand alias flags in argv into their canonical forms.

    This function does not mutate the provided argv list. It returns a new list
    where alias tokens are replaced in-place positionally with their mapped
    sequence of tokens.
    """
    if not argv:
        return []
    expanded: list[str] = []
    for token in argv:
        replacement = CLI_OPTIONS_ALIASES.get(token)
        if replacement is not None:
            expanded.extend(replacement)
        else:
            expanded.append(token)
    return expanded


@dataclass(slots=True)
class Context:
    # Field list should match CLI options.
    pattern: str = ""
    paths: list[str] = field(default_factory=list)
    include_tests: bool = DEFAULT_INCLUDE_TESTS
    include_lock: bool = DEFAULT_INCLUDE_LOCK
    include_dependencies: bool = DEFAULT_INCLUDE_DEPENDENCIES
    include_binary: bool = DEFAULT_INCLUDE_BINARY
    no_docs: bool = DEFAULT_NO_DOCS
    no_config: bool = DEFAULT_NO_CONFIG
    no_scripts: bool = DEFAULT_NO_SCRIPTS
    no_stylesheets: bool = DEFAULT_NO_STYLESHEETS
    include_empty: bool = DEFAULT_INCLUDE_EMPTY
    include_hidden: bool = DEFAULT_INCLUDE_HIDDEN
    extensions: list[Pattern] = field(default_factory=lambda: list(DEFAULT_EXTENSIONS_FILTER))
    exclusions: list[Pattern] = field(default_factory=lambda: list(DEFAULT_EXCLUDE_FILTER))
    no_exclude: bool = DEFAULT_NO_EXCLUDE
    no_ignore: bool = DEFAULT_NO_IGNORE

    # Depth controls
    max_depth: int | None = DEFAULT_MAX_DEPTH
    min_depth: int | None = DEFAULT_MIN_DEPTH
    exact_depth: int | None = DEFAULT_EXACT_DEPTH

    # Formatting and output
    only_headers: bool = DEFAULT_ONLY_HEADERS
    tag: Literal["xml", "md"] = DEFAULT_TAG
    max_files: int | None = None

    def __post_init__(self):
        """
        Resolve final exclusion list based on command line arguments.
        Specified exclusions are added on top of the default exclusions.
        Some boolean flags toggle off specific default exclusions (e.g., --include-*, --no-ignore).
        Some boolean flags toggle on an additional exclusion category (e.g., --no-docs and --hidden).
        The --no-exclude flag overrides everything and includes all files and directories.
        """
        if self.no_exclude:
            self.exclusions = []
            return

        exclusions = DEFAULT_EXCLUSIONS.copy()
        exclusions.extend(self.exclusions)

        if not self.include_hidden:
            exclusions.append(Hidden)

        if not self.include_tests:
            exclusions.extend(DEFAULT_TEST_EXCLUSIONS)

        if not self.include_lock:
            exclusions.extend(DEFAULT_LOCK_EXCLUSIONS)

        if not self.include_dependencies:
            exclusions.extend(DEFAULT_DEPENDENCY_EXCLUSIONS)

        if not self.include_binary:
            exclusions.extend(DEFAULT_BINARY_EXCLUSIONS)

        # Note: VCS ignore handling (.gitignore, .ignore, .fdignore, etc.) is performed
        # by GitIgnoreEngine at the adapter layer, not via exclusions list.

        if self.no_docs:
            exclusions.extend(DEFAULT_DOC_EXTENSIONS)

        if self.no_config:
            exclusions.extend(DEFAULT_CONFIG_EXTENSIONS)

        if self.no_scripts:
            exclusions.extend(DEFAULT_SCRIPT_EXCLUSIONS)

        if self.no_stylesheets:
            exclusions.extend(DEFAULT_STYLESHEET_EXTENSIONS)

        self.exclusions = exclusions

    def replace(self, **kwargs) -> Context:
        """Creates a new copy of the context with the given kwargs updated."""
        return dataclasses.replace(self, **kwargs)


def _normalize_extension_to_glob(val: TPath | Glob) -> Glob:
    """
    Ensures `val` is returned as a `Glob("*.ext")`.
    >>> _normalize_extension_to_glob("ext") == Glob("*.ext")
    True
    >>> _normalize_extension_to_glob(".ext") == Glob("*.ext")
    True
    >>> _normalize_extension_to_glob("*.ext") == Glob("*.ext")
    True
    >>> _normalize_extension_to_glob("like/this.ext")
    ValueError: Extension cannot be empty or contain path separator 'like/this.ext'
    >>> _normalize_extension_to_glob("")
    ValueError: Extension cannot be empty or contain path separator ''
    """
    val = val.strip()
    if not val or os.path.sep in val:
        raise ValueError(f"Extension cannot be empty or contain path separator {val!r}")
    if val.startswith("*."):
        return Glob(val)
    if val.startswith("."):
        return Glob(f"*{val}")
    return Glob(f"*.{val}")


def parse_common_args(argv: list[str] | None = None) -> Context:
    epilog = textwrap.dedent(
        """
        DEFAULT MATCH CRITERIA
        prin matches everything except a set of sane defaults typically excluded when loading a directory into an LLM context:
        - build artifacts and dependency directories
        - package lock files
        - cache
        - binary files
        - logs
        - secrets
        - tests
        - hidden files
        - empty files
        """
    )

    parser = argparse.ArgumentParser(
        description="Prints the contents of files in a directory or specific file paths",
        add_help=True,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )

    # What-then-where positional arguments (pattern + zero or more paths)
    parser.add_argument(
        "pattern",
        type=str,
        nargs="?",
        help="Pattern to search for (glob or regex). If omitted, lists all files.",
        default="",
    )
    parser.add_argument(
        "paths",
        type=str,
        nargs="*",
        help="Zero or more paths (files or directories). If omitted, defaults to current directory.",
        default=[],
    )

    # Uppercase short flags are boolean "include" flags.
    parser.add_argument(
        "-T",
        "--include-tests",
        action="store_true",
        help="Include `test` and `tests` directories and spec.ts files.",
        default=DEFAULT_INCLUDE_TESTS,
    )
    parser.add_argument(
        "-K",
        "--include-lock",
        action="store_true",
        help="Include lock files (e.g. package-lock.json, poetry.lock, Cargo.lock).",
        default=DEFAULT_INCLUDE_LOCK,
    )
    parser.add_argument(
        "--no-dependencies",
        action="store_false",
        dest="include_dependencies",
        help="Exclude dependency specification files (e.g. package.json, pyproject.toml, requirements.txt, pom.xml, Cargo.toml).",
        default=DEFAULT_INCLUDE_DEPENDENCIES,
    )
    parser.add_argument(
        "-a",  # Deviates from 'fd' that has '-a' for '--absolute-path'. Compat with 'rg'.
        "--text",
        "--include-binary",
        "--binary",
        action="store_true",
        dest="include_binary",
        help="Include binary files (e.g. *.pyc, *.jpg, *.zip, *.pdf).",
        default=DEFAULT_INCLUDE_BINARY,
    )
    parser.add_argument(
        "-d",
        "--no-docs",
        action="store_true",
        help=f"Exclude {', '.join(DEFAULT_DOC_EXTENSIONS)} files.",
        default=DEFAULT_NO_DOCS,
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        help=f"Exclude {', '.join(DEFAULT_CONFIG_EXTENSIONS)} files.",
        default=DEFAULT_NO_CONFIG,
    )
    parser.add_argument(
        "--no-scripts",
        action="store_true",
        help="Exclude shell and automation scripts (e.g. *.sh, *.ps1, *.bat) and scripts/ directories.",
        default=DEFAULT_NO_SCRIPTS,
    )
    parser.add_argument(
        "--no-style",
        "--no-css",
        action="store_true",
        dest="no_stylesheets",
        help=f"Exclude {', '.join(DEFAULT_STYLESHEET_EXTENSIONS)} files.",
        default=DEFAULT_NO_STYLESHEETS,
    )
    parser.add_argument(
        "-M",
        "--include-empty",
        action="store_true",
        help="Include empty files and Python files that only contain imports and __all__=... expressions.",
        default=DEFAULT_INCLUDE_EMPTY,
    )
    parser.add_argument(
        "-l",
        "--only-headers",
        "--list-details",  # 'fd' compat
        action="store_true",
        help="Print only the file paths in a plaintext list, without their contents.",
        default=DEFAULT_ONLY_HEADERS,
    )
    parser.add_argument(
        "-e",
        "--extension",
        type=_normalize_extension_to_glob,  # pyright: ignore[reportArgumentType]
        default=DEFAULT_EXTENSIONS_FILTER,
        action="append",
        help="Only include files with the given extension (repeatable). Overrides exclusions.",
    )

    parser.add_argument(
        "-E",
        "--exclude",
        "--ignore",
        type=str,
        help="Exclude files or directories by glob (repeatable). By default, excludes "
        + ", ".join(map(_describe_predicate, DEFAULT_EXCLUSIONS))
        + ", and any files in .gitignore, .git/info/exclude, and ~/.config/git/ignore.",
        default=DEFAULT_EXCLUDE_FILTER,
        action="append",
    )
    parser.add_argument(
        "--no-exclude",
        "--include-all",
        "-uuu",
        action="store_true",
        help="Include all files and directories (overrides --exclude).",
        default=DEFAULT_NO_EXCLUDE,
    )
    parser.add_argument(
        "-H",
        "--hidden",
        action="store_true",
        dest="include_hidden",
        help="Include hidden files and directories (dotfiles and dot-directories).",
        default=DEFAULT_INCLUDE_HIDDEN,
    )

    parser.add_argument(
        "-I",
        "--no-ignore",
        "--no-gitignore",
        "-u",
        "--unrestricted",
        "--no-ignore-dot",  # 'rg' compat
        action="store_true",
        help="Disable gitignore file processing.",
        default=DEFAULT_NO_IGNORE,
    )
    parser.add_argument(
        "-t",
        "--tag",
        type=str,
        choices=DEFAULT_TAG_CHOICES,
        default=DEFAULT_TAG,
        help="Output format tag.",
    )

    parser.add_argument(
        "--max-files",
        type=int,
        dest="max_files",
        default=None,
        help="Maximum number of files to print across all inputs.",
    )

    # Depth control arguments
    parser.add_argument(
        "--max-depth",
        type=int,
        dest="max_depth",
        default=DEFAULT_MAX_DEPTH,
        help="Maximum depth to traverse. Depth 1 means only direct children of the root.",
    )
    parser.add_argument(
        "--min-depth",
        type=int,
        dest="min_depth",
        default=DEFAULT_MIN_DEPTH,
        help="Minimum depth to start printing files. Depth 1 means only direct children of the root.",
    )
    parser.add_argument(
        "--exact-depth",
        type=int,
        dest="exact_depth",
        default=DEFAULT_EXACT_DEPTH,
        help="Print files only at this exact depth. Overrides --max-depth and --min-depth.",
    )

    # Expand known alias flags before parsing. If argv is None, use sys.argv[1:].
    effective_argv = _expand_cli_aliases(argv if argv is not None else sys.argv[1:])
    args = parser.parse_args(effective_argv)

    return Context(
        pattern=args.pattern,
        paths=list(args.paths or []),
        include_tests=bool(args.include_tests),
        include_lock=bool(args.include_lock),
        include_dependencies=bool(args.include_dependencies),
        include_binary=bool(args.include_binary),
        no_docs=bool(args.no_docs),
        no_config=bool(args.no_config),
        no_scripts=bool(args.no_scripts),
        no_stylesheets=bool(args.no_stylesheets),
        include_empty=bool(args.include_empty),
        only_headers=bool(args.only_headers),
        extensions=list(args.extension or []),
        exclusions=list(args.exclude or []),
        no_exclude=bool(args.no_exclude),
        no_ignore=bool(args.no_ignore),
        include_hidden=bool(args.include_hidden),
        tag=args.tag,
        max_files=args.max_files,
        max_depth=args.max_depth,
        min_depth=args.min_depth,
        exact_depth=args.exact_depth,
    )
