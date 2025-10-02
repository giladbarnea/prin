---
audience: Humans
description: Introduces 'prin' to newcomers in a clear and simple manner, with approachable examples. Presents what IS (current implementation) to attract users rather than overwhelm with future plans.
updated: After feature changes, additions, or removals.
authority rank: Not a source of truth. Should be derived from SPEC.md and AGENTS.md.
---

# `prin`

[![build](https://github.com/giladbarnea/prin/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/giladbarnea/prin/actions/workflows/build.yml)
[![tests](https://github.com/giladbarnea/prin/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/giladbarnea/prin/actions/workflows/tests.yml)
[![coverage](https://github.com/giladbarnea/prin/actions/workflows/coverage.yml/badge.svg?branch=master)](https://github.com/giladbarnea/prin/actions/workflows/coverage.yml)
[![coverage](https://img.shields.io/badge/coverage-56%25-red)](#)

Print the contents of full directories, remote GitHub repositories and websites in an LLM-friendly format for increased prompt performance.

## Basic Usage

`prin` accepts an optional pattern followed by zero or more paths (files or directories).
If no paths are provided, it defaults to the current directory.

```sh
# Search for Python files in the src directory
prin "*.py" src/

# Find all markdown files in the current directory
prin "*.md"

# Use regex to find test files
prin "test_.*\.py$" .

# Print all files in the docs directory
prin "" docs/

# Search in GitHub repositories
prin "*.rs" github.com/rust-lang/book
```

**Pattern-as-file behavior:** If the pattern itself is an existing file, it will be printed explicitly AND used as a search pattern. For example, `prin README.md src/` prints README.md plus any files matching "README.md" in src/.

## Sane Defaults with LLM performance in mind

`prin` omits files and dirs that you probably don't want in the context window. These are:
1. Build artifacts (dist/, out/, minified files, etc.)
2. Lock files
3. Binary files
4. Dot-files and dot-dirs (.env, .git, .cache, .vscode, etc.)
5. Tests
6. Git-ignored paths (.gitignore, .git/info/exclude, ~/.config/git/ignore, plus .ignore and .fdignore)  // noqa: parities

Each can be included in the output by specifying its corresponding `--include-...` CLI flag.

## Recommended Usage

`prin` can easily be used together with other tools, such as terminal code agents and the clipboard for a powerful combination.

#### Finding specific patterns and piping to `claude`
```sh
prin "*.py" agents/graph | claude -p "ConversationManager errors when invoking CoderAgent. Fix it."
```

#### Attaching a library's documentation to your prompt
```sh
prin . https://docs.framework.io | codex "Leverage framework's API to remove custom implementations."
```

See `prin --help` for the full list of options.

### Smoke test

Run the end-to-end smoke test script, which prints category-based expectations before each run:

```sh
./smoke-test.sh
```

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

- `md` precedes each file with a heading, separator, content, and divider:

```md
## FILE: LICENSE
================
MIT-whatever

---

## FILE: src/main.py
====================
def main(): ...

---
```

## Matching

The first positional argument may be a pattern (glob or regex). Any subsequent
positional arguments are paths (files or directories). If no paths are given,
the current directory is used.

```sh
# Glob pattern - matches all markdown files
prin '*.md' .

# Regex pattern - matches files starting with "test_"
prin '^test_.*\.py$' src/

# Empty pattern - lists all files
prin '' docs/
```

Patterns are matched against the full relative path from each provided path root.

You can also filter by file extensions using the `-e` flag:
```sh
# Print all markdown and rst files in the project: .md, .mdx, .mdc, .rst
prin '' . -e md -e rst -e 'md*'
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

##### Testing adapter-specific suites

You can focus or skip tests for specific adapters via pytest flags:

```sh
# Run only website adapter tests
./test.sh --website

# Run only GitHub repo adapter tests
./test.sh --repo

# Skip website adapter tests
./test.sh --no-website

# Skip GitHub repo adapter tests
./test.sh --no-repo

# Combine with network control
./test.sh --website --no-network
```

#### Task Completion Checklist (create internal todo list)

1. **Prep** (before any code)
- [ ] Read AGENTS.md, PARITIES.md, and SPEC.md.
- [ ] Recognize sets in PARITIES.md relevant to your plan.
- [ ] Run ./test.sh.
- [ ] Write TDD tests.

2. **The loop**
- [ ] Iterate until tests pass

3. **After the loop**
- [ ] Run ./test.sh.
- [ ] Update PARITIES.md as instructed in [Important: Working Against and Updating PARITIES.md](AGENTS.md) and in [Maintaining PARITIES.md](PARITIES.md).
- [ ] Review root-level `*.md` files for discrepancies across README.md, SPEC.md, AGENTS.md, PARITIES.md, and ROADMAP.md.
- [ ] Run `uv run src/internal/parities_check.py`.
- [ ] Run ./format.sh
- [ ] Status update user.

See [Development Cycle (Tight TDD Loop)](AGENTS.md) for more details.

## CLI Options

- [x] `-H`, `--hidden`: Include hidden files and directories in the search (dotfiles and dot-directories).

- [x] `-I`, `--no-ignore` (aliases: `--no-gitignore`, `--no-ignore-dot`, `-u`, `--unrestricted`): Disable gitignore/VCS ignore processing.

- [x] `-E`, `--exclude <glob or regex>` (repeatable; alias: `--ignore <glob>`): Exclude files or directories by shell-style glob or regex (identified automatically). Repeat to add multiple patterns (e.g., --exclude '*.log').

- [x] `-e`, `--extension <ext>` (repeatable): Only include files with the given extension (e.g., -e rs -e toml).

- [x] `-T`, `--include-tests`: Include `test`/`tests` directories and spec.ts files.

- [x] `-K`, `--include-lock`: Include lock files (e.g., package-lock.json, poetry.lock, Cargo.lock).

- [x] `--no-dependencies`: Exclude dependency specification files (e.g., package.json, pyproject.toml, requirements.txt, pom.xml, Cargo.toml).

- [x] `-d`, `--no-docs`: Exclude documentation files (e.g., *.md, *.rst, *.txt).

- [x] `-M`, `--include-empty`: Include empty files and semantically-empty Python files.

- [x] `-l`, `--only-headers`, `--list-details`: Print only file paths (no bodies).

- [x] `-t`, `--tag {xml|md}`: Choose output format.

- [x] `--max-files <n>`: Global maximum number of files to print across all inputs.

- [x] `--max-depth <n>`: Maximum depth to traverse. Depth 1 means only direct children of the root.

- [x] `--min-depth <n>`: Minimum depth to start printing files. Depth 1 means only direct children of the root.

- [x] `--exact-depth <n>`: Print files only at this exact depth. Overrides `--max-depth` and `--min-depth`.

- [x] `-uu`: Unrestricted search: include hidden files and disable ignore rules (equivalent to `--hidden --no-ignore`).

- [x] `-uuu`, `--no-exclude`, `--include-all`: Include everything. Equivalent to `--no-ignore --hidden --binary`.

- [x] `-a`, `--text`, `--include-binary`, `--binary`: Include binary files in the output (e.g., *.pyc, images, archives). Binary files are emitted as headers only in some formats.

## Roadmap

See `ROADMAP.md` for planned features and priorities.