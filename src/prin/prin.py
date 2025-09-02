from __future__ import annotations

import sys

from .adapters.filesystem import FileSystemSource
from .adapters.github import GitHubRepoSource
from .cli_common import Context, derive_filters_and_print_flags, parse_common_args
from .core import DepthFirstPrinter, StdoutWriter, Writer
from .formatters import MarkdownFormatter, XmlFormatter
from .util import extract_in_repo_subpath, is_github_url


def main(*, argv: list[str] | None = None, writer: Writer | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    ctx: Context = parse_common_args(argv)
    extensions, exclusions, include_empty, only_headers = derive_filters_and_print_flags(ctx)

    formatter = XmlFormatter() if ctx.tag == "xml" else MarkdownFormatter()
    out_writer = writer or StdoutWriter()

    # Split positional inputs into local paths and GitHub URLs
    local_paths: list[str] = []
    repo_urls: list[str] = []
    for tok in ctx.paths:
        if is_github_url(tok):
            repo_urls.append(tok)
        else:
            local_paths.append(tok)

    # Filesystem chunk (if any)
    if local_paths:
        fs_printer = DepthFirstPrinter(
            FileSystemSource(),
            formatter,
            include_empty=include_empty,
            only_headers=only_headers,
            extensions=extensions,
            exclude=exclusions,
        )
        fs_printer.run(local_paths, out_writer)

    # GitHub repos (each rendered independently to the same writer)
    if repo_urls:
        from .filters import resolve_exclusions as _resolve_exclusions

        # For remote repos, do not honor local gitignore by design
        repo_exclusions = _resolve_exclusions(
            no_exclude=ctx.no_exclude,
            custom_excludes=ctx.exclude,
            include_tests=ctx.include_tests,
            include_lock=ctx.include_lock,
            include_binary=ctx.include_binary,
            no_ignore=True,
            paths=[""],
        )
        for url in repo_urls:
            roots: list[str] = []
            derived = extract_in_repo_subpath(url).strip("/")
            if derived:
                roots.append(derived)
            if not roots:
                roots = [""]
            gh_printer = DepthFirstPrinter(
                GitHubRepoSource(url),
                formatter,
                include_empty=include_empty,
                only_headers=only_headers,
                extensions=extensions,
                exclude=repo_exclusions,
            )
            gh_printer.run(roots, out_writer)


if __name__ == "__main__":
    main()
