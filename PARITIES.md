# PARITIES
### Purpose
Define deliberate couplings in the codebase—places, or _members_, that must remain equivalent in meaning and behavior. This doc is designed to be:
1. Read when starting a task to grok how things are connected in the project. Helps avoid breaking dependencies.
2. Updated after finishing your task.

### Scope

**Parities.**
- Parities are high-signal, indisputable links between different elements of the project.
- These are intentional parities, not code smells. The threshold for inclusion is high and obvious.

**Sets.**
- This document is a list of parity _sets_: chains of entangled members that exist around the codebase.
- If one member in a parity set changes, the rest of the members need be changed accordingly.

**Members.**
- Members are what a codebase consists of. They range from a single code symbol (a class/function name), to an entire file or module.
- Members can be coupled in a variety of ways.

### Conventions

1. Each parity set lists an ID, Members (with precise locations/symbols), a Contract (what must stay in sync), Triggers (what changes require syncing), and Tests (coverage that asserts the contract).
2. Always use backticks when referring to a `file.ext`, `dir/`, `Symbol`, `function`, etc.

### Always finish off your task by updating PARITIES.md

**You are responsible for updating this document after you've completed your task, to make it reflect the new state of the project.**

See "Maintaining `PARITIES.md`" section at the bottom of this file for detailed instructions on how to do this.

---

# Parity Sets

## Set 1 [CLI-CTX-DEFAULTs-README]: CLI options ↔ Context fields ↔ Defaults ↔ README

#### Members
- `README.md`: Options documented under “Options”/usage.
- `src/prin/cli_common.py`: `parse_common_args(...)` flags and help; `Context` dataclass fields; `_expand_cli_aliases`.
- `src/prin/defaults.py`: `DEFAULT_*` used by CLI defaults and choices.
- `src/prin/core.py`: `DepthFirstPrinter._set_from_context` consumption/behavior tied to flags.

#### Contract
- One-to-one mapping between CLI flags and `Context` fields, including default values from `defaults.py` and documented behavior in `README.md`.
- If a flag affects traversal, filtering, or output, `DepthFirstPrinter` must consume the corresponding `Context` field explicitly.
- `README.md` must document only implemented flags with correct semantics (no “planned” flags presented as implemented).

#### Triggers
- Adding/removing/renaming a flag; changing a default; changing flag semantics.

#### Tests
- Filesystem options: `tests/test_options_fs.py`
- Repository options: `tests/test_options_repo.py`

## Set 2 [FORMATTER-SELECTION]: Tag choices ↔ Formatter classes ↔ Defaults ↔ README examples
#### Members
- `src/prin/prin.py`: tag→formatter dispatch
- `src/prin/formatters.py`: `XmlFormatter`, `MarkdownFormatter`, `HeaderFormatter`.
- `src/prin/defaults.py`: `DEFAULT_TAG_CHOICES`.
- `README.md`: output examples for available tags.

#### Contract
- Values in `DEFAULT_TAG_CHOICES` must exactly match the dispatch table in `prin.py`, and a concrete formatter class must exist for each value.
- README examples must reflect the actual output shape for each tag.

#### Triggers
- Adding a tag; changing a formatter’s behavior/format.

#### Tests
- `tests/test_options_fs.py::test_tag_md_outputs_markdown_format`
- `tests/test_options_repo.py::test_repo_tag_md_outputs_markdown_format`

## Set 3 [ONLY-HEADERS-ENFORCEMENT]: `--only-headers` flag ↔ `HeaderFormatter` behavior
#### Members
- `src/prin/cli_common.py`: `Context.only_headers` / CLI: `-l/--only-headers`.
- `src/prin/core.py`: `DepthFirstPrinter` forcing `HeaderFormatter` when `only_headers=True`.
- `src/prin/formatters.py`: `HeaderFormatter`.

#### Contract
- When `only_headers` is true, body content must not be printed, regardless of any explicitly selected formatter.

#### Triggers
- Changing `only_headers` semantics or formatter enforcement.

