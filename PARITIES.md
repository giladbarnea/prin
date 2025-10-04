---
audience: AI agents
description: Records the dependencies between elements in the codebase
updated: After code changes
authority rank: Eventual source of truth. Before any changes, this file is the canonical reference. When the code changes, the code is authoritative until this file is updated. After updating, this file locks a snapshot of the codebase and becomes the authoritative reference again.
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

1. Each parity set lists an ID, Members (with precise locations/symbols), a Contract (what must stay in sync), and Triggers (what changes require syncing).
2. Always use backticks when referring to a `file.ext`, `dir/`, `Symbol`, `function`, etc.

### Always finish off your task by updating PARITIES.md

**You are responsible for updating this document after you've completed your task, to make it reflect the new state of the project.**

See "Maintaining `PARITIES.md`" section at the bottom of this file for detailed instructions on how to do this.

---

# Parity Sets

## Set 1 [FLAGS-CONTEXT-DEFAULTS-DOCS]: CLI flags ↔ Context fields ↔ Defaults ↔ Documentation & Fixtures

#### Members
- `README.md`: CLI Options; Output Control; Sane Defaults for LLM Input
- `src/prin/cli_common.py`: `parse_common_args(...)` (all flags), `_expand_cli_aliases`; `Context` dataclass (all flag-derived fields, incl. `pattern`, `paths`)
- `src/prin/defaults.py`: CLI-related `DEFAULT_*` (choices/booleans/patterns; includes category sets such as exclusions, lock/dependency/docs/config/binary/test/script/stylesheets, hidden)
- `src/prin/core.py`: `DepthFirstPrinter._set_from_context` (printing-related fields)
- `src/prin/adapters/*`: `SourceAdapter.configure(Context)` consumes flag-derived config
- `src/prin/adapters/filesystem.py`: depth handling in `FileSystemSource._walk_dfs`; category/ignore handling in `should_print(...)`
- `tests/conftest.py`: `fs_root`/`VFS` fixtures with categorized file dicts (e.g., `dependency_spec_files`, `build_dependency_files`, `config_files`)
- `tests/test_depth_controls.py`: depth controls behavior
- `tests/test_dependency_flag.py`: `--no-dependencies` behavior
- `tests/test_config_flag.py`: `--no-config` behavior

#### Contract
- One-to-one mapping: each CLI flag maps to exactly one `Context` field and one default in `defaults.py`; `README.md` documents only implemented flags with current semantics.
- Category toggles (e.g., hidden/lock/docs/config/binary/tests/dependencies/scripts/stylesheets) are backed by explicit `DEFAULT_*` entries in `defaults.py` and enforced by adapters via `configure(Context)` and `should_print(...)`. See: Set 5 for filter mechanics.
- Depth controls (`--max-depth`, `--min-depth`, `--exact-depth`) are consumed by the filesystem adapter; depth is counted from the search root (depth 1 = direct children).
- Aliases expand only to canonical flags defined here. See: Set 10.

#### Triggers
- Adding/removing/renaming a flag; changing a default; changing flag semantics.
- Adding/removing a category or changing its inclusion/exclusion semantics.


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

 

## Set 3 [ONLY-HEADERS-ENFORCEMENT-WITH-HEADERFORMATTER]: `--only-headers` flag ↔ `HeaderFormatter` behavior
#### Members
- `src/prin/cli_common.py`: `Context.only_headers` / CLI: `-l/--only-headers`.
- `src/prin/core.py`: `DepthFirstPrinter` forcing `HeaderFormatter` when `only_headers=True`.
- `src/prin/formatters.py`: `HeaderFormatter`.

#### Contract
- When `only_headers` is true, body content must not be printed, regardless of any explicitly selected formatter.

#### Triggers
- Changing `only_headers` semantics or formatter enforcement.


## Set 5 [FILTERS-CONSISTENCY-ACROSS-SOURCES]: Path exclusion and extension semantics ↔ Pattern classifier
#### Members
- `src/prin/adapters/*`: `should_print(entry)` implementations.
- `src/prin/filters.py`: `is_excluded`, `extension_match`, `get_gitignore_exclusions`.
- `src/prin/path_classifier.py`: `classify_pattern`, `is_glob`, `is_extension`, `is_regex`.
- `src/prin/cli_common.py`: `_normalize_extension_to_glob`.

#### Contract
- Inclusion/exclusion and extension matching must behave identically regardless of source type; adapters may delegate to `filters.*` to keep behavior consistent.
- The classifier distinguishes two kinds of patterns: `regex` (matched by `re.search`) and `glob` (matched via `fnmatch`).
- Explicit extensions are normalized by `_normalize_extension_to_glob`; changes propagate to `filters.is_excluded` and `filters.extension_match`.
- Changes to classifier rules must be reflected in `filters.is_excluded` and `filters.extension_match`.
- Category flag semantics and defaults originate in Set 1; filters must implement them faithfully. See: Set 1.

