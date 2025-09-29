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

    pattern = ctx.pattern

    # If no paths are provided, default to current directory behavior (single run with None)
    if not ctx.paths:
        # Filesystem (default)
        fs_source = FileSystemSource()
        fs_source.configure(ctx)
        fs_printer = DepthFirstPrinter(fs_source, formatter=formatter, ctx=ctx)

        # If the pattern itself is an existing file path, emit it explicitly first
        try:
            p_as_path = fs_source.resolve(pattern)
            if p_as_path.exists() and p_as_path.is_file():
                # Print the exact file regardless of filters, using original token for display
                fs_printer.run_pattern("", pattern, out_writer, budget=budget)
        except Exception:
            pass

        fs_printer.run_pattern(pattern, None, out_writer, budget=budget)
        return

    # There are one or more paths. Share a single filesystem printer for all FS paths
    fs_source = FileSystemSource()
    fs_source.configure(ctx)
    fs_printer = DepthFirstPrinter(fs_source, formatter=formatter, ctx=ctx)

    # If the pattern itself is an existing file path, emit it explicitly once
    try:
        p_as_path = fs_source.resolve(pattern)
        if p_as_path.exists() and p_as_path.is_file():
            # Print the exact file regardless of filters, using original token for display
            fs_printer.run_pattern("", pattern, out_writer, budget=budget)
    except Exception:
        pass

    for token in ctx.paths:
        if budget.spent():
            break
        if util.is_github_url(token):
            gh_source = GitHubRepoSource(token)
            gh_source.configure(ctx.replace(no_ignore=True))
            gh_printer = DepthFirstPrinter(gh_source, formatter=formatter, ctx=ctx)
            gh_printer.run_pattern(pattern, token, out_writer, budget=budget)
            continue
        if util.is_http_url(token):
            ws_source = WebsiteSource(token)
            ws_source.configure(ctx)
            ws_printer = DepthFirstPrinter(ws_source, formatter=formatter, ctx=ctx)
            ws_printer.run_pattern(pattern, token, out_writer, budget=budget)
            continue

        # Filesystem token: detect if file or directory
        try:
            resolved = fs_source.resolve(token)
            if resolved.exists() and resolved.is_file():
                # Force-print this file regardless of filters by using empty pattern
                fs_printer.run_pattern("", token, out_writer, budget=budget)
            else:
                # Directory or non-existent; traverse with pattern (non-existent will yield nothing)
                fs_printer.run_pattern(pattern, token, out_writer, budget=budget)
        except Exception:
            # On any resolution error, fall back to traversal attempt
            fs_printer.run_pattern(pattern, token, out_writer, budget=budget)


if __name__ == "__main__":
    main()