#### Tests
- FS: `tests/test_options_fs.py::test_only_headers_prints_headers_only`
- Repo: `tests/test_options_repo.py::test_repo_only_headers_prints_headers_only`

## Set 4 [FILTER-CATEGORIES-FS-FIXTURE]: Default filter categories ↔ Defaults ↔ README ↔ FS fixture

#### Members
- `src/prin/defaults.py`: `DEFAULT_EXCLUSIONS`, `DEFAULT_TEST_EXCLUSIONS`, `DEFAULT_LOCK_EXCLUSIONS`, `DEFAULT_BINARY_EXCLUSIONS`, `DEFAULT_DOC_EXTENSIONS`, `Hidden`.
- `README.md`: “Sane Defaults for LLM Input” (categories listed).
- FS test fixture: `tests/conftest.py::fs_root` (examples for each category).

#### Contract
- Categories defined in `defaults.py` must be described in README, and `fs_root` must include representative files for coverage. Any category change requires updates to all three.

#### Triggers
- Adding/removing/renaming a category; changing category semantics.

#### Tests
- FS flags toggling categories: `tests/test_options_fs.py` (for example, `--hidden`, `--include-tests`, `--include-lock`, `--include-binary`, `--no-docs`, `--include-empty`, `--exclude`, `--no-exclude`, `--extension`).
- Repo analogs: `tests/test_options_repo.py`.


## Set 5 [FILTERS-CONSISTENCY-ACROSS-SOURCES]: Exclusion and extension semantics ↔ Pattern classifier
#### Members
- `src/prin/core.py`: `DepthFirstPrinter._excluded`, `_extension_match`.
- `src/prin/filters.py`: `is_excluded`, `is_extension`, `get_gitignore_exclusions`.
- `src/prin/path_classifier.py`: `classify_pattern`, `is_glob`, `is_extension`, `is_regex`.
- Adapters used via `DepthFirstPrinter`: filesystem, GitHub, website.

#### Contract
- Inclusion/exclusion and extension matching must behave identically regardless of source type. Any change to filters or engine matching must be validated for both filesystem and repository sources.
- The classifier distinguishes three kinds of patterns: `regex`, `glob`, and `text`.
  * `regex`: Not implemented.
  * `glob`: matched via `fnmatch`.
  * `text`: matched by exact path-segment sequence, not substrings; supports multi-part tokens containing separators.
  * Explicit extensions (e.g., `.py`) match by suffix.
- Changes to classifier rules must be reflected in `filters.is_excluded` behavior.

#### Triggers
- Changing matching rules, glob/regex detection, or text-token semantics.

#### Tests
- FS: `tests/test_options_fs.py::test_exclude_glob_and_literal`, `::test_extension_filters_by_extension`, `::test_literal_exclude_token_matches_segments_not_substrings`
- Repo: `tests/test_options_repo.py::test_repo_exclude_glob_and_literal`, `::test_repo_extension_filters`, `::test_repo_literal_exclude_token_matches_segments_not_substrings`
- Classifier: `tests/test_pattern_classifier.py` (covers `regex`/`glob`/`text`)


## Set 6 [SOURCE-ADAPTER-INTERFACE]: Protocol and uniform adapter semantics

#### Members
- Protocol: `src/prin/core.py`: `SourceAdapter` with `resolve_root`, `list_dir`, `read_file_bytes`, `is_empty` (and `Entry`/`NodeKind` shapes).
- Implementations: `src/prin/adapters/filesystem.py`, `src/prin/adapters/github.py`, `src/prin/adapters/website.py`.

#### Contract
- All adapters implement the four methods with identical semantics expected by the engine:
- `resolve_root` returns a stable POSIX-like root for display anchoring.
- `list_dir` raises `NotADirectoryError` when the input is a file (so explicit roots are force-included).
- `read_file_bytes` returns raw bytes.
- `is_empty` uses shared semantic emptiness (see Set 7); Website may defer emptiness until after fetch but must honor the shared definition.

