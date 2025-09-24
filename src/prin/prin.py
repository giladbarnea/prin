from __future__ import annotations

import sys
from pathlib import Path

from . import cli_common, util
from .adapters import github
from .adapters.filesystem import FileSystemSource
from .adapters.github import GitHubRepoSource
from .adapters.website import WebsiteSource
from .cli_common import Context
from .core import DepthFirstPrinter, FileBudget, StdoutWriter, Writer
from .formatters import MarkdownFormatter, XmlFormatter


def main(*, argv: list[str] | None = None, writer: Writer | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    ctx: Context = cli_common.parse_common_args(argv)

    formatter = {"xml": XmlFormatter, "md": MarkdownFormatter}[ctx.tag]()
    out_writer = writer or StdoutWriter()

    # Global print budget shared across sources
    budget = FileBudget(ctx.max_files)

    # Check if we're in old style (multiple paths) or new style (pattern + search_path)
    if ctx.paths:
        # Old style: handle multiple paths
        # To separate given cwd subdirs from external paths
        cwd_filesystem_source = FileSystemSource(Path.cwd())

        # Split positional inputs into local paths and GitHub URLs
        # Treat empty-string tokens as no-ops for local paths to avoid unintended CWD traversal
        local_paths: list[str] = []
        repo_urls: list[str] = []
        for path in filter(bool, ctx.paths):
            if util.is_github_url(path):
                repo_urls.append(path)
            else:
                cwd_filesystem_source.resolve(path)
                local_paths.append(path)

        # Filesystem chunk (if any)
        if local_paths:
            filesystem_ctx = ctx.replace(paths=local_paths)
            fs_printer = DepthFirstPrinter(
                FileSystemSource(),
                formatter,
                ctx=filesystem_ctx,
            )
            fs_printer.run(local_paths, out_writer, budget=budget)

        # GitHub repos (each rendered independently to the same writer)
        if repo_urls and not (budget and budget.spent()):
            # For remote repos, do not honor local gitignore by design
            repo_ctx = ctx.replace(no_ignore=True, paths=[""])
            for url in repo_urls:
                if budget and budget.spent():
                    break
                roots: list[str] = []
                derived = github.parse_github_url(url)["subpath"].strip("/")
                if derived:
                    roots.append(derived)
                if not roots:
                    roots = [""]
                gh_printer = DepthFirstPrinter(
                    GitHubRepoSource(url),
                    formatter,
                    ctx=repo_ctx,
                )
                gh_printer.run(roots, out_writer, budget=budget)

        # Website URLs (each rendered independently) - non-GitHub HTTP(S) inputs
        if not (budget and budget.spent()):
            website_urls = [
                tok for tok in ctx.paths if util.is_http_url(tok) and not util.is_github_url(tok)
            ]
            for base in website_urls:
                if budget and budget.spent():
                    break
                ws_printer = DepthFirstPrinter(
                    WebsiteSource(base),
                    formatter,
                    ctx=ctx,
                )
                # Single virtual root
                ws_printer.run([""], out_writer, budget=budget)
    else:
        # New style: pattern + search_path
        search_path = ctx.search_path
        pattern = ctx.pattern
        
        # Determine source type based on search_path
        if search_path and util.is_github_url(search_path):
            # GitHub repository
            gh_source = GitHubRepoSource(search_path)
            gh_source.configure(ctx.replace(no_ignore=True))
            printer = DepthFirstPrinter(gh_source, formatter, ctx=ctx)
            printer.run_pattern(pattern, search_path, out_writer, budget=budget)
        elif search_path and util.is_http_url(search_path):
            # Website
            ws_source = WebsiteSource(search_path)
            ws_source.configure(ctx)
            printer = DepthFirstPrinter(ws_source, formatter, ctx=ctx)
            printer.run_pattern(pattern, search_path, out_writer, budget=budget)
        else:
            # Filesystem (default)
            fs_source = FileSystemSource()
            fs_source.configure(ctx)
            printer = DepthFirstPrinter(fs_source, formatter, ctx=ctx)
            printer.run_pattern(pattern, search_path, out_writer, budget=budget)


if __name__ == "__main__":
    main()
