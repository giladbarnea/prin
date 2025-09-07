from __future__ import annotations

import argparse
import textwrap
from dataclasses import dataclass, field
from typing import Literal

from prin.defaults import (
    DEFAULT_EXCLUDE_FILTER,
    DEFAULT_EXCLUSIONS,
    DEFAULT_EXTENSIONS_FILTER,
    DEFAULT_INCLUDE_BINARY,
    DEFAULT_INCLUDE_EMPTY,
    DEFAULT_INCLUDE_LOCK,
    DEFAULT_INCLUDE_TESTS,
    DEFAULT_NO_DOCS,
    DEFAULT_NO_EXCLUDE,
    DEFAULT_NO_IGNORE,
    DEFAULT_ONLY_HEADERS,
    DEFAULT_RUN_PATH,
    DEFAULT_TAG,
    DEFAULT_TAG_CHOICES,
)
from prin.types import _describe_predicate


@dataclass(slots=True)
class Context:
    paths: list[str] = field(default_factory=lambda: [DEFAULT_RUN_PATH])
    include_tests: bool = DEFAULT_INCLUDE_TESTS
    include_lock: bool = DEFAULT_INCLUDE_LOCK
    include_binary: bool = DEFAULT_INCLUDE_BINARY
    no_docs: bool = DEFAULT_NO_DOCS
    include_empty: bool = DEFAULT_INCLUDE_EMPTY
    only_headers: bool = DEFAULT_ONLY_HEADERS
    extension: list[str] = field(default_factory=lambda: list(DEFAULT_EXTENSIONS_FILTER))
    exclude: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE_FILTER))
    no_exclude: bool = DEFAULT_NO_EXCLUDE
    no_ignore: bool = DEFAULT_NO_IGNORE
    tag: Literal["xml", "md"] = DEFAULT_TAG
    max_files: int | None = None


def parse_common_args(argv: list[str] | None = None) -> Context:
    from prin.filters import resolve_extensions

    epilog = textwrap.dedent(
        f"""
        DEFAULT MATCH CRITERIA
        When -e,--extension is unspecified, the following file extensions are matched: {", ".join(resolve_extensions(custom_extensions=[], no_docs=False))}.

        NOTE ABOUT EXCLUSIONS
        Exclusions match rather eagerly, because each specified exclusion is handled like a substring match. For example, 'o/b' matches 'foo/bar/baz'.
        Extension exclusions are stricter, so '.py' matches 'foo.py' but not 'foo.pyc'.
        For more control, use glob patterns; specifying '*o/b' will match 'foo/b' but not 'foo/bar/baz'.
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
        help="Exclude `.md`, `.mdx` and `.rst` files. Has no effect if -e,--extension is specified.",
        default=DEFAULT_NO_DOCS,
    )
    parser.add_argument(
        "-M",
        "--include-empty",
        action="store_true",
        help="Include empty files and files that only contain imports and __all__=... expressions.",
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
        help="Only include files with the given extension (repeatable).",
    )

    parser.add_argument(
        "-E",
        "--exclude",
        "--ignore",
        type=str,
        help="Exclude files or directories by shell-style glob or regex (repeatable). By default, excludes "
        + ", ".join(map(_describe_predicate, DEFAULT_EXCLUSIONS))
        + ", and any files in .gitignore, .git/info/exclude, and ~/.config/git/ignore.",
        default=DEFAULT_EXCLUDE_FILTER,
        action="append",
    )
    parser.add_argument(
        "--no-exclude",
        action="store_true",
        help="Disable all exclusions (overrides --exclude).",
        default=DEFAULT_NO_EXCLUDE,
    )
    parser.add_argument(
        "-I",
        "--no-ignore",
        action="store_true",
        help="Disable gitignore file processing.",
        default=DEFAULT_NO_IGNORE,
    )
    parser.add_argument(
        "--tag",
        type=str,
        choices=DEFAULT_TAG_CHOICES,
        default=DEFAULT_TAG,
        help="Output format tag: 'xml' or 'md'.",
    )

    parser.add_argument(
        "--max-files",
        type=int,
        dest="max_files",
        default=None,
        help="Maximum number of files to print across all inputs.",
    )

    args = parser.parse_args(argv)
    return Context(
        paths=list(args.paths),
        include_tests=bool(args.include_tests),
        include_lock=bool(args.include_lock),
        include_binary=bool(args.include_binary),
        no_docs=bool(args.no_docs),
        include_empty=bool(args.include_empty),
        only_headers=bool(args.only_headers),
        extension=list(args.extension or []),
        exclude=list(args.exclude or []),
        no_exclude=bool(args.no_exclude),
        no_ignore=bool(args.no_ignore),
        tag=args.tag,
        max_files=args.max_files,
    )


def derive_filters_and_print_flags(ctx: Context) -> tuple[list[str], list, bool, bool]:
    from .filters import resolve_exclusions, resolve_extensions  # shared helpers

    extensions = resolve_extensions(custom_extensions=ctx.extension, no_docs=ctx.no_docs)
    exclusions = resolve_exclusions(
        no_exclude=ctx.no_exclude,
        custom_excludes=ctx.exclude,
        include_tests=ctx.include_tests,
        include_lock=ctx.include_lock,
        include_binary=ctx.include_binary,
        no_docs=ctx.no_docs,
        no_ignore=ctx.no_ignore,
        paths=ctx.paths,
    )
    return extensions, exclusions, bool(ctx.include_empty), bool(ctx.only_headers)