#### Triggers
- Changing the protocol, method contracts, or `Entry`/`NodeKind` shapes; adding a new adapter.

#### Tests
- FS traversal/roots: `tests/test_cli_engine_tmp_path.py`, `tests/test_cli_engine_positional.py`.
- Repo positional semantics: `tests/test_print_repo_positional.py`.
- Mixed invocation: `tests/test_print_mixed_fs_repo.py`.
- Adapter specifics: `tests/test_filesystem_source.py`, `tests/test_github_adapter.py`, `tests/test_website_adapter.py`, `tests/test_website_adapter_all_urls.py`.

## Set 7 [SEMANTIC-EMPTINESS]: Shared definition across adapters

#### Members
- `src/prin/core.py`: `is_blob_semantically_empty`, `_is_text_semantically_empty`.
- Adapter usage: filesystem and GitHub `is_empty` delegate to shared function; Website returns False at routing time and defers to shared logic post-fetch when applicable.

#### Contract
- A single definition of “semantically empty” (Python-aware today) governs all adapters. The `--include-empty` flag toggles printing of otherwise empty blobs.

#### Triggers
- Changing emptiness heuristics or language coverage.

#### Tests
- FS: `tests/test_filesystem_source.py` (empty/non-empty Python and text files).
- Repo: `tests/test_options_repo.py::test_repo_include_empty`.

## Set 9 [BUDGET-GLOBALITY]: One global file budget across sources (`--max-files`)
#### Members
- `src/prin/core.py`: `FileBudget`.
- `src/prin/prin.py`: single `FileBudget` instance shared across all sources.

#### Contract
- The budget is enforced globally across all sources during a single invocation. New sources must share the same budget.

#### Triggers
- Changing budget semantics or introducing per-source budgets.

#### Tests
- FS: `tests/test_max_files_fs.py`.
- Repo: `tests/test_max_files_repo.py`.
- Mixed: `tests/test_print_mixed_fs_repo.py`.

## Set 10 [CLI-ALIAS-BEHAVIOR]: Alias expansion ↔ canonical flags
#### Members
- `src/prin/cli_common.py`: `CLI_OPTIONS_ALIASES` (for example, `-uu` → `--hidden` `--no-ignore`) and parser declarations (for example, `-u`/`--unrestricted`, `-uuu`/`--no-exclude`).
- `README.md`: alias documentation.

#### Contract
- Aliases must expand to semantically equivalent canonical flag sets. Keep alias table, parser declarations, and README consistent.

#### Triggers
- Adding/removing an alias; changing the flags an alias expands to.

#### Tests
- FS: `tests/test_options_fs.py::test_uu_includes_hidden_and_gitignored`, `::test_unrestricted_includes_gitignored` (note: `.gitignore` behavior is currently stubbed; see Set 16).

## Set 11 [TEST-COVERAGE-PARITY]: Feature coverage mirrored per source
// todo: this set needs to add the adapters and their baseclass to Members

#### Members
- `tests/test_options_fs.py`, `tests/test_options_repo.py`: cover each CLI flag end-to-end per source.
- `tests/test_cli_engine_*.py`: traversal and path display behavior.
- `tests/test_max_files_*.py`: `--max-files` semantics.
- `tests/test_website_adapter_*.py`: website parsing and rendering.

#### Contract
- For each implemented feature/flag, maintain parallel coverage for filesystem and GitHub (and website where applicable). Adding a feature implies adding/adapting tests in all relevant suites.

#### Triggers
- Adding a new option/behavior; adding a new adapter.

## Set 12 [WEBSITE-LLMS-TXT-PARSING]: URL list parsing ↔ rendering
#### Members
- `src/prin/adapters/website.py`: `_parse_llms_txt`, URL normalization, key naming/deduplication.
- `src/prin/prin.py`: website routing and `WebsiteSource` usage.

#### Contract
- All Markdown links and raw URLs listed by the website’s URL manifest are parsed and fetched; duplicates are deduplicated by key (with suffixing rules as needed); output rendered via the selected formatter.

