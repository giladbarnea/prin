# `prin`

[![build](https://github.com/giladbarnea/prin/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/giladbarnea/prin/actions/workflows/build.yml)
[![tests](https://github.com/giladbarnea/prin/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/giladbarnea/prin/actions/workflows/tests.yml)
[![coverage](https://github.com/giladbarnea/prin/actions/workflows/coverage.yml/badge.svg?branch=master)](https://github.com/giladbarnea/prin/actions/workflows/coverage.yml)
[![codecov](https://codecov.io/gh/giladbarnea/prin/branch/master/graph/badge.svg)](https://codecov.io/gh/giladbarnea/prin)

Print the contents of full directories, remote GitHub repositories and websites in an LLM-friendly format.

## Basic Usage

`prin` accepts one or more paths to directories, files, remote repositories or websites exposing llms.txt, and prints their contents.

```sh
# Print the contents of the codebase you're in
prin .

# Print the contents of the `docs` directory alongside the contents of the `rust-lang/book` remote repository
prin docs github.com/rust-lang/book

# Print specific files
prin AGENTS.md src/**/*.py
```

## Recommended Usage

`prin` can easily be used together with other tools, such as terminal code agents and the clipboard for a powerful combination.

#### Piping a local module and code examples from a remote repository to `claude`
```sh
prin agents/graph github.com/pydantic/pydantic-ai/{docs,examples} | claude -p "The graphs are not connected properly. Fix them."
```

#### Attaching a library's documentation to your prompt
```sh
prin . https://docs.framework.io | codex "Leverage framework's API better and minimize reinventing the wheel"
```

See `prin --help` for the full list of options.

## Sane Defaults for LLM Input
`prin` omits files and dirs that you probably don't want in the context window. These are:
1. Build artifacts (dist/, out/, minified files, etc.)
2. Lock files
3. Binary files
4. Dot-files and dot-dirs (.env, .git, .cache, .vscode, etc.)
5. Tests
6. Git-ignored paths

Each can be included in the output by specifying its corresponding `--include-...` CLI flag.

## Output Control

#### `-l`, `--only-headers`
Prints the matched paths in a plaintext list, without their contents.

Essentially outputs the project's structure.

#### `-t`, `--tag` `{xml,md}` (default: `xml`)
Sets how the files are separated in the output. 
- `xml` (the default) wraps each file in xml-like tags:
```xml
<LICENSE>
MIT-whatever
</LICENSE>

<src/main.py>
def main(): ...
</src/main.py>
```

- `md` preceds the file contents with a H2 heading:

```md
## LICENSE
MIT-whatever

---

## src/main.py
def main(): ...
```

## Matching

`prin` treats given arguments as glob:
```sh
# Print all markdown files in the current dir
prin '*.md'
```

You can specify file extensions:
```sh
# Print all markdown and rst files in the project: .md, .mdx, .mdc, .rst
prin -e md -e rst -e 'md*'
```

## Including paths that are excluded by default
// todo specify include flags

## Design

Inspired by the excellent `fd` and `rg` tools—and their superb CLI usability—`prin` is flexible, has powerful sane defaults, and is highly configurable.

`prin` aims to be compatible with the CLI options of both `fd` and Simon Willison's `files-to-prompt`.

## Installation

Run `uv tool install git+https://github.com/giladbarnea/prin.git` to install the latest version of `prin` as a tool on your local machine.

Alternatively, clone this repository and run `./install.sh` (Wraps `uv tool install`).

In both cases, the `prin` executable should be available in your shell.


### Development
- Install `uv` if needed: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Setup and test: `uv sync`; `./test.sh`. Network tests can be skipped with `./test.sh --no-network`.
- Lint and format: `./lint.sh` and `./format.sh`

## Options Roadmap

- `-H`, `--hidden` — implemented ✅
Include hidden files and directories in the search (dotfiles and dot-directories).

- `-I`, `--no-ignore` (aliases: `--no-gitignore`, `-u`, `--unrestricted`) — implemented ✅
Disable gitignore/VCS ignore processing.

- `--ignore-file <path>` — planned ⏳
Add an additional ignore-file in .gitignore format (lower precedence than command-line excludes).

- `-E`, `--exclude <glob or regex>` (repeatable; alias: `--ignore <glob>`) — implemented ✅
Exclude files or directories by shell-style glob or regex (identified automatically). Repeat to add multiple patterns (e.g., --exclude '*.log').

- `-g`, `--glob`, `--force-glob` — planned ⏳
Force the interpretation of the search pattern as a glob (instead of a regular expression).
Examples: prin -g '*.py', prin -g 'src/**/test_*.rs'.

- `-e`, `--extension <ext>` (repeatable) — implemented ✅
Only include files with the given extension (e.g., -e rs -e toml).

- `-T`, `--include-tests` — implemented ✅
Include `test`/`tests` directories and spec.ts files.

- `-K`, `--include-lock` — implemented ✅
Include lock files (e.g., package-lock.json, poetry.lock, Cargo.lock).

- `-M`, `--include-empty` — implemented ✅
Include empty files and semantically-empty Python files.

- `-l`, `--only-headers` — implemented ✅
Print only file paths (no bodies).

- `--tag {xml|md}` — implemented ✅
Choose output format.

- `--max-files <n>` — implemented ✅
Maximum number of files to print across all inputs.

- `-S`, `--size <constraint>` — planned ⏳
Filter by file size. Format: <+|-><NUM><UNIT> (e.g., +10k, -2M, 500b). Units: b, k, m, g, t, ki, mi, gi, ti.

- `-s`, `--case-sensitive` — planned ⏳
Force case-sensitive matching of the search pattern. By default, case sensitivity is "smart".

- `-i`, `--ignore-case` — planned ⏳
Force case-insensitive matching of the search pattern. By default, case sensitivity is "smart".

- `-u`, `--unrestricted` — implemented ✅
Equivalent to --no-ignore.

- `-uu` — implemented ✅
Unrestricted search: include hidden files and disable ignore rules (equivalent to --hidden --no-ignore).

- `-uuu` — implemented ✅
Include everything.
Equivalent to --no-ignore --hidden --binary, or `--no-exclude`.

- `-L`, `--follow` — planned ⏳
Follow symbolic links.

- `-d`, `--max-depth <n>` — planned ⏳
Limit directory traversal to at most <n> levels.

- `-A`, `--absolute-paths` — planned ⏳
Print absolute paths (instead of paths relative to the current working directory).

- `-a`, `--text` — implemented ✅
Alias of --include-binary. Include binary files in output.

- `--binary`, `--include-binary` — implemented ✅
Include binary files in the output (e.g., *.pyc, images, archives). Binary files are emitted as headers only in some formats.

- `-n`, `--line-number` (alias: `--line-numbers`) — planned ⏳
Show line numbers in printed file contents.