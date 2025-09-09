## PARITIES

This document enumerates intentional parity sets across the codebase: places that must remain "the same" in meaning and behavior. When any member of a parity set changes, update all other members accordingly.

Purpose: ensure future code AI agents automatically propagate consistent changes across paired components when modifying one of them.

Guidance for agents
- Prefer high-signal, obvious parities. Do not add speculative pairs.
- When adding a new feature/option, update all parity members in the same edit series.
- If you cannot satisfy a parity immediately, add a TODO in your PR description and open a follow-up issue.

### Parity 1 — CLI options ↔ Context fields ↔ Defaults ↔ README
- Elements:
  - `src/prin/cli_common.py`: `parse_common_args(...)` option set and help
  - `src/prin/cli_common.py`: `Context` dataclass fields (comment: "Field list should match CLI options.")
  - `src/prin/defaults.py`: `DEFAULT_*` constants (values and choices, e.g., `DEFAULT_TAG_CHOICES`)
  - `README.md`: options and usage documentation (flags, behavior, examples)
- Invariant:
  - 1:1 mapping between CLI flags and `Context` fields, including default values from `defaults.py` and documented behavior in `README.md`.
  - Renaming/adding/removing a flag requires updating: parser, `Context`, `defaults.py`, and `README.md` in lockstep.
- Tests touching this parity:
  - Filesystem options: `tests/test_options_fs.py`
  - Repository options: `tests/test_options_repo.py`

### Parity 2 — Tag choices ↔ Formatter classes ↔ README examples
- Elements:
  - `src/prin/defaults.py`: `DEFAULT_TAG_CHOICES` (e.g., `["xml", "md"]`)
  - `src/prin/prin.py`: tag→formatter dispatch (`{"xml": XmlFormatter, "md": MarkdownFormatter}`)
  - `src/prin/formatters.py`: `XmlFormatter`, `MarkdownFormatter`, `HeaderFormatter`
  - `README.md`: output examples for XML and Markdown
- Invariant:
  - Tag choices and dispatch table must stay in sync. Adding a tag requires a `Formatter` implementation, dispatch entry, defaults update, doc examples, and tests.
- Tests touching this parity:
  - `tests/test_options_fs.py::test_tag_md_outputs_markdown_format`
  - `tests/test_options_repo.py::test_repo_tag_md_outputs_markdown_format`

### Parity 3 — --only-headers flag ↔ HeaderFormatter enforcement
- Elements:
  - `Context.only_headers` (CLI: `-l/--only-headers`)
  - `DepthFirstPrinter.__init__` forcing `HeaderFormatter` when `only_headers=True`
- Invariant:
  - When `only_headers` is set, bodies must not be printed regardless of the passed formatter.
- Tests touching this parity:
  - FS: `tests/test_options_fs.py::test_only_headers_prints_headers_only`
  - Repo: `tests/test_options_repo.py::test_repo_only_headers_prints_headers_only`

### Parity 4 — Default filter categories ↔ Defaults ↔ README ↔ FS fixture
- Elements:
  - `src/prin/defaults.py`: `DEFAULT_EXCLUSIONS`, `DEFAULT_TEST_EXCLUSIONS`, `DEFAULT_LOCK_EXCLUSIONS`, `DEFAULT_BINARY_EXCLUSIONS`, `DEFAULT_DOC_EXTENSIONS`, `Hidden`
  - `README.md`: "Sane Defaults for LLM Input" section (categories listed)
  - FS test fixture tree: `tests/conftest.py::fs_root` (contains examples for each category)
- Invariant:
  - Categories described in README must be reflected in `defaults.py`, and corresponding sample files must exist in `fs_root` for coverage. If a category is added/removed/changed, update all three.
- Tests touching this parity:
  - FS flags toggling categories: `tests/test_options_fs.py` (e.g., `--hidden`, `--include-tests`, `--include-lock`, `--include-binary`, `--no-docs`, `--include-empty`, `--exclude`, `--no-exclude`, `--extension`)
  - Repo flags for analogous categories: `tests/test_options_repo.py`

### Parity 5 — Exclusion/matching semantics shared across sources
- Elements:
  - `src/prin/core.py`: `DepthFirstPrinter._excluded` and `_extension_match`
  - `src/prin/filters.py`: `is_excluded`, `is_glob`, `get_gitignore_exclusions`
  - All adapters via `DepthFirstPrinter`: FS, GitHub, Website
- Invariant:
  - Inclusion/exclusion and extension matching must behave the same regardless of source. Any change to `filters` or engine matching must be validated against FS and Repo tests.
- Tests touching this parity:
  - FS: `tests/test_options_fs.py::test_exclude_glob_and_literal`, `::test_extension_filters_by_extension`
  - Repo: `tests/test_options_repo.py::test_repo_exclude_glob_and_literal`, `::test_repo_extension_filters`

### Parity 6 — SourceAdapter protocol implemented uniformly by all adapters
- Elements:
  - Protocol: `src/prin/core.py`: `SourceAdapter` with `resolve_root`, `list_dir`, `read_file_bytes`, `is_empty`
  - Implementations: `src/prin/adapters/filesystem.py`, `src/prin/adapters/github.py`, `src/prin/adapters/website.py`
