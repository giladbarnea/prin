---
audience: AI agents
description: records the dependencies between elements in the codebase
updated: after making changes in the code
authority rank: ”eventual“ source of truth. code changes first, then locking-in a snapshot of the codebase in this file. absolute source of truth before first change.
---

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
- `README.md`: Options documented under "Options"/usage; pattern-then-path syntax examples.
- `src/prin/cli_common.py`: `parse_common_args(...)` flags and help; `Context` dataclass fields with `pattern` and `search_path`; `_expand_cli_aliases`.
- `src/prin/defaults.py`: `DEFAULT_*` used by CLI defaults and choices.
- `src/prin/core.py`: `DepthFirstPrinter._set_from_context` minimal consumption for printing behavior.
- `src/prin/adapters/*`: `SourceAdapter.configure(Context)` consumes CLI-derived configuration.

#### Contract
- CLI accepts two positional arguments: pattern (optional, defaults to "") and search_path (optional, defaults to None/cwd).
- One-to-one mapping between CLI flags and `Context` fields, including default values from `defaults.py` and documented behavior in `README.md`.
- If a flag affects traversal, filtering, or output, the adapter must consume it via `configure(Context)`; printer only consumes printing-related flags (e.g., `only_headers`, `tag`, `max_files`).
- `README.md` must document only implemented flags with correct semantics (no "planned" flags presented as implemented).

#### Triggers
- Adding/removing/renaming a flag; changing a default; changing flag semantics.

#### Tests
- Filesystem options: `tests/test_options_fs.py`
- Repository options: `tests/test_options_repo.py`

## Set 2 [FORMATTERS-CLI-TAG-OPTION]: Tag choices ↔ Formatter classes ↔ Defaults ↔ README examples
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

## Set 3 [ONLY-HEADERS-ENFORCEMENT-WITH-HEADERFORMATTER]: `--only-headers` flag ↔ `HeaderFormatter` behavior
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

## Set 4 [FILTER-CATEGORIES-CLI-FLAGS-DEFAULTS-CONTEXT-FIELDS-TESTS-FS-FIXTURE-README]: Filter categories ↔ CLI flags ↔ Defaults ↔ Context fields ↔ FS Tests fixture ↔ README

#### Members
- `src/prin/cli_common.py`: CLI flags, `Context` fields, CLI documentation in `parse_common_args`.
- `src/prin/defaults.py`: patterns in `DEFAULT_EXCLUSIONS`, `DEFAULT_TEST_EXCLUSIONS`, `DEFAULT_LOCK_EXCLUSIONS`, `DEFAULT_BINARY_EXCLUSIONS`, `DEFAULT_DOC_EXTENSIONS`, `Hidden`; default CLI configuration by all the `DEFAULT_*` scalar constants.
- `README.md` sections: “Sane Defaults for LLM Input”, “Output Control”, CLI Options”.
- FS test fixture: `tests/conftest.py::fs_root` (mock files/paths and `VFS` field for each category).

#### Contract
- Filter flags exposed by the CLI in `cli_common.py` must have corresponding DEFAULT_* patterns and DEFAULT_* feature flags in `defaults.py`, `Context` fields, representation in `README.md` in specified sections, synced CLI help in `parse_common_args`, mocks in `conftest.fs_root` and a field in `conftest.VFS`.
 - Hidden category in the FS fixture is represented by files under dot-directories (e.g., `.github/config`, `app/submodule/.git/config`); directories themselves are not printed.
 - Build directory exclusion uses path-bounded regex `(^|/)build(/|$)`; minified assets are excluded by default via `*.min.*`; doc extensions include `*.1`.

#### Triggers
- Adding/removing/renaming a filter category; changing category semantics.

#### Tests
- FS flags toggling categories: `tests/test_options_fs.py` (for example, `--hidden`, `--include-tests`, `--include-lock`, `--include-binary`, `--no-docs`, `--include-empty`, `--exclude`, `--no-exclude`, `--extension`).
- Repo analogs: `tests/test_options_repo.py`.


## Set 5 [FILTERS-CONSISTENCY-ACROSS-SOURCES]: Path exclusion and extension semantics ↔ Pattern classifier
#### Members
- `src/prin/adapters/*`: `should_print(entry)` implementations.
- `src/prin/filters.py`: `is_excluded`, `extension_match`, `get_gitignore_exclusions`.
- `src/prin/path_classifier.py`: `classify_pattern`, `is_glob`, `is_extension`, `is_regex`.
- `src/prin/cli_common.py`: `_normalize_extension_to_glob`.

