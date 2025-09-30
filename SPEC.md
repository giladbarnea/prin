---
audience: AI agents and humans
description: A precise and complete source of truth for how 'prin' behaves. Code deviating from the spec is considered a bug.
updated: Before making changes in the code — like in TDD (think Spec Driven Development)
authority rank: Absolute source of truth. Implementation and other docs derive from this file.
---

## What–Then–Where (per-root): Filesystem Path Display Spec

### Scope
- Defines how printed file paths are displayed for the local filesystem adapter, based on the provided “where” token.
- Assumes anchor = current working directory (cwd). In examples, cwd = `/home` and the project layout is:

```bash
./
./foo/main.py
./bar/main.py
```

### Core Rules (Display Base and Prefix)
- The first positional argument may be a pattern (what). It is followed by zero or more search roots (where).
- Each “where” token determines two things for its own subtree:
  - the traversal base (what subtree to search in)
  - the display form of matched paths (absolute vs relative and any required prefix)

#### Relative vs Absolute “where”
- If no “where” is provided: 
  - Traverse: cwd
  - Display: bare paths, relative to cwd (no leading `./`).
- If “where” is a relative child of cwd (e.g., `foo`):
  - Traverse: cwd/child
  - Display: bare paths, relative to cwd (no leading `./`).
- If “where” is `.` or begins with `./` (e.g., `.` or `./foo`):
  - Traverse: cwd (or the given child under cwd)
  - Display: paths relative to current dir, prefixed exactly as written (`./…`).
- If “where” begins with `../` (one-level walk-up):
  - Traverse: the resolved parent path (e.g., `/` when cwd is `/home`)
  - Display: paths relative to that base, preserving the leading `../…` prefix.
- If “where” is absolute (e.g., `/`, `/home`, `/home/foo`):
  - Traverse: the absolute path
  - Display: absolute paths (the fact it may equal cwd or be a child of it is irrelevant).

### Canonical Examples (cwd = `/home`)

```bash
# No ‘where’ arg → bare paths relative to cwd
$ prin main
foo/main.py
bar/main.py

# ‘where’ = current dir dot → relative to current dir (with leading ./)
$ prin main .
./foo/main.py
./bar/main.py

# ‘where’ = foo (relative child) → traverse /home/foo; display bare relative to cwd
$ prin main foo
foo/main.py

# ‘where’ = ./foo → display relative to current dir (child), preserving ./
$ prin main ./foo
./foo/main.py

# ‘where’ = ../ (one-level up) → display relative to that ../ segment
$ prin main ../
../home/foo/main.py
../home/bar/main.py

# ‘where’ = ../home (walk up then back down) → still relative to ../home
$ prin main ../home
../home/foo/main.py
../home/bar/main.py

# ‘where’ = / (absolute) → display absolute
$ prin main /
/home/foo/main.py
/home/bar/main.py

# ‘where’ = /home (absolute path of cwd) → display absolute
$ prin main /home
/home/foo/main.py
/home/bar/main.py

# ‘where’ = /home/foo (absolute child) → display absolute
$ prin main /home/foo
/home/foo/main.py
```

### Notes
- The display form (absolute vs relative; presence of `./` or `../`) is driven solely by each "where" token's shape, not by where it resolves to.
- Pattern matching is performed against the full path relative to each traversal base; specifying a pattern does not override default exclusions.

## Pattern-as-File Behavior

When the pattern argument resolves to an existing file path, `prin` exhibits dual behavior:

1. The file is force-printed (explicit) regardless of filters
2. The pattern is ALSO applied to traverse each specified path (or current directory if none given)

**Example:**
```bash
# If README.md exists:
$ prin README.md src/
# Output: README.md (force-printed) + any files matching "README.md" pattern in src/
```

This allows combining explicit file output with pattern-based search in a single invocation.

## CLI Options

### Exclusions
- `-E`, `--exclude <glob|regex>` (repeatable): exclude paths matching the pattern; matches full display-relative path.
- `-d`, `--no-docs`: exclude documentation files (e.g., `*.md`, `*.rst`, `*.txt`).

### Inclusions
- `-H`, `--hidden`: include dot-files and dot-directories.
- `-T`, `--include-tests`: include `test`/`tests` directories and related test files (e.g., `*.spec.*`).
- `-K`, `--include-lock`: include lock files.
- `-M`, `--include-empty`: include empty files (and semantically-empty Python files).
- `-a`, `--binary`, `--include-binary` (alias: `--text`): include binary files.
- `-I`, `--no-ignore` (aliases: `--no-gitignore`, `-u`, `--unrestricted`): do not honor VCS ignore files (.gitignore, .git/info/exclude, ~/.config/git/ignore, plus .ignore and .fdignore are ignored by default unless this is set).
- `--no-exclude`, `-uuu`, `--include-all`: include everything (disable all default exclusions).
- `-uu`: shorthand for `--hidden --no-ignore`.
