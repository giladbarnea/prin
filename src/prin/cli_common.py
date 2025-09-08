from __future__ import annotations

import argparse
import sys
import textwrap
from dataclasses import dataclass, field, replace
from typing import Literal

from prin.defaults import (
    DEFAULT_BINARY_EXCLUSIONS,
    DEFAULT_DOC_EXTENSIONS,
    DEFAULT_EXCLUDE_FILTER,
    DEFAULT_EXCLUSIONS,
    DEFAULT_EXTENSIONS_FILTER,
    DEFAULT_INCLUDE_BINARY,
    DEFAULT_INCLUDE_EMPTY,
    DEFAULT_INCLUDE_HIDDEN,
    DEFAULT_INCLUDE_LOCK,
    DEFAULT_INCLUDE_TESTS,
    DEFAULT_LOCK_EXCLUSIONS,
    DEFAULT_NO_DOCS,
    DEFAULT_NO_EXCLUDE,
    DEFAULT_NO_IGNORE,
    DEFAULT_ONLY_HEADERS,
    DEFAULT_RUN_PATH,
    DEFAULT_TAG,
    DEFAULT_TAG_CHOICES,
    DEFAULT_TEST_EXCLUSIONS,
    Hidden,
)
from prin.filters import get_gitignore_exclusions
from prin.types import _describe_predicate

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
    paths: list[str] = field(default_factory=lambda: [DEFAULT_RUN_PATH])
    include_tests: bool = DEFAULT_INCLUDE_TESTS
    include_lock: bool = DEFAULT_INCLUDE_LOCK
    include_binary: bool = DEFAULT_INCLUDE_BINARY
    no_docs: bool = DEFAULT_NO_DOCS
    include_empty: bool = DEFAULT_INCLUDE_EMPTY
    include_hidden: bool = DEFAULT_INCLUDE_HIDDEN
    extensions: list[str] = field(default_factory=lambda: list(DEFAULT_EXTENSIONS_FILTER))
    exclusions: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE_FILTER))
    no_exclude: bool = DEFAULT_NO_EXCLUDE
    no_ignore: bool = DEFAULT_NO_IGNORE

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

        if not self.include_binary:
            exclusions.extend(DEFAULT_BINARY_EXCLUSIONS)

        if not self.no_ignore:
            exclusions.extend(get_gitignore_exclusions(self.paths))

        if self.no_docs:
            exclusions.extend(DEFAULT_DOC_EXTENSIONS)

        self.exclusions = exclusions

    def replace(self, **kwargs) -> Context:
        """Creates a new copy of the context with the given kwargs updated."""
        return replace(self, **kwargs)


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

    parser.add_argument(
        "paths",
        type=str,
        nargs="*",
        help="Path(s) or roots. Defaults to current directory if none specified.",
        default=[DEFAULT_RUN_PATH],
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
        "-a",
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
        "-M",
        "--include-empty",
        action="store_true",
        help="Include empty files and Python files that only contain imports, comments, and __all__=... expressions.",
        default=DEFAULT_INCLUDE_EMPTY,
    )
    parser.add_argument(
        "-l",
        "--only-headers",
        action="store_true",
        help="Print only the file paths.",
        default=DEFAULT_ONLY_HEADERS,
    )
    parser.add_argument(
        "-e",
        "--extension",
        type=str,
        default=DEFAULT_EXTENSIONS_FILTER,
        action="append",
        help="Only include files with the given extension (repeatable). Overrides exclusions (untested).",
    )

    parser.add_argument(
        "-E",
        "--exclude",
        "--ignore",
        type=str,
        help="Exclude files or directories by glob or regex (repeatable). By default, excludes "
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
        action="store_true",
        help="Disable gitignore file processing.",
        default=DEFAULT_NO_IGNORE,
    )
    parser.add_argument(
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

    # Expand known alias flags before parsing. If argv is None, use sys.argv[1:].
    effective_argv = _expand_cli_aliases(argv if argv is not None else sys.argv[1:])
    args = parser.parse_args(effective_argv)
    return Context(
        paths=list(args.paths),
        include_tests=bool(args.include_tests),
        include_lock=bool(args.include_lock),
        include_binary=bool(args.include_binary),
        no_docs=bool(args.no_docs),
        include_empty=bool(args.include_empty),
        only_headers=bool(args.only_headers),
        extensions=list(args.extension or []),
        exclusions=list(args.exclude or []),
        no_exclude=bool(args.no_exclude),
        no_ignore=bool(args.no_ignore),
        include_hidden=bool(args.include_hidden),
        tag=args.tag,
        max_files=args.max_files,
    )
