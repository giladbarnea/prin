PARITIES — Single Source of Truth (Updated)

Purpose. Define deliberate couplings in the codebase—places that must remain equivalent in meaning and behavior. When any member of a set changes, review and update all other members to keep the set in lockstep.

Scope. These are intentional parities, not code smells. The threshold for inclusion is high and obvious.

Guidance for maintainers and code agents
	•	Prefer high-signal, indisputable parities. Do not add speculative links.
	•	When adding a feature or option, update all members of every affected set in the same edit series.
	•	If you cannot fix a parity immediately, add a TODO in the pull request description and open a follow-up issue.
	•	Tests called out under each set are the guardrails; add or update them alongside code changes.

Conventions. Each set lists an ID, Members (precise locations/symbols), a Contract (what must stay in sync), Triggers (what requires syncing), and Tests (coverage that asserts the contract).

⸻

Set 1 [CLI-CTX-DEFAULTs-README]: CLI options ↔ Context fields ↔ Defaults ↔ README

Members
	•	README.md (options and usage)
	•	src/prin/cli_common.py (parse_common_args(...), Context fields, _expand_cli_aliases)
	•	src/prin/defaults.py (DEFAULT_* used by CLI defaults and choices)
	•	src/prin/core.py (DepthFirstPrinter._set_from_context consumption/behavior tied to flags)

Contract
	•	One-to-one mapping between CLI flags and Context fields, including default values from defaults.py and documented behavior in README.md.
	•	If a flag affects traversal, filtering, or output, DepthFirstPrinter consumes the corresponding Context field explicitly.
	•	README documents only implemented flags with correct semantics.

Triggers
	•	Adding/removing/renaming a flag; changing a default; changing flag semantics.

Tests
	•	tests/test_options_fs.py, tests/test_options_repo.py

⸻

Set 2 [FORMATTER-SELECTION]: Tag choices ↔ Formatter classes ↔ Defaults ↔ README examples

Members
	•	src/prin/prin.py (tag→formatter dispatch)
	•	src/prin/formatters.py (XmlFormatter, MarkdownFormatter, HeaderFormatter)
	•	src/prin/defaults.py (DEFAULT_TAG_CHOICES)
	•	README.md (output examples)

Contract
	•	Values in DEFAULT_TAG_CHOICES exactly match the dispatch table in prin.py, with a concrete formatter class for each value.
	•	README examples reflect the actual output shape for each tag.

Triggers
	•	Adding a tag; changing a formatter’s behavior or format.

Tests
	•	tests/test_options_fs.py::test_tag_md_outputs_markdown_format
	•	tests/test_options_repo.py::test_repo_tag_md_outputs_markdown_format

⸻

Set 3 [ONLY-HEADERS-ENFORCEMENT]: --only-headers flag ↔ HeaderFormatter behavior

Members
	•	src/prin/cli_common.py (Context.only_headers / CLI: -l/--only-headers)
	•	src/prin/core.py (DepthFirstPrinter forcing HeaderFormatter)
	•	src/prin/formatters.py (HeaderFormatter)

Contract
	•	When only_headers is true, body content must not be printed, regardless of selected formatter.

Triggers
	•	Changing only_headers semantics or formatter enforcement.

Tests
	•	FS: tests/test_options_fs.py::test_only_headers_prints_headers_only
	•	Repo: tests/test_options_repo.py::test_repo_only_headers_prints_headers_only

⸻

Set 4 [FILTER-CATEGORIES-FS-FIXTURE]: Default filter categories ↔ Defaults ↔ README ↔ FS fixture

Members
	•	src/prin/defaults.py (DEFAULT_EXCLUSIONS, DEFAULT_TEST_EXCLUSIONS, DEFAULT_LOCK_EXCLUSIONS, DEFAULT_BINARY_EXCLUSIONS, DEFAULT_DOC_EXTENSIONS, Hidden)
	•	README.md (defaults described)
	•	tests/conftest.py::fs_root (examples for each category)

Contract
	•	Categories defined in defaults.py are described in README, and fs_root includes representative files for coverage. Category changes update all three.

Triggers
	•	Adding/removing/renaming a category; changing category semantics.

Tests
	•	FS flags: tests/test_options_fs.py (e.g., --hidden, --include-tests, --include-lock, --include-binary, --no-docs, --include-empty, --exclude, --no-exclude, --extension)
	•	Repo analogs: tests/test_options_repo.py

⸻

