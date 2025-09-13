# `prin`

[![build](https://github.com/giladbarnea/prin/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/giladbarnea/prin/actions/workflows/build.yml)
[![tests](https://github.com/giladbarnea/prin/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/giladbarnea/prin/actions/workflows/tests.yml)
[![coverage](https://github.com/giladbarnea/prin/actions/workflows/coverage.yml/badge.svg?branch=master)](https://github.com/giladbarnea/prin/actions/workflows/coverage.yml)
[![coverage](https://img.shields.io/badge/coverage-56%25-red)](#)

Print the contents of full directories, remote GitHub repositories and websites in an LLM-friendly format for increased prompt performance.

## Basic Usage

`prin` accepts one or more paths to directories, files, remote repositories or websites, and prints the paths and contents of the files in them, in a way that is easy for LLMs to understand.

```sh
# Print the contents of the codebase you're in
prin .

# Print the contents of the `docs` directory alongside the contents of the `rust-lang/book` remote repository
prin docs github.com/rust-lang/book

# Print specific files
prin AGENTS.md src/**/*.py
```

## Sane Defaults with LLM performance in mind

`prin` omits files and dirs that you probably don't want in the context window. These are:
1. Build artifacts (dist/, out/, minified files, etc.)
2. Lock files
3. Binary files
4. Dot-files and dot-dirs (.env, .git, .cache, .vscode, etc.)
5. Tests
6. Git-ignored paths  // noqa: parities

Each can be included in the output by specifying its corresponding `--include-...` CLI flag.

## Recommended Usage

`prin` can easily be used together with other tools, such as terminal code agents and the clipboard for a powerful combination.

#### Piping a local module and code examples from a remote repository to `claude`
```sh
prin agents/graph github.com/pydantic/pydantic-ai/{docs,examples} | claude -p "ConversationManager errors when invoking CoderAgent. Fix it."
```

#### Attaching a library's documentation to your prompt
```sh
prin . https://docs.framework.io | codex "Leverage framework's API better to remove custom implementations where possible"
```

See `prin --help` for the full list of options.

## Output Control

#### `-l`, `--only-headers`
Prints the matched paths in a plaintext list, without their contents.

Essentially outputs the project's structure.

Aliases: `--list-details`.

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
- Test: `./test.sh` [pytest options...]
- Lint and format: `./lint.sh` and `./format.sh`.
 - To add or remove a dependency, use `uv add` or `uv remove`.

#### Task Completion Checklist (create internal todo list)

1. **Prep** (before any code)
- [ ] Read AGENTS.md and PARITIES.md.
- [ ] Recognize sets in PARITIES.md relevant to your plan.
- [ ] Run ./test.sh.
- [ ] Write TDD tests.

2. **The loop**
- [ ] Iterate until tests pass

3. **After the loop**
- [ ] Run ./test.sh.
- [ ] Update PARITIES.md as instructed in [Important: Working Against and Updating PARITIES.md](AGENTS.md) and in [Maintaining PARITIES.md](PARITIES.md).
- [ ] Run `uv run src/internal/parities_check.py`.
- [ ] Run ./format.sh
- [ ] Status update user.

See [Development Cycle (Tight TDD Loop)](AGENTS.md) for more details.

## Planned (not implemented)

#### CLI Options

- [x] `-H`, `--hidden`: Include hidden files and directories in the search (dotfiles and dot-directories).

- [x] `-I`, `--no-ignore` (aliases: `--no-gitignore`, `--no-ignore-dot`, `-u`, `--unrestricted`): Disable gitignore/VCS ignore processing.

- [ ] `--ignore-file <path>`: Add an additional ignore-file in .gitignore format (lower precedence than command-line excludes).

- [x] `-E`, `--exclude <glob or regex>` (repeatable; alias: `--ignore <glob>`): Exclude files or directories by shell-style glob or regex (identified automatically). Repeat to add multiple patterns (e.g., --exclude '*.log').

- [x] `-e`, `--extension <ext>` (repeatable): Only include files with the given extension (e.g., -e rs -e toml).

- [x] `-T`, `--include-tests`: Include `test`/`tests` directories and spec.ts files.

- [x] `-K`, `--include-lock`: Include lock files (e.g., package-lock.json, poetry.lock, Cargo.lock).

- [x] `-d`, `--no-docs`: Exclude documentation files (e.g., *.md, *.rst, *.txt).

- [x] `-M`, `--include-empty`: Include empty files and semantically-empty Python files.

- [x] `-l`, `--only-headers`, `--list-details`: Print only file paths (no bodies).

- [x] `-t`, `--tag {xml|md}`: Choose output format.

- [x] `--max-files <n>`: Maximum number of files to print across all inputs.

- [x] `-uu`: Unrestricted search: include hidden files and disable ignore rules (equivalent to `--hidden --no-ignore`).

- [x] `-uuu`, `--no-exclude`, `--include-all`: Include everything. Equivalent to `--no-ignore --hidden --binary`.

- [x] `-a`, `--text`, `--include-binary`, `--binary`: Include binary files in the output (e.g., *.pyc, images, archives). Binary files are emitted as headers only in some formats.

- [ ] `-g`, `--glob`, `--force-glob`: Force the interpretation of the search pattern as a glob (instead of a regular expression). Examples: prin -g '*.py', prin -g 'src/**/test_*.rs'.

- [ ] `-S`, `--size <constraint>`: Filter by file size. Format: <+|-><NUM><UNIT> (e.g., +10k, -2M, 500b). Units: b, k, m, g, t, ki, mi, gi, ti.

- [ ] `-s`, `--case-sensitive`: Force case-sensitive matching of the search pattern. By default, case sensitivity is "smart".

- [ ] `-i`, `--ignore-case`: Force case-insensitive matching of the search pattern. By default, case sensitivity is "smart".

- [ ] `-L`, `--follow`: Follow symbolic links.

- [ ] `-d`, `--max-depth <n>`: Limit directory traversal to at most <n> levels.

- [ ] `-D`, `--exact-depth <n>`: Traverse directories exactly <n> levels deep.

- [ ] `-m`, `--min-depth <n>`: Traverse directories at least <n> levels deep.

- [ ] `-A`, `--absolute-paths`: Print absolute paths (instead of paths relative to the specified root).

- [ ] `-n`, `--line-number` (alias: `--line-numbers`): Show line numbers in printed file contents.

- [ ] `-o`, `--output {json,yaml,csv}`: Format the entire output as a JSON, YAML or CSV string.
  - [ ] `--json` alias for `-o json`.
  - [ ] `--yaml` alias for `-o yaml`.
  - [ ] `--csv` alias for `-o csv`.

- [ ] `--no-cache`: Do not cache results of GitHub API calls and HTTP requests.

#### Capabilities

- [ ] Support regex-based matching.
- [ ] Smart-case matching.
- [ ] `prin /tmp/par` matches `/tmp/parts.md` and `/tmp/foo/non-partisan.md` (compat with 'fd')