- Invariant:
  - Each adapter must implement the four methods with identical semantics expected by the engine:
    - `list_dir` raises `NotADirectoryError` when given a file path so explicit roots force-include
    - `resolve_root` returns a stable POSIX-like root for display-path calculations
    - `is_empty` semantics are consistent (see Parity 7)
- Tests touching this parity:
  - FS engine traversal/roots: `tests/test_cli_engine_tmp_path.py`, `tests/test_cli_engine_positional.py`
  - Repo positional semantics: `tests/test_print_repo_positional.py`
  - Mixed invocation: `tests/test_print_mixed_fs_repo.py`

### Parity 7 — Semantic emptiness detection shared across adapters
- Elements:
  - `src/prin/core.py`: `is_blob_semantically_empty`, `_is_text_semantically_empty`
  - Adapters: FS (`is_empty` uses shared function), GitHub (`is_empty` uses shared function), Website (`is_empty` returns False; emptiness determined after download if needed)
- Invariant:
  - A single definition of "semantically empty" governs FS and GitHub sources (Python-only at present). Changes must update both adapters and associated tests.
- Tests touching this parity:
  - FS: `tests/test_filesystem_source.py` (empty/non-empty Python and text files)
  - Repo: `tests/test_options_repo.py::test_repo_include_empty`

### Parity 8 — Display-path normalization across sources
- Elements:
  - `DepthFirstPrinter._display_path` and anchor-base logic in `run`
  - Adapter `resolve_root` implementations (FS yields absolute POSIX, GitHub uses repo-relative, Website uses a virtual root)
- Invariant:
  - Printed paths are relative to the provided roots (or the anchor base) and use POSIX separators consistently across sources.
- Tests touching this parity:
  - FS: `tests/test_cli_engine_positional.py`
  - Repo: `tests/test_print_repo_positional.py`

### Parity 9 — Global file budget across sources (`--max-files`)
- Elements:
  - `src/prin/core.py`: `FileBudget`
  - `src/prin/prin.py`: single `FileBudget` instance shared across FS/Repo/Website runs
- Invariant:
  - The budget must be enforced globally across all sources in one invocation. New sources must consume from the same budget.
- Tests touching this parity:
  - FS: `tests/test_max_files_fs.py`
  - Repo: `tests/test_max_files_repo.py`

### Parity 10 — GitHub URL subpath handling
- Elements:
  - `src/prin/util.py`: `extract_in_repo_subpath` (parses `/blob/`, optional branch, subpaths)
  - `src/prin/prin.py`: derives repo roots from the extracted subpath and sets `repo_ctx = ctx.replace(no_ignore=True, paths=[""])`
- Invariant:
  - URL-to-root translation logic in `util` and its use in `prin.main` must agree so that explicit file or subdirectory URLs behave as explicit roots and force-include as needed.
- Tests touching this parity:
  - Repo positional cases: `tests/test_print_repo_positional.py`

### Parity 11 — CLI alias behavior
- Elements:
  - `src/prin/cli_common.py`: `CLI_OPTIONS_ALIASES` expansion (e.g., `-uu` → `--hidden --no-ignore`)
  - Direct short/long flags declared on the parser (e.g., `-u/--unrestricted`, `-uuu/--no-exclude`)
- Invariant:
  - Aliases must expand to semantically equivalent flag sets. Keep alias table, parser declarations, and README consistent.
- Tests touching this parity:
  - FS: `tests/test_options_fs.py::test_uu_includes_hidden_and_gitignored`, `::test_unrestricted_includes_gitignored` (note: `.gitignore` parsing is intentionally skipped)

### Parity 12 — Test coverage parity for FS vs Repo
- Elements:
  - Options exercised in both suites: `tests/test_options_fs.py` and `tests/test_options_repo.py`
  - Budget tests: `tests/test_max_files_fs.py` and `tests/test_max_files_repo.py`
- Invariant:
  - Mature CLI behaviors should be covered for both adapters (filesystem and GitHub), unless the feature is intentionally source-specific. When adding a new option/behavior, add or adapt tests in both locations.

### Parity 13 — Website adapter URL list parsing ↔ tests
- Elements:
  - `src/prin/adapters/website.py`: `_parse_llms_txt`, URL resolution, key naming/dedup logic
  - Tests: `tests/test_website_adapter.py`, `tests/test_website_adapter_all_urls.py` (monkeypatch `_parse_llms_txt` and assert all URLs are printed)
- Invariant:
  - The adapter’s interpretation of `llms.txt` and header naming must remain stable with the tests’ expectations. Changes here require test updates.


## Candidates to confirm (borderline parities)

- Filters classifier coupling: `filters.is_glob` delegates to `path_classifier._is_glob`; tests live in `tests/test_pattern_classifier.py`. If classification rules change, `is_excluded` behavior can shift. Treat as a soft parity between `path_classifier.py` and `filters.py`.
- README “Options Roadmap” status badges (implemented/planned) vs actual parser/options. Keep roughly aligned, but this is informative rather than normative; prefer Parity 1 as the source of truth.
- Web and GitHub HTTP GET disk caches (`adapters/website.py` vs `adapters/github.py`) share similar patterns but are not required to be identical. Only treat as a parity if you intentionally standardize them.


## Change checklist (apply to any affected parity)

- Update all listed elements under the relevant parity.
- Run `./test.sh` (or with `--no-network` when appropriate) and fix regressions.
- Verify README examples and help text still match behavior.
- For new options/tags/sources: add tests for FS and Repo (and Website when applicable).