Set 5 [FILTERS-CONSISTENCY-ACROSS-SOURCES]: Exclusion and extension semantics ↔ Pattern classifier

Members
	•	src/prin/core.py (DepthFirstPrinter._excluded, _extension_match)
	•	src/prin/filters.py (is_excluded, get_gitignore_exclusions, is_glob, is_extension)
	•	src/prin/path_classifier.py (classify_pattern, is_glob, is_extension, is_regex)
	•	All adapters via DepthFirstPrinter

Contract
	•	Inclusion/exclusion and extension matching behave identically across sources.
	•	The classifier distinguishes three kinds of patterns: regex, glob, and text.
	•	regex/glob: matched via fnmatch (regex-like patterns are treated through glob-equivalent matching as implemented).
	•	text: matched by exact path-segment sequence, not substrings; supports multi-part tokens containing separators.
	•	Explicit extensions (e.g., .py) match by suffix.
	•	Changes to classifier rules must be reflected in filters.is_excluded behavior.

Triggers
	•	Changing matching rules, glob/regex detection, or text-token semantics.

Tests
	•	FS: tests/test_options_fs.py::test_exclude_glob_and_literal, ::test_extension_filters_by_extension, ::test_literal_exclude_token_matches_segments_not_substrings
	•	Repo: tests/test_options_repo.py::test_repo_exclude_glob_and_literal, ::test_repo_extension_filters, ::test_repo_literal_exclude_token_matches_segments_not_substrings
	•	Classifier: tests/test_pattern_classifier.py (covers regex/glob/text)

⸻

Set 6 [SOURCE-ADAPTER-INTERFACE]: Protocol and uniform adapter semantics

Members
	•	src/prin/core.py (SourceAdapter, Entry, NodeKind)
	•	src/prin/adapters/filesystem.py, src/prin/adapters/github.py, src/prin/adapters/website.py

Contract
	•	All adapters implement resolve_root, list_dir (raise NotADirectoryError for files), read_file_bytes, is_empty with the semantics expected by the engine.
	•	resolve_root returns stable POSIX-like roots used for display anchoring.
	•	is_empty uses shared semantic emptiness (see Set 7).

Triggers
	•	Changing the protocol, method contracts, or Entry/NodeKind shapes; adding a new adapter.

Tests
	•	FS traversal/roots: tests/test_cli_engine_tmp_path.py, tests/test_cli_engine_positional.py
	•	Repo positional semantics: tests/test_print_repo_positional.py
	•	Mixed invocation: tests/test_print_mixed_fs_repo.py
	•	Adapter specifics: tests/test_filesystem_source.py, tests/test_github_adapter.py, tests/test_website_adapter.py, tests/test_website_adapter_all_urls.py

⸻

Set 7 [SEMANTIC-EMPTINESS]: Shared definition across adapters

Members
	•	src/prin/core.py (is_blob_semantically_empty, _is_text_semantically_empty)
	•	Adapters: filesystem and GitHub is_empty delegate to the shared function; website defers until after download.

Contract
	•	A single definition of “semantically empty” (Python-aware) governs all adapters. --include-empty toggles printing of otherwise empty blobs.

Triggers
	•	Changing emptiness heuristics or language coverage.

Tests
	•	FS: tests/test_filesystem_source.py
	•	Repo: tests/test_options_repo.py::test_repo_include_empty

⸻

Set 8 [DISPLAY-PATH-NORMALIZATION]: Consistent display paths and anchor-base semantics

Members
	•	src/prin/core.py (DepthFirstPrinter._display_path, anchor-base logic in run)
	•	Adapter resolve_root implementations

Contract
	•	Printed paths use POSIX separators and are relative to a display base determined as follows:
	1.	Compute anchor_base = source.resolve_root('.').
	2.	For each provided root r: if r is under anchor_base, display paths relative to anchor_base; otherwise, display paths relative to r itself (avoid .. segments like ../../../foo).
	•	Multiple roots may therefore print with different bases in one invocation.

Triggers
	•	Changing anchor resolution rules, base selection, or adapter root semantics.

Tests
	•	tests/test_cli_engine_positional.py::test_two_sibling_directories_both_subdirs_of_root_print_relative_paths_to_cwd
	•	tests/test_cli_engine_positional.py::test_one_dir_outside_root_assumes_root_and_subdir_of_root_prints_relative_path_to_root

⸻

Set 9 [BUDGET-GLOBALITY]: One global file budget across sources (--max-files)

Members
	•	src/prin/core.py (FileBudget)
	•	src/prin/prin.py (single FileBudget shared across sources)

