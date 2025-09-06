### Test coverage conclusion

- Untested features (from tests/ scan):
  - include/exclude tests flags: `-T/--include-tests`, `-K/--include-lock`, `-a/--text --include-binary --binary`, `-M/--include-empty`, `-l/--only-headers`, `--tag md|xml` (XML is covered indirectly; MD not explicitly).
  - parser wiring for `--exclude/--ignore` and `-e/--extension` is indirectly covered via helpers, but no end-to-end CLI invocation tests for `prin` script; coverage is via engine and helpers.
  - repo path extraction and traversal are covered; however, formatting options and include-empty/only-headers on repo path are not covered.

# CLI coverage: features and tests

Note: A feature counts as covered only when it is explicitly specified in the test (not just exercised via defaults), in a dedicated test.
Only `prin.main`-level tests are acceptable (Engine-level don't count).

- include-tests (`-T/--include-tests`):
  - [] FS
  - [] Repo
- include-lock (`-K/--include-lock`):
  - [] FS
  - [] Repo
- include-binary (`-a/--text/--include-binary/--binary`):
  - [] FS
  - [] Repo
- no-docs (`-d/--no-docs`):
  - [] FS
  - [] Repo
- include-empty (`-M/--include-empty`):
  - [] FS
  - [] Repo
- only-headers (`-l/--only-headers`):
  - [] FS
  - [] Repo
- extension (`-e/--extension`, repeatable):
  - [? maybe, needs verification] FS
  - [] Repo
- exclude (`-E/--exclude/--ignore`, repeatable):
  - [] FS
  - [] Repo
- no-exclude (`--no-exclude`):
  - [] FS
  - [] Repo
- no-ignore (`-I/--no-ignore`):
  - [] FS
  - [] Repo
- tag (`--tag xml|md`):
  - [] FS
  - [] Repo
- max-files (`--max-files`):
  - [x] FS
  - [x] Repo
- positional roots (multiple inputs):
  - [x] FS
  - [x] Repo
  - many planned options remain unimplemented; by definition they’re untested: hidden, no-ignore-vcs toggle, ignore-file, glob/force-glob, size, case-sensitive/ignore-case, unrestricted combos (`-u`/`-uu`/`-uuu`), follow symlinks, max-depth, absolute-paths, line-number.

