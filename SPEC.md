---
audience: AI agents and humans
description: a precise and complete source of truth for how 'prin' behaves. Code deviating from the spec is considered a bug.
updated: before making changes in the code — like in TDD (think Spec Driven Development)
authority rank: absolute source of truth. implementation and other docs derive from this file.
---

## What–Then–Where: Filesystem Path Display Spec

### Scope
- Defines how printed file paths are displayed for the local filesystem adapter, based on the provided “where” token.
- Assumes anchor = current working directory (cwd). In examples, cwd = `/home` and the project layout is:

```bash
./
./foo/main.py
./bar/main.py
```

### Core Rules (Display Base and Prefix)
- The first positional argument is the pattern (what). The second is the search location (where).
- The “where” token determines two things:
  - the traversal base (what subtree to search in)
  - the display form of matched paths (absolute vs relative and any required prefix)

#### Relative vs Absolute “where”
- If “where” is omitted (None):
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
- The display form (absolute vs relative; presence of `./` or `../`) is driven solely by the “where” token’s shape, not by where it resolves to.
- Pattern matching is performed against the full path relative to the traversal base; specifying a pattern does not override default exclusions.