Contract
	•	The budget is enforced globally across all sources during a single invocation. New sources share the same budget.

Triggers
	•	Changing budget semantics or introducing per-source budgets.

Tests
	•	FS: tests/test_max_files_fs.py
	•	Repo: tests/test_max_files_repo.py
	•	Mixed: tests/test_print_mixed_fs_repo.py

⸻

Set 10 [CLI-ALIAS-BEHAVIOR]: Alias expansion ↔ canonical flags

Members
	•	src/prin/cli_common.py (CLI_OPTIONS_ALIASES and parser declarations)
	•	README.md (alias documentation)

Contract
	•	Aliases expand to semantically equivalent canonical flag sets. Keep alias table, parser declarations, and README consistent.

Triggers
	•	Adding/removing an alias; changing the flags an alias expands to.

Tests
	•	tests/test_options_fs.py::test_uu_includes_hidden_and_gitignored, ::test_unrestricted_includes_gitignored

⸻

Set 11 [TEST-COVERAGE-PARITY]: Feature coverage mirrored per source

Members
	•	tests/test_options_fs.py, tests/test_options_repo.py
	•	tests/test_cli_engine_*.py, tests/test_max_files_*.py
	•	tests/test_website_adapter_*.py

Contract
	•	For each implemented feature/flag, maintain parallel coverage for filesystem and GitHub (and website where applicable). Adding a feature implies adding/adapting tests in all relevant suites.

Triggers
	•	Adding a new option/behavior; adding a new adapter.

⸻

Set 12 [WEBSITE-LLMS-TXT-PARSING]: URL list parsing ↔ rendering

Members
	•	src/prin/adapters/website.py (_parse_llms_txt, URL normalization, key naming/dedup)
	•	src/prin/prin.py (website routing and WebsiteSource usage)

Contract
	•	All Markdown links and raw URLs in llms.txt are parsed and fetched; duplicates deduped by key (with suffixing rules as needed); output rendered via the selected formatter.

Triggers
	•	Changing llms.txt interpretation, URL normalization, or keying rules.

Tests
	•	tests/test_website_adapter.py, tests/test_website_adapter_all_urls.py

⸻

Set 13 [CLI-URL-ROUTING]: Token routing to adapters

Members
	•	src/prin/prin.py (routing of input tokens across filesystem, GitHub, website; subpath extraction; global budget use)
	•	src/prin/util.py (is_github_url, is_http_url)
	•	src/prin/adapters/github.py (parse_github_url → owner, repo, subpath)

Contract
	•	Routing logic and helper predicates align:
	•	GitHub tokens are handled by the GitHub adapter; HTTP non-GitHub are handled by the website adapter; everything else is local filesystem.
	•	Repo subpaths come from the GitHub URL parser and are reflected in traversal roots.
	•	Adapters expose clear domain classification used by prin.py.

Triggers
	•	Changing URL detection, subpath rules, or adding new source kinds.

Tests
	•	tests/test_print_repo_positional.py, tests/test_print_mixed_fs_repo.py, tests/test_max_files_*, tests/test_github_adapter.py

⸻

Set 14 [README-EXAMPLES-REALITY]: Documentation ↔ observed behavior

Members
	•	README.md (examples, described defaults/flags)
	•	src/prin/prin.py and adapters (actual behavior)
	•	End-to-end tests (options, mixed-source)

Contract
	•	README claims match implemented behavior and flags; examples are runnable as shown.

Triggers
	•	Any behavior or flag change; example edits.

Tests
	•	Covered indirectly via options and mixed-source tests.

⸻

Set 15 [EXPLICIT-PATH-FORCE-INCLUDE]: Explicit files bypass exclusions

Members
	•	src/prin/core.py (DFS handling of NotADirectoryError → force include; duplicate suppression)
	•	src/prin/adapters/github.py (file-path responses raise NotADirectoryError)
	•	src/prin/adapters/filesystem.py (list_dir filesystem semantics)

Contract
	•	Passing an explicit path prints it even if default exclusions would skip it, uniformly across adapters.

Triggers
	•	Changing explicit-path routing or how adapters signal file vs directory.

Tests
	•	FS: tests/test_cli_engine_positional.py::test_directory_and_explicit_ignored_file_inside
	•	Repo: tests/test_print_repo_positional.py::test_repo_explicit_ignored_file_is_printed

⸻

Set 16 [GITIGNORE-BEHAVIOR]: Current .gitignore semantics