#### Triggers
- Changing the website URL-manifest interpretation, URL normalization, or keying rules.

#### Tests
- `tests/test_website_adapter.py`, `tests/test_website_adapter_all_urls.py`.

## Set 13 [CLI-URL-ROUTING]: Token routing to adapters
#### Members
- `src/prin/prin.py`: routing of input tokens across filesystem, GitHub, and website; repo subpath extraction; global `FileBudget` use.
- `src/prin/util.py`: `is_github_url`, `is_http_url`
- `src/prin/adapters/github.py`: `parse_github_url` → `owner`, `repo`, `subpath`

#### Contract
- Routing logic and helper predicates must align:
- Tokens classified as GitHub are handled by the GitHub adapter; HTTP non-GitHub goes to the Website adapter; everything else is treated as local filesystem.
- Repo subpaths are extracted consistently and reflected in traversal roots.
- Adapters provide a clear domain “matches” check that `prin.py` relies on.

#### Triggers
- Changing URL detection, subpath rules, or adding a new source kind.

#### Tests
- `tests/test_print_repo_positional.py`, `tests/test_print_mixed_fs_repo.py`, `tests/test_max_files_*`, `tests/test_github_adapter.py`.

## Set 14 [README-EXAMPLES-REALITY]: Documentation ↔ observed behavior
#### Members
- `README.md`: examples and described behavior/flags
- `src/prin/prin.py` and adapters: actual behavior
- End-to-end tests that exercise the same stories.

#### Contract
- README claims must match implemented behavior and flags; examples should be runnable as shown.

#### Triggers
- Any behavior or flag change; example edits.

#### Tests
- Covered indirectly via options and mixed-source tests; add story-based tests if examples grow in complexity.

## Set 15 [EXPLICIT-PATH-FORCE-INCLUDE]: Explicit files bypass exclusions
#### Members
- `src/prin/core.py`: DFS handling of `NotADirectoryError` → force include; duplicate suppression.
- `src/prin/adapters/github.py`: file-path responses raise `NotADirectoryError`.
- `src/prin/adapters/filesystem.py`: `list_dir` uses `scandir` semantics; explicit file roots handled by the engine.

#### Contract
- Passing an explicit path must print it even if default exclusions would skip it. This applies uniformly across adapters.

#### Triggers
- Changing explicit-path routing or how adapters signal file vs directory.

#### Tests
- FS: `tests/test_cli_engine_positional.py::test_directory_and_explicit_ignored_file_inside`.
- Repo: `tests/test_print_repo_positional.py::test_repo_explicit_ignored_file_is_printed`.

## Set 16 [GITIGNORE-BEHAVIOR]: Current `.gitignore` semantics

#### Members
- `src/prin/filters.py`: `get_gitignore_exclusions` (currently returns `[]`).
- `src/prin/cli_common.py`: `Context.__post_init__` composition of exclusions with `no_ignore`.

#### Contract
- Until real `.gitignore` parsing is implemented, gitignored files are not excluded by default. Flags (`--no-ignore`, `-u`, `-uu`) remain consistent with current stubbed behavior and README/alias documentation.

#### Triggers
- Implementing real `.gitignore` parsing; changing the meaning of `no_ignore`/`unrestricted`.

#### Tests
- FS: `tests/test_options_fs.py::test_unrestricted_includes_gitignored` (and any currently skipped tests around `.gitignore` or `no-ignore`).

---

### Notes on interplay
- Sets 4, 5, and 7 together govern filtering: category defaults, cross-source consistency, and semantic emptiness.
- Set 1 and Set 10 together ensure CLI shape (flags, defaults, aliases) stays truthful, with Set 14 keeping README aligned.
- Set 6 (protocol) and Set 13 (routing) ensure adapters are both selectable and interoperable once selected.
- Set 9 (budget) must be honored by all traversal code paths, including explicit force-includes (Set 15) and website fetching (Set 12).

