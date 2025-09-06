### Test coverage conclusion

- Filesystem options now have dedicated CLI-level tests in `tests/test_options_fs.py`.
- Remaining gaps are repo-path scenarios and any repo-specific formatting/flags.

# CLI coverage: features and tests

Note: A feature counts as covered only when it is explicitly specified in the test (not just exercised via defaults), in a dedicated test.
Only `prin.main`-level tests are acceptable (Engine-level don't count).

- include-tests (`-T/--include-tests`):
  - [x] FS
  - [] Repo
- include-lock (`-K/--include-lock`):
  - [x] FS
  - [] Repo
- include-binary (`-a/--text/--include-binary/--binary`):
  - [x] FS
  - [] Repo
- no-docs (`-d/--no-docs`):
  - [x] FS
  - [] Repo
- include-empty (`-M/--include-empty`):
  - [x] FS
  - [] Repo
- only-headers (`-l/--only-headers`):
  - [x] FS
  - [] Repo
- extension (`-e/--extension`, repeatable):
  - [x] FS
  - [] Repo
- exclude (`-E/--exclude/--ignore`, repeatable):
  - [x] FS
  - [] Repo
- no-exclude (`--no-exclude`):
  - [x] FS
  - [] Repo
- no-ignore (`-I/--no-ignore`):
  - [x] FS
  - [] Repo
- tag (`--tag xml|md`):
  - [x] FS
  - [] Repo
- max-files (`--max-files`):
  - [x] FS
  - [x] Repo
- positional roots (multiple inputs):
  - [x] FS
  - [x] Repo
  - many planned options remain unimplemented; by definition they’re untested: hidden, no-ignore-vcs toggle, ignore-file, glob/force-glob, size, case-sensitive/ignore-case, unrestricted combos (`-u`/`-uu`/`-uuu`), follow symlinks, max-depth, absolute-paths, line-number.