Members
	•	src/prin/filters.py (get_gitignore_exclusions)
	•	src/prin/cli_common.py (Context.__post_init__ composition of exclusions with no_ignore)

Contract
	•	Until real .gitignore parsing is implemented, gitignored files are not excluded by default. Flags (--no-ignore, -u, -uu) remain consistent with current stubbed behavior and README/alias documentation.

Triggers
	•	Implementing real .gitignore parsing; changing the meaning of no_ignore/unrestricted.

Tests
	•	FS: tests/test_options_fs.py::test_unrestricted_includes_gitignored (plus any skipped tests around .gitignore)

⸻

Notes on interplay
	•	Sets 4, 5, and 7 together govern filtering: category defaults, cross-source consistency, and semantic emptiness.
	•	Set 1 and Set 10 keep CLI shape (flags, defaults, aliases) truthful; Set 14 keeps README aligned.
	•	Set 6 (protocol) and Set 13 (routing) ensure adapters are both selectable and interoperable once selected.
	•	Set 9 (budget) is honored across traversal paths, including explicit force-includes (Set 15) and website fetching (Set 12).

⸻

Maintaining PARITIES.md

This section defines how to keep PARITIES.md accurate, terse, and durable as the project evolves. It is format-centric and future-proof: it does not instruct how to maintain any specific set, file, or symbol.

Audience and prerequisites

Before editing the codebase, read: README.md, AGENTS.md, and this PARITIES.md. A change that affects behavior or tests is incomplete unless PARITIES.md is updated in the same pull request.

Document contract (meta)
	•	PARITIES.md is a snapshot, not a history.
	•	Each set uses the same minimal structure (ID • Members • Contract • Triggers • Tests), in that order.
	•	Prefer cross-references by Set ID over repetition.
	•	Keep signal over noise: short, testable, and unambiguous.

Set block template (copy–paste)

Use this exact shape for every set; keep headings and their order.

## Set <ID>: <Short name, 3–6 words>

**Members**
- <repo-path>:<symbol-or-scope>

**Contract**
- <single-sentence rule>

**Triggers**
- <event that requires syncing>

**Tests**
- <suite-or-path>::<test_name>

Style rules
	•	Members: exact paths and symbols only; one item per line; no ranges.
	•	Contract/Triggers: short, actionable sentences; avoid explanatory prose.
	•	Tests: name the smallest checks that prove the contract.
	•	Cross-reference: if another set owns a rule, write “See: Set <ID>”.

Size discipline (line-delta rules)
	1.	Removal → shrink — deleting behavior/files must delete lines here; net lines decrease.
	2.	Modification → steady — scope unchanged ⇒ update in place; net lines unchanged.
	3.	Addition → minimal growth — scope expands ⇒ add only what is necessary:
	•	+1 line per new Members item
	•	≤1 short sentence in Contract/Triggers if semantics changed
	•	A new set rarely exceeds ~10 lines
If exceeded, add a one-line PR note: PARITIES: +<N> lines because <reason>.

Edit recipes
	•	Remove a member or set — delete its Members line; prune now-irrelevant Contract/Triggers/Tests; delete empty sets.
	•	Modify without expanding scope — update paths/symbols and adjust wording without adding bullets; replace sentences instead of appending.
	•	Add a capability or member — append one precise Members line; optionally add one short sentence under Contract/Triggers if semantics changed; reference tests succinctly.
	•	Merge or split sets — only when it reduces duplication or clarifies ownership; preserve IDs or note the mapping in the PR description.

Automation hooks (recommended)
	•	Line-growth gate — fail if total growth >10 lines or any single set grows >6 lines unless PR includes PARITIES: override.
	•	Schema check — each set has exactly the required headings, in order.
	•	ID uniqueness — all Set IDs are unique.
	•	Dangling references — every <repo-path> in Members exists at review time.
	•	Cross-ref integrity — any “See: Set <ID>” resolves.
	•	Test presence — named tests under Tests are discoverable by the test runner.

Review checklist
	•	I read README.md, AGENTS.md, and PARITIES.md before making changes.
	•	For each changed behavior, the matching set(s) are updated in this PR.
	•	I followed the template and style rules exactly.
	•	My changes obey the line-delta rules; if not, I included PARITIES: override with a one-line reason.
	•	I removed stale references and avoided duplication.
	•	Tests named under Tests actually exercise the contract.

Operating principle

