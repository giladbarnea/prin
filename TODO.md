### Test coverage conclusion

- Untested features (from tests/ scan):
  - include/exclude tests flags: `-T/--include-tests`, `-K/--include-lock`, `-a/--text --include-binary --binary`, `-M/--include-empty`, `-l/--only-headers`, `--tag md|xml` (XML is covered indirectly; MD not explicitly).
  - parser wiring for `--exclude/--ignore` and `-e/--extension` is indirectly covered via helpers, but no end-to-end CLI invocation tests for `prin` script; coverage is via engine and helpers.
  - repo path extraction and traversal are covered; however, formatting options and include-empty/only-headers on repo path are not covered.

# CLI coverage: features and tests

Note: A feature counts as covered only when it is explicitly specified in the test (not just exercised via defaults). Either engine-level or `prin.main`-level tests are acceptable.

- include-tests (`-T/--include-tests`): FS covered; Repo missing
- include-lock (`-K/--include-lock`): FS missing; Repo missing
- include-binary (`-a/--text/--include-binary/--binary`): FS missing; Repo missing
- no-docs (`-d/--no-docs`): FS missing; Repo missing
- include-empty (`-M/--include-empty`): FS missing; Repo missing
- only-headers (`-l/--only-headers`): FS missing; Repo missing
- extension (`-e/--extension`, repeatable): FS covered (engine sets explicitly); Repo missing
- exclude (`-E/--exclude/--ignore`, repeatable): FS missing; Repo missing
- no-exclude (`--no-exclude`): FS missing; Repo missing
- no-ignore (`-I/--no-ignore`): FS missing; Repo missing
- tag (`--tag xml|md`): FS missing; Repo covered (md)
- max-files (`--max-files`): FS covered; Repo covered
- positional roots (multiple inputs): FS covered; Repo covered
  - many planned options remain unimplemented; by definition they’re untested: hidden, no-ignore-vcs toggle, ignore-file, glob/force-glob, size, case-sensitive/ignore-case, unrestricted combos (`-u`/`-uu`/`-uuu`), follow symlinks, max-depth, absolute-paths, line-number.

