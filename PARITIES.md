# PARITIES

Purpose: Ensure that when any member of a parity set changes, all other members are reviewed/updated to maintain intentional 1:1 or N:N consistency. These are deliberate couplings, not smells. The threshold for inclusion is high and obvious.

Conventions
- Each set has: ID, Members (with exact locations), Contract (what must stay in lockstep), Triggers (what events require syncing), and How to Update (quick checklist/tests).
- “Members” list exact symbols or files; ranges are avoided. If a member is removed, either remove the set or replace the member accordingly.

---

SET: CLI-CTX-OPTIONS
- Members
  - README.md: Options documented under “Options Roadmap” and behavior narratives
  - src/prin/cli_common.py: `Context` fields and default values; `parse_common_args(...)` arguments and flags; `_expand_cli_aliases` map
  - src/prin/defaults.py: `DEFAULT_*` used by CLI defaults and choices
  - src/prin/core.py: `DepthFirstPrinter._set_from_context` consumed fields and runtime behavior tied to flags
  - tests/test_options_fs.py, tests/test_options_repo.py: end-to-end option coverage
- Contract
  - 1:1 parity between CLI flags, `Context` fields, and defaults in `defaults.py`. Adding/changing a flag requires adding/changing the matching `Context` field and default constant, and adjusting `DepthFirstPrinter` consumption when applicable.
  - CLI alias expansions must reflect the same semantic behavior as the canonical flags.
  - README must describe every implemented flag with correct semantics; planned flags must not be claimed implemented.
- Triggers
  - Adding/removing/renaming a CLI flag; changing a default; changing how a flag affects traversal, filtering, or output.
- How to Update
  1) Update `defaults.py` constants
  2) Update `Context` field list and `parse_common_args`
  3) Update `_expand_cli_aliases` if aliases change
  4) If behavior changes, update `DepthFirstPrinter._set_from_context` and friends
  5) Update README’s option documentation
  6) Extend/adjust tests in `tests/test_options_*.py`

---

SET: FORMATTER-SELECTION
- Members
  - src/prin/prin.py: selection of formatter by `ctx.tag` ("xml" → `XmlFormatter`, "md" → `MarkdownFormatter`)
  - src/prin/formatters.py: `XmlFormatter`, `MarkdownFormatter`, `HeaderFormatter` semantics
  - src/prin/core.py: `DepthFirstPrinter` forcing `HeaderFormatter` when `only_headers` is true
  - tests/test_options_fs.py::test_tag_md_outputs_markdown_format
  - tests/test_options_repo.py::test_repo_tag_md_outputs_markdown_format
- Contract
  - Tag strings available in CLI must have a matching formatter class and identical mapping in `prin.py` and `defaults.DEFAULT_TAG_CHOICES`.
  - `only_headers` forces header-only output regardless of selected formatter.
- Triggers
  - Adding a new tag value; changing behavior/format of a formatter.
- How to Update
  1) Add formatter class
  2) Add tag value to `DEFAULT_TAG_CHOICES` and mapping in `prin.py`
  3) Adjust tests to assert new format, keep header-only override behavior
  4) Update README

---

SET: SOURCE-ADAPTER-INTERFACE
- Members
  - src/prin/core.py: `SourceAdapter` Protocol and `Entry`/`NodeKind`
  - src/prin/adapters/filesystem.py: `FileSystemSource`
  - src/prin/adapters/github.py: `GitHubRepoSource`
  - src/prin/adapters/website.py: `WebsiteSource`
  - tests/test_filesystem_source.py, tests/test_github_adapter.py, tests/test_website_adapter.py, tests/test_website_adapter_all_urls.py
- Contract
  - All adapters implement: `resolve_root`, `list_dir`, `read_file_bytes`, `is_empty` with the semantics expected by `DepthFirstPrinter`:
    - `resolve_root` returns a logical POSIX path used for display anchoring
    - `list_dir` raises `NotADirectoryError` when the input refers to a single file (to force-include explicit paths)
    - `read_file_bytes` returns raw bytes
    - `is_empty` uses shared semantic emptiness for Python where applicable
  - Path display must be interoperable (POSIX-like) to keep formatting consistent across adapters.
- Triggers
  - Adding a new adapter; changing the protocol or `Entry`/`NodeKind` shapes or semantics.
- How to Update
  1) Update `SourceAdapter` Protocol and all adapters to match
  2) Ensure explicit-file behavior via `NotADirectoryError` parity
  3) Keep POSIX-style paths for display
  4) Add/adjust adapter-specific tests; ensure mixed-source tests still pass

---

SET: ENGINE-FILTERS-SEMANTIC-EMPTINESS
- Members
  - src/prin/core.py: filtering hooks (`_excluded`, `_extension_match`, `is_blob_semantically_empty`), budget handling, header-only behavior
  - src/prin/filters.py: `is_excluded`, `get_gitignore_exclusions`, `is_glob`, `is_extension`
  - src/prin/defaults.py: default exclusion sets and categories (tests, lock, binary, docs, hidden)
  - tests/test_cli_engine_*.py, tests/test_options_*.py
- Contract
  - Engine filter behavior must reflect CLI context and defaults consistently; explicit positional paths are force-included regardless of exclusions.
  - Semantic emptiness for Python is shared and adapter-agnostic; toggled by `include_empty`.
  - `--max-files` applies globally across sources via `FileBudget`.
- Triggers
  - Changing filter semantics, default exclusion sets, or emptiness logic.
- How to Update
  1) Adjust `defaults.py` and `filters.py`
  2) Ensure `Context.__post_init__` composes final exclusions correctly
  3) Verify engine respects force-include and budget semantics
  4) Update README behavior narratives and tests

---

