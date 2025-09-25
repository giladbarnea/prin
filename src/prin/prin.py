from __future__ import annotations

import sys

from . import cli_common, util
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

    search_path = ctx.search_path
    pattern = ctx.pattern

    # Determine source type based on search_path
    if search_path and util.is_github_url(search_path):
        # GitHub repository
        gh_source = GitHubRepoSource(search_path)
        gh_source.configure(ctx.replace(no_ignore=True))
        printer = DepthFirstPrinter(gh_source, formatter=formatter, ctx=ctx)
        printer.run_pattern(pattern, search_path, out_writer, budget=budget)
    elif search_path and util.is_http_url(search_path):
        # Website
        ws_source = WebsiteSource(search_path)
        ws_source.configure(ctx)
        printer = DepthFirstPrinter(ws_source, formatter=formatter, ctx=ctx)
        printer.run_pattern(pattern, search_path, out_writer, budget=budget)
    else:
        # Filesystem (default)
        fs_source = FileSystemSource()
        fs_source.configure(ctx)
        printer = DepthFirstPrinter(fs_source, formatter=formatter, ctx=ctx)
        printer.run_pattern(pattern, search_path, out_writer, budget=budget)


if __name__ == "__main__":
    main()