#### Contract
- Inclusion/exclusion and extension matching must behave identically regardless of source type. Any change to filters must be validated across adapters. Adapters may delegate to `filters.*` to keep behavior consistent.
- The classifier distinguishes two kinds of patterns: `regex` and `glob`.
  * `regex`: matched by `re.search`.
  * `glob`: matched via `fnmatch`.
- Explicit extensions are normalized by `_normalize_extension_to_glob`. Changes to normalization rules must be reflected in `filters.is_excluded` and `filters.extension_match` behavior.
- Changes to classifier rules must be reflected in `filters.is_excluded` and `filters.extension_match` behavior.

#### Triggers
- Changing matching rules, glob/regex detection, or text-token semantics. Changing extension normalization rules.

#### Tests
- FS: `tests/test_options_fs.py::test_exclude_glob_and_literal`, `::test_extension_filters_by_extension`, `::test_literal_exclude_token_matches_segments_not_substrings`
- Repo: `tests/test_options_repo.py::test_repo_exclude_glob_and_literal`, `::test_repo_extension_filters`, `::test_repo_literal_exclude_token_matches_segments_not_substrings`
- Classifier: `tests/test_pattern_classifier.py` (covers `regex`/`glob`)


## Set 6 [SOURCE-ADAPTER-INTERFACE]: Protocol and uniform adapter semantics

#### Members
- Protocol: `src/prin/core.py`: `SourceAdapter` with `configure`, `walk_pattern`, `should_print`, `read_body_text`, `resolve`, `exists` (and `Entry`/`NodeKind` shapes).
- Implementations: `src/prin/adapters/filesystem.py`, `src/prin/adapters/github.py`, `src/prin/adapters/website.py`.

#### Contract
- Adapters implement a uniform interface:
  - `configure(Context)` consumes CLI-derived config.
  - `walk_pattern(pattern, search_path)` yields files matching pattern in search_path.
  - `should_print(entry)` applies exclusions/extensions/emptiness (`Entry.explicit` forces include).
  - `read_body_text(entry)` returns (text, is_binary) for the printer.
- `resolve`/`exists` keep lexical resolution rules; `is_empty` should adhere to shared definition (see Set 7).

#### Triggers
- Changing the protocol, method contracts, or `Entry`/`NodeKind` shapes; adding a new adapter.

#### Tests
- FS traversal/roots: `tests/test_cli_engine_tmp_path.py`, `tests/test_cli_engine_positional.py`.
- Repo positional semantics: `tests/test_print_repo_positional.py`.
- Mixed invocation: `tests/test_print_mixed_fs_repo.py`.
- Adapter specifics: `tests/test_filesystem_source.py`, `tests/test_github_adapter.py`, `tests/test_website_adapter.py`, `tests/test_website_adapter_all_urls.py`.

## Set 7 [SEMANTIC-EMPTINESS-ADAPTERS]: Shared definition across adapters

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

## Set 10 [CLI-ALIAS-BEHAVIOR-README]: Alias expansion ↔ canonical flags
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
#### Members
- `src/prin/core.py`: `SourceAdapter` protocol.
- `src/prin/adapters/filesystem.py`: `FileSystemSource` implementation.
- `src/prin/adapters/github.py`: `GitHubRepoSource` implementation.
- `src/prin/adapters/website.py`: `WebsiteSource` implementation.
- `tests/test_options_fs.py`, `tests/test_options_repo.py`: cover each CLI flag end-to-end per source.
- `tests/test_cli_engine_*.py`: traversal and path display behavior.
- `tests/test_max_files_*.py`: `--max-files` semantics.
- `tests/test_website_adapter_*.py`: website parsing and rendering.
- `tests/conftest.py`: adapter-specific pytest markers and selection flags (`--website`, `--repo`, `--no-website`, `--no-repo`).
- `pyproject.toml` `[tool.pytest.ini_options].markers`: `website`, `repo` declarations.

#### Contract
- For each implemented feature/flag, maintain parallel coverage for filesystem and GitHub (and website where applicable). Adding a feature implies adding/adapting tests in all relevant suites.
 - Adapter markers/flags must map 1:1 to source adapters; include flags restrict to marked suites; exclude flags skip them.