Treat PARITIES.md as a switchboard: it names the circuits (Members), the rule that keeps them synchronized (Contract), when to check them (Triggers), and the fuses that trip if something breaks (Tests). Keep labels exact, sentences short, and growth justified.


# Maintaining `PARITIES.md`

This canvas defines **how** to keep `PARITIES.md` accurate, terse, and durable as the project evolves. It is format-centric and future-proof.

---

## Audience and prerequisites

A change that affects behavior or tests is **incomplete** unless `PARITIES.md` is updated in the same pull request.

## Maintaining PARITIES.md: Contract

* `PARITIES.md` is a **snapshot**, not a history or design doc.
* Each set uses the **same minimal structure** (see “Set block template”).
* Prefer **cross-references** by Set ID over repetition.
* Keep **signal over noise**: short, testable, and unambiguous.

## Set block template

Use this exact shape for every set; keep headings and their order.

```
## Set <ID>: <Short name, 3–6 words>

**Members**
- <repo-path>:<symbol-or-scope>
- <repo-path>:<symbol-or-scope>

**Contract**
- <single-sentence rule>
- <single-sentence rule>

**Triggers**
- <event that requires syncing>
- <event that requires syncing>

**Tests**
- <suite-or-path>::<test_name>
- <suite-or-path>::<test_name>
```

**Style rules**

* **Members:** exact paths and symbols only; one item per line; no ranges.
* **Contract/Triggers:** short, actionable sentences; avoid explanatory prose.
* **Tests:** name the smallest checks that prove the contract.
* **Cross-reference:** if another set owns a rule, write “See: Set `<ID>`”.

---

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

   * **+1** line per new **Member** item
   * **≤1** new sentence in **Contract** and/or **Triggers** *if* semantics changed
   * A brand-new set should rarely exceed **\~10 lines** total
     If you exceed these budgets, add a one-line PR note:
     `PARITIES: +<N> lines because <concise reason>`.

---

## Edit recipes (apply one; prefer replacement over addition)

* **Remove a member or set**
  Delete the **Members** line; prune any now-irrelevant **Contract/Triggers/Tests** bullets.
  If a set loses all members, delete the set.

* **Modify without expanding scope**
  Update paths/symbols and adjust wording **without** adding bullets.
  Replace sentences; do not append new ones.

* **Add a capability or new member**
  Append **one** precise **Members** line.
  Add **at most one** new sentence under **Contract/Triggers** if semantics truly changed.
  Reference tests succinctly; prefer naming existing checks.

* **Merge or split sets**
  Only when it **reduces duplication** or clarifies ownership.
  Preserve Set IDs or record the mapping in the PR description.

---

## Automation hooks (recommended, tool-agnostic)

Codify the canvas with lightweight checks. Names below are illustrative; implement with your CI/pre-commit of choice.

* **Line-growth gate**
  Fail if `PARITIES.md` grows by more than **10 lines** overall, or any single set grows by more than **6 lines**, unless the PR contains `PARITIES: override`.

* **Schema check**
  Ensure each set has exactly these headings, in order: `Members`, `Contract`, `Triggers`, `Tests`.

* **ID uniqueness**
  All Set IDs are unique; no duplicates or missing IDs.

* **Dangling references**
  Every `<repo-path>` listed under **Members** exists in the tree at review time.

* **Cross-ref integrity**
  Any “See: Set `<ID>`” points to a present ID.

* **Test presence**
  Named tests under **Tests** are discoverable by the test runner.

---

## Review checklist (for authors and reviewers)

* [ ] I read `README.md`, `AGENTS.md`, and `PARITIES.md` before making changes.
* [ ] For each changed behavior, the matching set(s) are updated in this PR.
* [ ] I followed the **Set block template** and **Style rules** exactly.
* [ ] My changes obey the **line-delta rules**; if not, I included `PARITIES: override` with a one-line reason.
* [ ] I removed all stale references and avoided duplicating content across sets.
* [ ] Tests named under **Tests** actually exercise the contract.

---

## Anti-patterns (avoid)

* Narrative explanations, examples that restate code, or historical context.
* Catch-all sets that mix unrelated concerns.
* “Future work” notes; put those in issues, not here.
* Duplicating rules across sets instead of cross-referencing.
* Vague members (for example, whole directories without symbol scoping).

---

## Operating principle

Treat `PARITIES.md` as a **switchboard**: it names the circuits (Members), the rule that keeps them synchronized (Contract), when to check them (Triggers), and the fuses that trip if something breaks (Tests). Keep labels exact, sentences short, and growth justified.