#### Triggers
- Changing matching rules, glob/regex detection, or text-token semantics. Changing extension normalization rules.


## Set 6 [SOURCE-ADAPTER-INTERFACE]: Protocol and uniform adapter semantics

#### Members
- Protocol: `src/prin/core.py`: `SourceAdapter` with `configure`, `walk_pattern`, `should_print`, `read_body_text`, `resolve`, `exists` (and `Entry`/`NodeKind` shapes).
- Implementations: `src/prin/adapters/filesystem.py`, `src/prin/adapters/github.py`, `src/prin/adapters/website.py`.

#### Contract
- Adapters implement a uniform interface: `configure(Context)`, `walk_pattern`, `should_print`, `read_body_text`, `resolve`, `exists`; shared `Entry`/`NodeKind` shapes.
- `configure(Context)` must consume the flag-derived fields defined in Set 1.
- `resolve`/`exists` keep lexical resolution rules; `is_empty` adheres to Set 7.

#### Triggers
- Changing the protocol, method contracts, or `Entry`/`NodeKind` shapes; adding a new adapter.

 

## Set 7 [SEMANTIC-EMPTINESS-ADAPTERS]: Shared definition across adapters

#### Members
- `src/prin/core.py`: `is_blob_semantically_empty`, `_is_text_semantically_empty`.
- Adapter usage: filesystem and GitHub `is_empty` delegate to shared function; Website returns False at routing time and defers to shared logic post-fetch when applicable.

#### Contract
- A single definition of “semantically empty” governs all adapters; the `--include-empty` CLI flag toggles printing of otherwise empty blobs (flag mapping: Set 1).

#### Triggers
- Changing emptiness heuristics or language coverage.

 

## Set 8 [BINARY-FILE-DETECTION]: Automatic binary detection for filesystem

#### Members
- `src/prin/binary_detection.py`: `is_binary_file`, `_detect_file_fastsig`, `_is_binary_file_fallback`.
- `src/prin/adapters/filesystem.py`: `read_body_text` uses `is_binary_file`.
- `src/prin/core.py`: `_is_text_bytes`, `_decode_text` (legacy byte-based detection for non-filesystem adapters).
- `src/prin/adapters/github.py`, `src/prin/adapters/website.py`: use `_is_text_bytes` for blob-based detection.

#### Contract
- Filesystem adapter uses path-based binary detection (`binary_detection.is_binary_file`) combining signature-based (fastsig) and content-based (fallback) approaches.
- GitHub and Website adapters use legacy byte-based detection (`core._is_text_bytes`) since they operate on already-downloaded blobs.
- Binary files return `(None, True)` from `read_body_text`; text files return `(decoded_text, False)`.

#### Triggers
- Adding/modifying binary format signatures; changing content analysis heuristics; adapter refactoring.

 

## Set 9 [BUDGET-GLOBALITY]: One global file budget across sources (`--max-files`)
#### Members
- `src/prin/core.py`: `FileBudget`.
- `src/prin/prin.py`: single `FileBudget` instance shared across all sources.
- `src/prin/cli_common.py`: `Context.max_files`.

#### Contract
- The budget is enforced globally across all sources during a single invocation. New sources must share the same budget.

#### Triggers
- Changing budget semantics or introducing per-source budgets.

 

## Set 10 [CLI-ALIAS-BEHAVIOR-README]: Alias expansion ↔ canonical flags
#### Members
- `src/prin/cli_common.py`: `CLI_OPTIONS_ALIASES` (for example, `-uu` → `--hidden` `--no-ignore`) and parser declarations (for example, `-u`/`--unrestricted`, `-uuu`/`--no-exclude`).
- `README.md`: alias documentation.

#### Contract
- Aliases must expand to semantically equivalent canonical flag sets. Keep alias table, parser declarations, and README consistent.

#### Contract
- Aliases must expand to semantically equivalent canonical flag sets defined in Set 1; keep alias table, parser declarations, and README consistent.
 

## Set 12 [WEBSITE-LLMS-TXT-PARSING]: URL list parsing ↔ rendering
#### Members
- `src/prin/adapters/website.py`: `_parse_llms_txt`, URL normalization, key naming/deduplication.
- `src/prin/prin.py`: website routing and `WebsiteSource` usage.

#### Contract
- All Markdown links and raw URLs listed by the website’s URL manifest are parsed and fetched; duplicates are deduplicated by key (with suffixing rules as needed); output rendered via the selected formatter.

#### Triggers
- Changing the website URL-manifest interpretation, URL normalization, or keying rules.

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