-----------------------------------------

# Important: Maintaining `PARITIES.md`

This section defines how to keep `PARITIES.md` truthful, accurate, terse, and durable as the project evolves.

## Maintaining PARITIES.md: Contract
- `PARITIES.md` is a **snapshot** of the codebase, not a history or design doc.
- Each set uses the **same minimal structure** (see “Set block template”).
- Prefer **cross-references** by Set ID over repetition.
- Keep **signal over noise**: short, testable, and unambiguous.
- You are responsible for updating it after making changes that have to do with any of the members it lists. 

## Update `PARITIES.md`: Definition of Done

DoD: PARITIES.md is once again a snapshot of the codebase, pointing out intentionally coupled elements and paired aspects in the codebase.

1. Fix elements that have been moved or renamed
2. Delete references to elements that have been deleted
3. Integrate newly created elements into the parity sets:
a. Add to the set (or multiple sets) of members they are coupled to, and 
b. Reference in other parity sets where appropriate.


## Parity Set Structure 
Keep this exact shape in every new or existing set:

```
## Set <ID>: <Short name, 3–6 words>

#### Members
- <repo-path>:<symbol-or-scope>
- <repo-path>:<symbol-or-scope>

#### Contract
- <single-sentence rule>
- <single-sentence rule>

#### Triggers
- <event that requires syncing>
- <event that requires syncing>

#### Tests
- <suite-or-path>::<test_name>
- <suite-or-path>::<test_name>
```

**Style rules**
- **Members:** exact paths and symbols only; one item per line; no ranges.
- **Contract/Triggers:** short, actionable sentences; avoid explanatory prose.
- **Tests:** name the smallest checks that prove the contract.
- **Cross-reference:** if another set owns a rule, write “See: Set `<ID>`”.

## Size discipline (line-delta rules)
These three rules keep growth proportional to real scope changes:

1. **Removal → shrink**
When behavior/files are removed, delete all corresponding lines here.
*Expected net effect: total lines **decrease**.*
2. **Modification → steady**
When scope is unchanged, update in place without adding bullets or sentences.
*Expected net effect: total lines **unchanged**.*
3. **Addition → minimal growth**
When scope expands, add only what is strictly necessary:

- **+1** line per new **Member** item
- **≤1** new sentence in **Contract** and/or **Triggers** *if* semantics changed
- A brand-new set should rarely exceed **\~10 lines** total
If you exceed these budgets, ask the user to review.

## Edit recipes (apply one; prefer replacement over addition)

#### Remove a member
1. Delete the appropriate Members line; prune any now-irrelevant Contract/Triggers/Tests bullets.
2. Remove references throughout the document.
3. If a set loses all members, delete the set (rare).

#### Modify without expanding scope
1. Update references in the document and adjust wording **without** adding bullets.
2. Replace parts of sentences; do not append new ones.

#### Add an element or new member
1. Append **one** precise **Members** line.
2. Add **at most one** new sentence under **Contract/Triggers** if semantics truly changed.
3. Reference tests succinctly; prefer naming existing checks.
4. Add references in other sets who have members coupled to the new element/member.

#### Merge or split sets
Different sets can share members, although ideally this should be minimized. This is common with generic members used for a variety of different needs.  What draws a line between sets, even if they share a member or two,  is their domains. Each set deals with a different subject.

## Anti-patterns (avoid)

* Narrative explanations, examples that restate code, or historical context.
* Catch-all sets that mix unrelated concerns.
* “Future work” notes; put those in issues, not here.
* “Changelog” notes; don't emphasize something because it's new. There's no notion of "before" and "after".
* Duplicating rules across sets instead of cross-referencing.
* Vague members (for example, whole directories without symbol scoping).

## Operating principle
Treat `PARITIES.md` as a **switchboard**: it names the circuits (Members), the rule that keeps them synchronized (Contract), when to check them (Triggers), and the fuses that trip if something breaks (Tests). Keep labels exact, sentences short, and growth justified.
