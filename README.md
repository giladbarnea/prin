# `prin`

Prints LLM-friendly content from directories and remote repositories in XML or Markdown.

## Design

Inspired by the excellent `fd` and `rg` tools—and their superb CLI usability—`prin` is flexible, has sane defaults, and is highly configurable.

`prin` aims to be compatible with the CLI options of both `fd` and Simon Willison's `files-to-prompt`.

## Installation

Run `uv tool install git+https://github.com/giladbarnea/prin.git` to install the latest version of `prin` as a tool on your local machine.

Alternatively, clone this repository and run `uv tool install .`.

In both cases, the `prin` executable should be available in your shell.

## Basic Usage

`prin` accepts one or more paths to directories, files, or remote repositories and prints their contents.

```sh
# Print the entire contents of the codebase
prin path/to/codebase

# Print the contents of the `docs` directory alongside the contents of the `rust-lang/book` remote repository
prin path/to/codebase/docs github.com/rust-lang/book

# Print the contents of specific files
prin path/to/codebase/AGENTS.md path/to/codebase/src/**/*.py
```

This can easily be used together with other tools, such as terminal code agents, for a powerful combination:

```sh
prin ./agents/graph/ github.com/pydantic/pydantic-ai/{docs,examples} | claude -p "The graphs are not wired right. Fix them."
```

See `prin --help` for the full list of options.


### Development
- Setup and test: `uv sync` (install uv if needed); `./test.sh`
- Lint and format: `./lint.sh` and `./format.sh`

## Options Roadmap (most of these are not implemented yet)

- `-H`, `--hidden` (alias: --include-hidden) — planned ⏳
Include hidden files and directories in the search (dotfiles and dot-directories).

- `-I`, `--no-ignore` (re-enable with `--ignore`) — implemented ✅
Disable all ignore rules (e.g., from .gitignore, .ignore, .fdignore, and global ignore files).

- `--no-ignore-vcs` (alias: `--ignore-gitignore`; re-enable with `--ignore-vcs`) — implemented ✅
Do not respect Version Control System (VCS) ignore rules (such as .gitignore, .git/info/exclude, and global gitignore).

- `--ignore-file <path>` — planned ⏳
Add an additional ignore-file in .gitignore format (lower precedence than command-line excludes).

- `-E`, `--exclude <glob or regex>` (repeatable; alias: `--ignore <glob>`) — implemented ✅
Exclude files or directories by shell-style glob or regex (identified automatically). Repeat to add multiple patterns (e.g., --exclude '*.log').

- `-g`, `--glob`, `--force-glob` — planned ⏳
Force the interpretation of the search pattern as a glob (instead of a regular expression).
Examples: prin -g '*.py', prin -g 'src/**/test_*.rs'.

- `-e`, `--extension <ext>` (repeatable) — implemented ✅
Only include files with the given extension (e.g., -e rs -e toml).

- `-S`, `--size <constraint>` — planned ⏳
Filter by file size. Format: <+|-><NUM><UNIT> (e.g., +10k, -2M, 500b). Units: b, k, m, g, t, ki, mi, gi, ti.

- `-s`, `--case-sensitive` — planned ⏳
Force case-sensitive matching of the search pattern. By default, case sensitivity is "smart".

- `-i`, `--ignore-case` — planned ⏳
Force case-insensitive matching of the search pattern. By default, case sensitivity is "smart".

- `-H`, `--hidden` (listed above for clarity) — planned ⏳

- `-u`, `--unrestricted` — planned ⏳
Unrestricted search: include hidden files and disable ignore rules (equivalent to --hidden --no-ignore).

- `-uu` — planned ⏳
Equivalent to --no-ignore --hidden.

- `-uuu` — planned ⏳
Equivalent to --no-ignore --hidden --binary.

- `-L`, `--follow` — planned ⏳
Follow symbolic links.

- `-d`, `--max-depth <n>` — planned ⏳
Limit directory traversal to at most <n> levels.

- `-A`, `--absolute-paths` — planned ⏳
Print absolute paths (instead of paths relative to the current working directory).

- `-a`, `--text` — planned ⏳
Treat binary files as text (search and print them as-is).

- `--binary`, `--include-binary` — implemented ✅
Include binary files in the output (e.g., *.pyc, images, archives). Binary files are emitted as headers only in some formats.

- `-n`, `--line-number` (alias: `--line-numbers`) — planned ⏳
Show line numbers in printed file contents.