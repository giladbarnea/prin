from __future__ import annotations

import sys

from . import filters
from .adapters.filesystem import FileSystemSource
from .adapters.github import GitHubRepoSource
from .adapters.website import WebsiteSource
from .cli_common import Context, derive_filters_and_print_flags, parse_common_args
from .core import DepthFirstPrinter, FileBudget, StdoutWriter, Writer
from .formatters import MarkdownFormatter, XmlFormatter
from .util import extract_in_repo_subpath, is_github_url


def main(*, argv: list[str] | None = None, writer: Writer | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    ctx: Context = parse_common_args(argv)
    extensions, exclusions = derive_filters_and_print_flags(ctx)

    formatter = {"xml": XmlFormatter, "md": MarkdownFormatter}[ctx.tag]()
    out_writer = writer or StdoutWriter()

    # Split positional inputs into local paths and GitHub URLs
    # Treat empty-string tokens as no-ops for local paths to avoid unintended CWD traversal
    local_paths: list[str] = []
    repo_urls: list[str] = []
    for tok in ctx.paths:
        if is_github_url(tok):
            repo_urls.append(tok)
        else:
            if tok != "":
                local_paths.append(tok)

    # Global print budget shared across sources
    budget = FileBudget(ctx.max_files)

    # Filesystem chunk (if any)
    if local_paths:
        fs_printer = DepthFirstPrinter(
            FileSystemSource(),
            formatter,
            include_empty=ctx.include_empty,
            only_headers=ctx.only_headers,
            extensions=extensions,
            exclude=exclusions,
        )
        fs_printer.run(local_paths, out_writer, budget=budget)

    # GitHub repos (each rendered independently to the same writer)
    if repo_urls and not (budget and budget.spent()):
        # For remote repos, do not honor local gitignore by design
        repo_exclusions = filters.resolve_exclusions(
            no_exclude=ctx.no_exclude,
            custom_excludes=ctx.exclude,
            include_tests=ctx.include_tests,
            include_lock=ctx.include_lock,
            include_binary=ctx.include_binary,
            no_docs=ctx.no_docs,
            no_ignore=True,
            include_hidden=ctx.include_hidden,
            paths=[""],
        )
        for url in repo_urls:
            if budget and budget.spent():
                break
            roots: list[str] = []
            derived = extract_in_repo_subpath(url).strip("/")
            if derived:
                roots.append(derived)
            if not roots:
                roots = [""]
            gh_printer = DepthFirstPrinter(
                GitHubRepoSource(url),
                formatter,
                include_empty=ctx.include_empty,
                only_headers=ctx.only_headers,
                extensions=extensions,
                exclude=repo_exclusions,
            )
            gh_printer.run(roots, out_writer, budget=budget)

    # Website URLs (each rendered independently) - non-GitHub HTTP(S) inputs
    if not (budget and budget.spent()):
        from .util import is_http_url

        website_urls = [tok for tok in ctx.paths if is_http_url(tok) and not is_github_url(tok)]
        for base in website_urls:
            if budget and budget.spent():
                break
            ws_printer = DepthFirstPrinter(
                WebsiteSource(base),
                formatter,
                include_empty=ctx.include_empty,
                only_headers=ctx.only_headers,
                extensions=extensions,
                exclude=exclusions,
            )
            # Single virtual root
            ws_printer.run([""], out_writer, budget=budget)


if __name__ == "__main__":
    main()