SET: CLI-URL-ROUTING
- Members
  - src/prin/prin.py: input token routing between filesystem, GitHub, and website URLs; repo subpath extraction; global `FileBudget`
  - src/prin/util.py: `is_github_url`, `is_http_url`, `extract_in_repo_subpath`
  - tests/test_print_repo_positional.py, tests/test_print_mixed_fs_repo.py, tests/test_max_files_*.
- Contract
  - Routing logic and helpers remain in lockstep: a token classified as GitHub must be handled by GitHub adapter; HTTP non-GitHub goes to Website adapter; everything else local filesystem. Subpath extraction must be reflected in traversal roots.
- Triggers
  - Changing URL detection or subpath rules; adding new source kinds.
- How to Update
  1) Update helpers in `util.py`
  2) Update routing in `prin.py`
  3) Extend tests to cover mixed inputs and edge cases
  4) Update README examples

---

SET: PATTERN-CLASSIFIER
- Members
  - src/prin/path_classifier.py: `classify_pattern` and `_is_glob`
  - src/prin/filters.py: `is_glob` re-export and use
  - tests/test_pattern_classifier.py
  - src/prin/__init__.py: re-export for external tests
- Contract
  - Classifier rules must be consistently used by filters; re-exports must remain aligned with tests’ import paths.
- Triggers
  - Changing classifier heuristics or moving exports.
- How to Update
  1) Update classifier
  2) Keep `filters.is_glob` parity
  3) Adjust tests and any re-exports

---

SET: README-EXAMPLES-REALITY
- Members
  - README.md examples and documented behavior
  - src/prin/prin.py and adapters for actual observed behavior
  - tests that cover the same stories (options tests, mixed-source tests)
- Contract
  - README claims must reflect implemented behavior and flags; examples should run as described.
- Triggers
  - Any behavior or flag change; example updates.
- How to Update
  1) Update README text and examples
  2) Ensure corresponding tests still pass

---

SET: TEST-SUITE-COVERAGE-BY-FEATURE
- Members
  - tests/test_options_fs.py, tests/test_options_repo.py: cover each CLI flag end-to-end per source
  - tests/test_cli_engine_*.py: traversal and path display behavior
  - tests/test_max_files_*.py: `--max-files` budget semantics
  - tests/test_website_adapter_*.py: website parsing and rendering
- Contract
  - For each implemented feature/flag, there is test coverage for both local filesystem and GitHub sources when applicable; website adapter covered for its specific behavior.
- Triggers
  - Adding a new CLI flag or behavior; adding a new adapter.
- How to Update
  1) Add parallel tests for each source where feature applies
  2) Keep assertions aligned (differ only by adapter-specific expectations)

---

SET: EXPLICIT-PATH-FORCE-INCLUDE
- Members
  - src/prin/core.py: DFS handling of `NotADirectoryError` → force include; duplicate suppression
  - src/prin/adapters/github.py: file-path responses raise `NotADirectoryError`
  - src/prin/adapters/filesystem.py: `list_dir` uses scandir semantics; explicit file roots handled by engine
  - tests/test_cli_engine_positional.py::test_directory_and_explicit_ignored_file_inside
  - tests/test_print_repo_positional.py::test_repo_explicit_ignored_file_is_printed
- Contract
  - Passing an explicit path must print it even if default exclusions would skip it; applies uniformly across adapters.
- Triggers
  - Changing how explicit paths are routed or how adapters signal file vs directory.
- How to Update
  1) Ensure adapters raise `NotADirectoryError` for explicit file-path roots
  2) Keep engine’s force-include behavior intact
  3) Verify tests for both FS and GitHub

---

SET: BUDGET-GLOBALITY
- Members
  - src/prin/core.py: `FileBudget`
  - src/prin/prin.py: single shared budget across all sources
  - tests/test_max_files_fs.py, tests/test_max_files_repo.py, tests/test_print_mixed_fs_repo.py
- Contract
  - One global budget is shared across all sources in a single invocation; stopping traversal when spent.
- Triggers
  - Changing how file limits apply or introducing per-source budgets.
- How to Update
  1) Keep `FileBudget` logic and shared usage consistent
  2) Adjust tests to new semantics

---

SET: GITIGNORE-BEHAVIOR
- Members
  - src/prin/filters.py: `get_gitignore_exclusions` (currently returns [])
  - src/prin/cli_common.py: `Context.__post_init__` composition of exclusions with `no_ignore`
  - tests/test_options_fs.py::test_unrestricted_includes_gitignored (and skipped tests around no-ignore)
- Contract
  - Until implemented, `.gitignore` is effectively ignored unless behavior changes; flags (`--no-ignore`, `-u`, `-uu`) must remain consistent with current semantics.
- Triggers
  - Implementing real gitignore parsing.
- How to Update
  1) Implement `get_gitignore_exclusions`
  2) Revisit flag interactions in `Context.__post_init__`
  3) Unskip and/or add tests documenting the new behavior

---

SET: WEBSITE-LLMS-TXT-PARSING
- Members
  - src/prin/adapters/website.py: `_parse_llms_txt`, URL normalization, key deduplication
  - tests/test_website_adapter.py, tests/test_website_adapter_all_urls.py
  - src/prin/prin.py: website routing and `WebsiteSource` usage
- Contract
  - All Markdown links and raw URLs in llms.txt are parsed and fetched; duplicates deduped by key with suffixing; printed with selected formatter.
- Triggers
  - Changing llms.txt parsing or keying rules.
- How to Update
  1) Update parser behavior and key mapping
  2) Adjust tests for expected headers and content

---

Notes on non-parities (intentionally excluded)
- Internal variable names and helper private-method shapes that do not affect the public CLI, adapter protocol, or documented behavior are not parity-bound.
- Performance choices (sorting strategy, traversal order beyond documented behavior) are not parity-bound unless tests assert specifics.