#### Triggers
- Adding a new option/behavior; adding a new adapter.

#### Tests
- FS: `tests/test_options_fs.py` (for example flags); Repo: `tests/test_options_repo.py`; Website: `tests/test_website_adapter_*.py`.
- Marker selection honored: `./test.sh --website` runs only website-marked tests; `./test.sh --no-repo` skips repo-marked tests.

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

## Set 13 [CLI-URL-ROUTING-ADAPTERS]: Token routing to adapters
#### Members
- `src/prin/prin.py`: routing of input tokens across filesystem, GitHub, and website; repo subpath extraction; global `FileBudget` use.
- `src/prin/util.py`: `is_github_url`, `is_http_url`
- `src/prin/adapters/github.py`: `parse_github_url` → `owner`, `repo`, `subpath`, `ref`

#### Contract
- Routing logic and helper predicates must align:
- Tokens classified as GitHub are handled by the GitHub adapter; HTTP non-GitHub goes to the Website adapter; everything else is treated as local filesystem.
- Repo subpaths are extracted consistently and reflected in traversal roots. Subpaths may include a trailing pattern segment (glob/regex). The adapter must traverse the literal base and match the pattern against full display-relative paths under that base.
- Adapters provide a clear domain “matches” check that `prin.py` relies on.

#### Triggers
- Changing URL detection, subpath rules, or adding a new source kind.

#### Tests
- `tests/test_print_repo_positional.py`, `tests/test_print_mixed_fs_repo.py`, `tests/test_max_files_*`, `tests/test_github_adapter.py`.
- `tests/test_github_adapter_combinatorics.py::test_parse_github_url_combinations`

## Set 14 [README-EXAMPLES-CLI-REALITY]: Documentation ↔ observed behavior
#### Members
- `README.md`: examples and described behavior/flags
- `src/prin/prin.py` and adapters: actual behavior
- `src/prin/cli_common.py`: exposed CLI flags and options.
- End-to-end tests that exercise the same stories.

#### Contract
- README claims must match implemented behavior and flags; examples should be runnable as shown.

#### Triggers
- Any behavior or flag change; example edits.

#### Tests
- Covered indirectly via options and mixed-source tests; add story-based tests if examples grow in complexity.

## Set 15 [EXPLICIT-PATH-FORCE-INCLUDE]: Explicit files bypass exclusions
#### Members
- `src/prin/adapters/*`: `walk(token)` sets `Entry.explicit=True` for explicit file roots; adapters’ `should_print` honors it.
- `src/prin/core.py`: duplicate suppression by absolute path key remains in the printer.

#### Contract
- Passing an explicit path must print it even if default exclusions would skip it. This applies uniformly across adapters via `Entry.explicit=True` and `should_print` implementation.

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

## Set 17 [PATTERN-THEN-PATH]: Pattern-then-path interface

#### Members
- `src/prin/cli_common.py`: positional args parsing (pattern, search_path).
- `src/prin/core.py`: `DepthFirstPrinter.run_pattern` method.
- `src/prin/prin.py`: main dispatcher logic.
- `src/prin/adapters/*`: `walk_pattern(pattern, search_path)` implementations.
- `README.md`: what-then-where usage examples.

#### Contract
- First arg is pattern (glob/regex), second is search path (optional, defaults to cwd).
- Pattern matching happens against full relative paths from search location.
- Empty pattern means list all files in the path.
- Paths are displayed relative to search location.

#### Triggers
- Changing pattern matching semantics; modifying path display logic.

#### Tests
- Integration: `tests/test_integration_what_then_where.py`
- Pattern search: `tests/test_pattern_search.py`

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

## Work Against and Update PARITIES.md

1. **`PARITIES.md` is the source of truth** for what’s going on in the project. You are responsible for keeping it accurate after you have completed your task.
2. Initially, before making code changes: **map your plan against `PARITIES.md`.** Identify which elements will be affected by your changes and have a general idea of what you’ll need to update when you’re done. 
* An ‘element’ is a piece of information ranging from a reference to a single symbol to a Member line, or, rarely, an entire set.
3. After everything is working: **return to `PARITIES.md` and surgically update** any parts that are no longer accurate due to your changes. **Add any new items introduced by your task**, and **follow the instructions in [Maintaining PARITIES.md](PARITIES.md)**.