## Set 15 [EXPLICIT-PATH-FORCE-INCLUDE]: Explicit files bypass exclusions
#### Members
- `src/prin/adapters/*`: `walk(token)` sets `Entry.explicit=True` for explicit file roots; adapters’ `should_print` honors it.
- `src/prin/core.py`: duplicate suppression by absolute path key remains in the printer.

#### Contract
- Passing an explicit path must print it even if default exclusions would skip it. This applies uniformly across adapters via `Entry.explicit=True` and `should_print` implementation.

#### Triggers
- Changing explicit-path routing or how adapters signal file vs directory.

## Set 16 [GITIGNORE-BEHAVIOR]: `.gitignore` semantics

#### Members
- `src/prin/adapters/filesystem.py`: `FileSystemSource.configure` initializes `GitIgnoreEngine`; `should_print` consults engine first.
- `src/prin/filters.py`: `GitIgnoreEngine` implementation; `get_gitignore_exclusions` shim.
- `src/prin/cli_common.py`: `Context.__post_init__` keeps `no_ignore` field; help text.
- `SPEC.md`: CLI option notes for `--no-ignore`.
- `README.md`: Sane defaults list includes VCS ignore paths.

#### Contract
- By default, filesystem traversal respects `.gitignore`, `.git/info/exclude`, global `~/.config/git/ignore`, plus `.ignore` and `.fdignore`. The last matching rule wins, and negations are honored. `--no-ignore` disables this engine. Explicit file roots still force-include.

#### Triggers
- Changing ignore engine semantics or sources; altering `--no-ignore` meaning.

## Set 17 [PATTERN-THEN-PATHS]: Pattern-then-paths interface

#### Members
- `src/prin/cli_common.py`: positional args parsing (pattern, paths*).
- `src/prin/core.py`: `DepthFirstPrinter.run_pattern` method.
- `src/prin/prin.py`: main dispatcher logic.
- `src/prin/adapters/*`: `walk_pattern(pattern, root)` implementations.
- `README.md`: what-then-where usage examples.

#### Contract
- First arg is pattern (glob/regex), followed by zero or more paths (files or directories). With no paths, cwd is used.
- Pattern matching happens against full relative paths from each provided path root.
- Empty pattern means list all files in the path.
- Paths are displayed relative to each root token's shape (absolute vs relative vs ./ or ../ prefix).

#### Triggers
- Changing pattern matching semantics; modifying path display logic.

 
## Set 18 [FS-DISPLAY-WHAT-THEN-WHERE]: Filesystem display semantics

#### Members
- `SPEC.md`: What–Then–Where: Filesystem Path Display Spec
- `src/prin/adapters/filesystem.py`: `walk_pattern`
- `src/prin/adapters/filesystem.py`: `_display_rel`
- `README.md`: “Basic Usage”/“Matching” examples showing displayed path shapes

#### Contract
- Each root token’s shape solely dictates displayed path form: None/child → bare relative; `./…` preserved; `../…` preserved; absolute → absolute paths.

#### Triggers
- Any change to filesystem display base/prefix rules or to README/SPEC examples reflecting them.

---

### Notes on interplay
- **Sets 1, 5, 7, and 8** together govern filtering and content classification: flag/context/defaults & docs (Set 1), classifier and filter mechanics (Set 5), semantic-emptiness toggling (Set 7), and binary file detection (Set 8).
- **Set 1 and Set 10** together ensure the CLI shape (flags, defaults, aliases) stays truthful; formatter/output examples live in their domain sets (Set 2, Set 17/18).
- **Set 6 (protocol)** and **Set 13 (routing)** ensure adapters are both selectable and interoperable once selected.
- **Set 9 (budget)** must be honored by all traversal code paths, including explicit force-includes (Set 15) and website fetching (Set 12).


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
```

**Style rules**
- **Members:** exact paths and symbols only; one item per line; no ranges.
- **Contract/Triggers:** short, actionable sentences; avoid explanatory prose.
 
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
 Treat `PARITIES.md` as a **switchboard**: it names the circuits (Members), the rule that keeps them synchronized (Contract), and when to check them (Triggers). Keep labels exact, sentences short, and growth justified.

## Work Against and Update PARITIES.md

1. **`PARITIES.md` is the source of truth** for what’s going on in the project. You are responsible for keeping it accurate after you have completed your task.
2. Initially, before making code changes: **map your plan against `PARITIES.md`.** Identify which elements will be affected by your changes and have a general idea of what you’ll need to update when you’re done.
* An ‘element’ is a piece of information ranging from a reference to a single symbol to a Member line, or, rarely, an entire set.
3. After everything is working: **return to `PARITIES.md` and surgically update** any parts that are no longer accurate due to your changes. **Add any new items introduced by your task**, and **follow the instructions in [Maintaining PARITIES.md](PARITIES.md)**.

