# Comprehensive Analysis: GitHub and Website Adapter Alignment Plan

**Date:** 2025-10-05  
**Status:** Analysis Complete - Awaiting Clarification Before Implementation  
**Author:** Claude (Background Agent)

---

## Executive Summary

The filesystem adapter has reached maturity with comprehensive feature support. The GitHub and website adapters are significantly outdated, missing:
- Depth controls (GitHub only)
- Category-based filtering integration
- Sophisticated binary detection
- Consistent display path semantics
- Full alignment with the `SourceAdapter` protocol

This document analyzes the gaps, identifies ambiguities requiring clarification, and proposes an implementation plan that maximizes code reuse while maintaining adapter-specific concerns.

---

## 1. CURRENT STATE ASSESSMENT

### Filesystem Adapter (FileSystemSource) - ✅ MATURE

The filesystem adapter is feature-complete with:

- ✅ Full `SourceAdapter` protocol implementation
- ✅ Depth controls (`--max-depth`, `--min-depth`, `--exact-depth`)
- ✅ GitIgnore engine integration (respects `.gitignore`, `.git/info/exclude`, global config, `.ignore`, `.fdignore`)
- ✅ Category-based filtering (tests, lock files, dependencies, docs, config, scripts, stylesheets, binary, hidden, empty)
- ✅ Extension filtering (`-e` flag)
- ✅ Custom exclusions (`-E` flag) 
- ✅ Display path semantics (relative/absolute, `./`, `../` prefix handling per SPEC.md)
- ✅ Pattern matching (glob vs regex classification)
- ✅ Binary detection (signature + content-based fallback)
- ✅ Semantic emptiness (Python files with only imports/`__all__`)
- ✅ Explicit file force-include (`Entry.explicit=True`)
- ✅ Budget enforcement

### GitHub Adapter (GitHubRepoSource) - ⚠️ PARTIALLY OUTDATED

**What exists and works:**
- ✅ Basic URL parsing (owner/repo/ref/subpath extraction)
- ✅ GitHub API integration with rate-limit handling
- ✅ Disk caching for responses
- ✅ `configure()`, `walk_pattern()`, `should_print()`, `read_body_text()` methods
- ✅ Basic pattern matching (glob/regex)
- ✅ Basic exclusion/extension filtering
- ✅ Semantic emptiness checks

**What's missing:**
- ❌ Depth controls (no `max_depth`, `min_depth`, `exact_depth` handling)
- ❌ Category filtering not connected (tests, lock, docs, config, scripts, stylesheets)
- ❌ Binary detection (uses simple `_is_text_bytes` check, not the sophisticated `binary_detection.py`)
- ❌ No integration with defaults categories
- ❌ Hidden file filtering not implemented
- ❌ Display path semantics unclear (no `./` or `../` prefix handling)

### Website Adapter (WebsiteSource) - ⚠️ PARTIALLY OUTDATED

**What exists and works:**
- ✅ `llms.txt` manifest parsing
- ✅ URL list extraction (Markdown links + raw URLs)
- ✅ Key-based deduplication
- ✅ `configure()`, `walk_pattern()`, `should_print()`, `read_body_text()` methods
- ✅ Basic pattern matching on keys
- ✅ Basic exclusion/extension filtering
- ✅ Disk caching

**What's missing:**
- ❌ Depth controls (N/A for websites - flat structure)
- ❌ Category filtering not connected
- ❌ Binary detection (uses simple `_is_text_bytes`)
- ❌ Display path semantics unclear
- ❌ Pattern matching is on keys, not full URLs (is this correct?)

---

## 2. FEATURE GAPS TO CLOSE

### Priority 1: Core Protocol Alignment

#### 1.1 Depth Controls

**GitHub:** Needs `max_depth`, `min_depth`, `exact_depth` in `configure()` and `_walk_dfs()`

**Website:** N/A (URLs are flat), but should gracefully ignore these option​s

❗️ **User comment**: CORRECTION: Websites often have multiple pages organized in a tree structure. For example, the base URL `https://ai.pydantic.dev/` has many sub-URLs, including `ai.pydantic.dev/agents/index.html`, `ai.pydantic.dev/common-tools/index.html`, `ai.pydantic.dev/models/anthropic/index.html`, etc.  Given a website url and given that the base url has an accessible `/llms.txt`, `prin` should use the information it contains to map out the site tree and treat it as a tree for all intents and purposes.

**Question:** For GitHub, when user specifies `github.com/owner/repo/src`:

- Is `src/` considered depth 0 (root) or depth 1?
- Should `--max-depth 1` show only files directly in `src/`, or one level deeper?

❗️**Answer:**
Depth handling should be consistent across adapters and matches how `fd` does it. Depth starts at 1 at the search root: items directly inside the root are depth 1.

Examples:
- `prin --exact-depth=1 . mydir` prints only the files directly in `mydir/`. (If you omit `mydir`, it prints files directly in `$PWD`.)
- `prin --max-depth=1 . mydir` also prints **only** the files directly in `mydir/`.
- `prin --min-depth=1 . mydir` prints files in `mydir/` and deeper. Just to connect the dots for you, this is the default depth control, so `--min-depth=1` is redundant. 
- `prin --exact-depth=1 . mydir/subdir` prints only the files directly in `mydir/subdir/`.
- `prin --exact-depth=2 . mydir` prints only the files exactly one level below `mydir/` (e.g., files in `mydir/subdir/` and other immediate child directories of `mydir/`).
- `prin --min-depth=2 . mydir` prints files one level below `mydir/` and deeper (e.g., files in `mydir/subdir/` and beyond).

This existing depth control also behaves like this with the filesystem adapter. No changes to depth logic are needed. Only to integrate the other adaptors.

Direct answers about running `prin` with `github.com/owner/repo/src`:
- The specified directory is depth 1. Therefore, in this case, `src/` is depth 1. If `github.com/owner/repo/src/foo` was specified, then `src/foo/` was depth 1. If `github.com/owner/repo` was specified, then `/` — the root of the repo — was depth 1.
- `prin . github.com/owner/repo/src --max-depth 1` prints only the files directly in `src/`, not deeper.

Mental model for depth control in The GitHub adapter: should behave as if you cloned the repo (`git clone owner/repo`), cd’d into its root (`cd repo`), and ran prin with `github.com/owner/repo` stripped from the path: `prin . src --max-depth 1`, `prin . . --min-depth 3`, etc. Note that, unlike depth control, the displayed paths in the GitHub Adapter don’t behave like file system. More on this below.


#### 1.2 Category Filtering Integration

Both adapters have `configure()` but don't consume category flags from `Context`:
- `no_docs`, `no_config`, `no_scripts`, `no_stylesheets`
- `include_tests`, `include_lock`, `include_dependencies`, `include_hidden`

**Question:** For GitHub, do we filter by:
- File extension/name patterns only? 
- Directory names (e.g., `tests/`, `scripts/`) as well?

❗️**Answer**: both. For GitHub, apply the same category filtering as in the file system. The only quirk is that remote repositories, by definition, don’t have .gitignore'd files. Therefore, honoring .gitignore on GitHub is nonsensical and should be hard-coded off.

**Question:** For Website, should we:
- Apply extension-based filters only?
- Skip directory-based rules entirely?
- Parse URL paths for directory patterns?

❗️**Answer**:
**The website adapter ignores all default category filters and user provided filter patterns unless `--filter-websites` is explicitly provided.**
Note that unlike a file system or a GitHub repo, where we are given a predetermined file tree, the website adapter builds the tree ahead of time from the links in llms.txt, selecting only URLs with textual content. As a result, in the vast majority of cases the user ends up with a tree of plain, Markdown-converted pages. And even if a subtree happens to be `example.com/node_modules/`, it’s more likely documentation or articles the user is interested in, so excluding it by default would be surprising.
For this reason, applying filters on websites is opt-in and explicit with `--filter-websites`. (`--filter-websites` was not discussed until now)


#### 1.3 Binary Detection Upgrade

- GitHub: Should use shared `binary_detection.is_binary_file()` after fetching
- Website: Same - detect after download

**Challenge:** GitHub API provides `encoding` field - should we trust it or verify ourselves?
❗️**Answer**: Trust it.

**Question:** Should we:
- Use filesystem's `binary_detection.is_binary_file()` on fetched bytes?
- Trust remote hints (GitHub `encoding`, website `Content-Type`)?
- Skip binary detection for websites (assume all text)?

❗️**Answer:** 
For websites: Skip binary detection for websites.
For GitHub: we should use filesystem's `binary_detection.is_binary_file()` on fetched bytes, only if they “survive” the first layer of checking GitHub `encoding` (which we trust).
Currently, binary detection is performed by first trying a fast signature-based check, then a generic and thorough content (bytes) check (termed ‘fallback’ in `binary_detection.py`.) GitHub should check `encoding` before the signature-based check. This is a nice optimization because it will be done **before** the file is downloaded or read. Only if `encoding` passes, should `prin` download the bytes and perform a fast sig -> fallback logic. In general, if there's a way to quickly get file metadata for cheap pre-filtering, we should do so.


### Priority 2: Display Path Semantics

#### 2.1 GitHub Display Paths

Currently returns relative paths from search root.

**Ambiguity:** What should display paths look like for GitHub?
- `owner/repo/path/to/file.py`?
- `path/to/file.py` (relative to subpath)?
- Just the file path relative to search root?

**Example scenarios:**
```bash
# What should be displayed?
prin "*.py" github.com/torvalds/linux/drivers

# Option A: drivers/net/ethernet/...
# Option B: net/ethernet/... (relative to drivers/)
# Option C: github.com/torvalds/linux/drivers/net/ethernet/...
```

❗️**Answer:** Neither. 
For both website and GitHub, we should display the full (“absolute”) path, but split it across two XML attributes: `path` and `source`. `path` represents the absolute path from the root. `source` represents the URL. 

For `prin github.com/torvalds/linux`:

```xml
<path="MAINTAINERS" source="github.com/torvalds/linux">
...
</path="MAINTAINERS" source="github.com/torvalds/linux">
<path="fs/aio.c" source="github.com/torvalds/linux">
...
</path="fs/aio.c" source="github.com/torvalds/linux">
```

**the display path would be the same even if the argument pointed at the a child directory:** for `prin "*.c" github.com/torvalds/linux/fs`: 

```xml
# Display paths are the same as prin github.com/torvalds/linux
<path="fs/aio.c" source="github.com/torvalds/linux">
...
</path="fs/aio.c" source="github.com/torvalds/linux">
```

Specifying a child path in the CLI (rather than the root)  only narrows the search scope; it does not affect the display path.
Compared to the file system behavior, only the display path is different. Matching and traversal semantics are completely the same.
Examples:

Example 1:
`prin https://github.com/torvalds/linux/tree/master/kernel/power`

```xml
<path="kernel/power/autosleep.c" source="github.com/torvalds/linux">
...
</path="kernel/power/autosleep.c" source="github.com/torvalds/linux">
```

Example 2: the pattern matches a directory

`prin power https://github.com/torvalds/linux`

```xml
<path="kernel/power/autosleep.c" source="github.com/torvalds/linux">
...
</path="kernel/power/autosleep.c" source="github.com/torvalds/linux">
```

Example 3:
`prin "io" https://github.com/torvalds/linux`

```xml
<path="io_uring/advise.c" source="github.com/torvalds/linux">
...
</path="io_uring/advise.c" source="github.com/torvalds/linux">
<path="drivers/iommu/apple-dart.c" source="github.com/torvalds/linux">
...
</path="drivers/iommu/apple-dart.c" source="github.com/torvalds/linux">
```

Again, besides the display path with XML attributes, this is 100% consistent with how the file system adapter traverses and matches entries.

#### 2.2 Website Display Paths

Currently uses deduped keys (basenames, or `domain.name`)

**Ambiguity:** Should these be:
- Keys as-is (`api-reference`, `guides.2`)?
- Full URLs?
- Simplified URLs (strip protocol/domain)?

❗️**Answer:** Same principle as GitHub. For `prin https://ai.pydantic.dev/models/`:

```xml
<path="models" source="ai.pydantic.dev">
...
</path="models" source="ai.pydantic.dev">
<path="models/anthropic" source="ai.pydantic.dev">
...
</path="models/anthropic" source="ai.pydantic.dev">
<path="models/openai" source="ai.pydantic.dev">
...
</path="models/openai" source="ai.pydantic.dev">
```

For `prin ai.pydantic.dev`:

```xml
<path="/" source="ai.pydantic.dev">
...
</path="/" source="ai.pydantic.dev">
<path="a2a" source="ai.pydantic.dev">
...
</path="a2a" source="ai.pydantic.dev">
<path="models/anthropic" source="ai.pydantic.dev">
...
</path="models/anthropic" source="ai.pydantic.dev">
```

### Priority 3: Pattern Matching Consistency

#### 3.1 GitHub Subpath + Pattern

AGENTS.md says: "Subpaths may include literal segments and a trailing pattern segment"

**Question:** How do we distinguish between:
- `prin "*.py" github.com/owner/repo/src` (src is literal path, `*.py` is pattern)
- `prin "" github.com/owner/repo/src/*.py` (`src/*.py` is subpath with pattern?)

**Current implementation:** Pattern is separate from URL, applied to traversal results

❗️**Answer:** This phrase in AGENTS.md is OUTDATED and INCORRECT. Mixing patterns and paths is invalid globally, for all adapters. Moreover, as stated in an earlier answer, filters are ignored for websites until `--filter-websites` is specified.

This means that all of the following are invalid:
<invalid examples mixing path and pattern>

- `prin "" github.com/owner/repo/src/*.py`
- `prin "" ./my/local/dir/*.c`
- `prin "" www.example.com/*.rs`
</invalid examples mixing path and pattern>

This is also invalid, because it does not have `--filter-websites`:

- `prin "*.rs" www.example.com/`

Instead, pattern and path should be specified separately and clearly:
<valid examples separating path and pattern>

- `prin "*.py" github.com/owner/repo/src/`
- `prin "*.c" ./my/local/dir/`

</valid examples separating path and pattern>

#### 3.2 Website Pattern Matching

Currently matches against keys only.

**Should it also match:** Full URLs? URL paths? Both?

**Example:** If `llms.txt` lists `https://docs.example.com/api/auth`, should:

- `prin "api" example.com` match (key might be `auth` or `api`)?
- `prin "docs.example" example.com` match (full URL)?  // ← nonsensical

❗️**Answer:** consistent with earlier answers, filters are ignored for websites until `--filter-websites` is specified.

##### Website Pattern Matching WITH `--filter-websites`

Should behave like GitHub pattern matching.

If `llms.txt` lists `https://www.example.com/api/auth`:  (I've replaced `docs.` with `www.` for simplicity)

- `prin "api" example.com` would match `https://www.example.com/api` and all of `/api` 's child pages: `https://www.example.com/api/auth`, `https://www.example.com/auth/foo/bar`, etc.
- This is consistent with File system adapter: given a local file tree `./example-com/api/auth/foo/bar`, with a `file1.txt`  in every level, running `prin api example-com` matches everything in `example-com/api/` and below: 
  `example-com/api/file1.txt`, `example-com/api/auth/file1.txt`, `example-com/api/auth/foo/file1.txt`, `example-com/api/auth/foo/bar/file1.txt`.
  `example-com/file1.txt` does not match, because there's no `api` in that path.
- The above is equally true for GitHub repos. `prin "api" github.com/owner/repo` would match a `api` dir if it exists, including its children. 
- `prin "docs.example" example.com` doesn't work. Both `docs` and `docs.example` belong in the “where” argument. This is because base urls and subdomains are the “where”. Patterns (“what”) filter components belonging to the base URL.
- This is consistent with with the other two adapters: with a local file tree `./www-example-com/api/auth`, running `prin "docs-example" ./www-example-com` would match nothing (unless a child path matches this string). Even the simpler case is nonsensical and would match nothing: with a local file tree `./example-com/api/auth`, running `prin "example" ./example-com` would match nothing. It should always be `prin WHAT WHERE`.

### Priority 4: Edge Cases & Special Behaviors

#### 4.1 GitIgnore Semantics for GitHub

`prin.py` currently forces `no_ignore=True` for GitHub.

**Rationale:** GitHub repos don't have local `.gitignore` to read.

**Question:** Should we:
- Fetch `.gitignore` from repo and apply it?
- Keep it disabled (current behavior)?

**My assessment:** Keep `no_ignore=True` - it's a remote source, no local VCS context.

❗️**Answer:** Keep it disabled (current behavior). 

#### 4.2 Explicit File Force-Include

- Filesystem: Works via `Entry.explicit=True` when file is passed directly
- GitHub: Need to detect when URL points to a specific file (currently handled via `NotADirectoryError`)
- Website: URLs in manifest are all "explicit" in a sense

**Question:** Should direct file URLs bypass all filters?
```bash
prin github.com/owner/repo/blob/main/.env  # Force-print despite hidden?
prin https://docs.example.com/secret.html  # Force-print?
```

❗️**Answer:** `Entry.explicit=True` should be supported by all adapters. GitHub should force-print despite filters, and Website should print despite `--filter-websites`.

```bash
prin github.com/owner/repo/blob/main/.env  # Force-print despite hidden
prin --exclude html https://docs.example.com/index.html --filter-websites  # Force-print despite ‘html’ exclusion
```



#### 4.3 Empty Files

- Filesystem: Semantic emptiness works (Python-specific)
- GitHub/Website: Same logic exists but should it apply?

**Edge case:** What if a repo has `__init__.py` files that are just `"""Module."""\nimport x\n__all__ = []`? Exclude by default?

❗️**Answer:** Semantic emptiness has actually been REMOVED from the project. There is no such thing any more.

#### 4.4 Budget Exhaustion

- Filesystem: Stops traversal when budget spent
- GitHub: Should stop API calls mid-directory listing?
- Website: Should stop downloading from `llms.txt` list?

**Current behavior:** Budget is global, checked per file print.

❗️**Answer:** Listing operations don't count against budget, regardless of adapter. Only printing files consumes the budget. The user-specified budget number is the maximum number of files (or pages, in the case of websites) printed.

---

## 3. IMPLEMENTATION CHALLENGES

### Challenge 1: Depth Tracking in GitHub

**Problem:** GitHub API's `/contents` endpoint returns flat lists per directory. To track depth:

**Options:**
- A) Track depth in `_walk_dfs` stack (like filesystem)
- B) Count path segments from search root

**Complexity:** Subpaths complicate this. If user says `github.com/owner/repo/src`, is `src/` depth 0 or 1?

❗️**Answer:** Option A. Like filesystem. See  2. FEATURE GAPS TO CLOSE >  Priority 1: Core Protocol Alignment >  1.1 Depth Controls for detailed depth control spec in this case.

### Challenge 2: Binary Detection for Remote Files

**Problem:** Fetching file content to detect binary status is expensive.

**Comparison:**
- **Filesystem:** Can use file signatures, quick checks
- **GitHub/Website:** Must download entire file first

**Optimization considerations:**
- Check Content-Type headers first?
- Trust GitHub's API `encoding` field?
- Implement a header-only check with fallback?

❗️**Answer:** Filesystem: keep as-is. GitHub/Website: do not download the file. Rely on metadata: Content-Type, GitHub's API `encoding`, and file extension.

### Challenge 3: Category Filters Without Filesystem Context

**Problem:** Categories like "tests" and "scripts" are defined by:
- Directory names (`tests/`, `scripts/`)
- File patterns (`test_*.py`, `*.test.js`)

**For remote sources:**

- GitHub: Can match paths against patterns
- Website: Keys might not preserve directory structure

❗️**Answer:** GitHub:  indeed should match paths against patterns. Website: as specified above, default category filters don't apply to websites. Only NON-category patterns and exclusions are applied to websites if and only if `--filter-websites` is also specified.

E.g., given that these two pages exist (and for the sake of example, only they exist):

1. `www.ai.pydantic.dev/models/anthropic`
2. `www.ai.pydantic.dev/models/openai`

Running `prin --filter-websites --exclude=openai ai.pydantic.dev` would skip the `/openai` branch and only match the `/anthropic` branch.



### Challenge 4: Pattern-as-File Behavior

**Filesystem example:**
```bash
prin README.md src/  # Prints README.md + any README.md in src/
```

**GitHub challenge:** How to detect if "pattern" is a file URL?
```bash
prin github.com/owner/repo/blob/main/README.md src/
# Is first arg a pattern or a GitHub URL?
```

**Current routing:** GitHub URLs are detected in `paths`, not `pattern`.

**Implication:** This feature doesn't apply to remote sources (correct?).

### Challenge 5: Display Base Selection

**Filesystem:** Complex rules based on token shape (`.`, `./`, `../`, absolute)  
**GitHub:** No CWD concept - everything relative to repo root  
**Website:** No directory concept - flat URL list

**Question:** Should we:
1. Keep filesystem display rules, ignore for remote sources?
2. Implement GitHub-specific display rules?
3. Document that display semantics only apply to filesystem?

---

## 4. QUESTIONS FOR CLARIFICATION

### Critical Questions (Must Resolve Before Coding)

1. **GitHub Display Paths:** What should be the display format?
   - Relative to subpath root? Repo root? Full GitHub path?
   - Should we show `owner/repo` prefix, or just the file path?

2. **Depth for GitHub:** When user specifies `github.com/owner/repo/src`:
   - Is `src/` considered depth 0 (root) or depth 1?
   - Should `--max-depth 1` show only files directly in `src/`, or one level deeper?

3. **Category Filters Scope:** Should directory-based category filters (like `tests/`) work for:
   - GitHub: Yes, match against repo paths?
   - Website: No, only extension-based?

4. **Binary Detection Strategy:** Should we:
   - Use filesystem's `binary_detection.is_binary_file()` on fetched bytes?
   - Trust remote hints (GitHub `encoding`, website `Content-Type`)?
   - Skip binary detection for websites (all text)?

5. **GitIgnore for GitHub:** Should we:
   - Fetch and apply `.gitignore` from the repo?
   - Keep it disabled (current: `no_ignore=True` forced)?

### Nice-to-Clarify Questions

6. **Pattern Matching on Websites:** Match against keys, URLs, or both?

7. **Explicit File URLs:** Should these bypass filters?
   ```bash
   prin github.com/owner/repo/blob/main/.env  # Show hidden file?
   ```

8. **Empty File Semantics:** Should semantic emptiness apply to remote Python files?

9. **Display Prefixes for Remote:** Should `./`, `../` work for GitHub/website URLs?

---

## 5. PROPOSED IMPLEMENTATION APPROACH

### Phase 1: Minimal Viable Alignment
**Goal:** Get GitHub and website adapters passing the same filtering tests as filesystem

1. **Add depth control fields to both adapters**
   - GitHub: Implement in `_walk_dfs` with depth tracking
   - Website: Accept in `configure()` but ignore (document as N/A)

2. **Connect category filters**
   - Parse `Context` flags in `configure()`
   - Store as instance fields (`include_hidden`, `no_docs`, etc.)
   - Apply in `should_print()` via path/name matching
   - Delegate to `filters.is_excluded()` with computed exclusion list

3. **Upgrade binary detection**
   - For GitHub: Modify to use `binary_detection.is_binary_file()` approach
   - For Website: Same approach
   - Fall back to `_is_text_bytes()` if needed

4. **Add missing category support**
   - Hidden file filtering: Check for dot-prefix in paths
   - Test directory filtering: Match against `DEFAULT_TEST_EXCLUSIONS` patterns
   - Lock file filtering: Match against `DEFAULT_LOCK_EXCLUSIONS`
   - Etc. for all categories

### Phase 2: Display Path Parity
**Goal:** Consistent display paths across adapters

1. **Define GitHub display rules** (awaiting clarification)
   - Suggested default: Relative to subpath/repo root, no special prefixes
   
2. **Define website display rules** (awaiting clarification)
   - Suggested default: Keys as-is (current behavior)
   
3. **Implement in `walk_pattern()` for each adapter**
   - Ensure `Entry.path` and `Entry.display_path` are set correctly
   - Match filesystem's pattern of separating logical path from display path

### Phase 3: Edge Cases & Polish
**Goal:** Handle all special behaviors

1. **Explicit file force-include** for remote URLs
   - Detect single-file GitHub URLs (already partially works)
   - Set `Entry.explicit=True` appropriately
   
2. **Budget optimization** 
   - Early exit from traversal when budget exhausted
   - Stop API pagination when budget is spent
   
3. **Pattern-as-file** behavior (if applicable to remote sources)
   - Clarify semantics first

### Implementation Order

**Step 1: GitHub Adapter**
- More complex due to depth controls
- More similar to filesystem (directory structure)
- Serves as reference for website adapter

**Step 2: Website Adapter**
- Simpler (flat structure)
- Can follow GitHub's pattern for category filtering

**Step 3: Shared Code Extraction**
- Extract duplicate caching logic (`_get()`, `_make_hashable()`)
- Consider shared binary detection wrapper

---

## 6. CODE REUSE OPPORTUNITIES

### Can Be Reused Directly

1. ✅ `filters.is_excluded()` - Already used by both
2. ✅ `filters.extension_match()` - Already used by both
3. ✅ `path_classifier.classify_pattern()` - Already used by both
4. ✅ `core.is_blob_semantically_empty()` - GitHub uses, website doesn't (need to add)
5. ✅ `core._is_text_bytes()`, `core._decode_text()` - Both use

### Need Adaptation

1. ⚠️ `binary_detection.is_binary_file()` - Takes file path, needs to work with bytes/URLs
   - **Solution:** Add variant that works on bytes + optional filename hint
   
2. ⚠️ `GitIgnoreEngine` - Filesystem-specific, N/A for remote sources
   - **Solution:** Not applicable to remote adapters
   
3. ⚠️ Depth tracking logic - Can't directly copy due to API differences
   - **Solution:** Implement similar pattern adapted to stack-based traversal

### Shared Patterns to Extract (DRY Violations)

**Current duplication:**
- `_make_hashable()` - Identical in GitHub and Website adapters
- `_get_cache_key()` - Identical in GitHub and Website adapters
- `_get()` function - Very similar between GitHub and Website

**Suggestion:** Extract to `src/prin/adapters/http_cache.py` or similar:
```python
# src/prin/adapters/http_cache.py
def make_hashable(value: Any) -> Any: ...
def get_cache_key(url: str, *, params: Any) -> tuple: ...
def cached_get(session: requests.Session, url: str, *, params=None, ...) -> requests.Response: ...
```

---

## 7. PARITIES.md IMPACT

### Sets to Update After Implementation

1. **Set 1 [FLAGS-CONTEXT-DEFAULTS-DOCS]**
   - Update: Add GitHub/Website adapter consumption of depth controls and category flags
   - New members: `GitHubRepoSource.configure`, `WebsiteSource.configure` consuming new fields

2. **Set 5 [FILTERS-CONSISTENCY-ACROSS-SOURCES]**
   - Update: Extend contract to explicitly include GitHub and Website
   - Add note about directory-based filters for remote sources

3. **Set 6 [SOURCE-ADAPTER-INTERFACE]**
   - Update: Remove "NOTE: Website and GitHub adapters are PARKED and OUT OF DATE"
   - Confirm all adapters now implement full protocol

4. **Set 7 [SEMANTIC-EMPTINESS-ADAPTERS]**
   - Update: Confirm website adapter now uses shared emptiness logic
   - Add usage note for remote adapters

5. **Set 8 [BINARY-FILE-DETECTION]**
   - Update: Extend to GitHub and Website adapters
   - Document remote-specific detection approach

6. **Set 13 [CLI-URL-ROUTING-ADAPTERS]**
   - Update: Clarify subpath + pattern semantics once implemented
   - Document display path choices for remote sources

### Potential New Sets

**Set N [HTTP-CACHE-BEHAVIOR]:** HTTP response caching across adapters
- Members: `github.py`: `_get`, `website.py`: `_get` (or shared module after extraction)
- Contract: Consistent disk caching, TTL, cache key generation
- Triggers: Changing cache location, TTL policy, or key generation

---

## 8. TESTING STRATEGY

### Existing Test Infrastructure

- `tests/conftest.py`: Rich fixture setup with `VFS` covering all file categories
- `tests/test_depth_controls.py`: Comprehensive depth testing
- GitHub mock via `PRIN_GH_MOCK_ROOT` environment variable
- Website cache disabling via `PRIN_DISABLE_WEB_CACHE`

### Tests to Add

1. **GitHub Adapter Tests**
   - Depth controls with nested repo structure
   - Category filtering (tests/, docs/, config/, etc.)
   - Binary file detection
   - Hidden file filtering (.gitignore, .env, etc.)
   - Pattern matching with subpaths
   - Budget exhaustion

2. **Website Adapter Tests**
   - Category filtering (extension-based)
   - Binary detection on web responses
   - Pattern matching on keys/URLs
   - llms.txt parsing edge cases
   - Budget exhaustion

3. **Cross-Adapter Consistency Tests**
   - Same pattern/filters produce consistent results across adapters
   - Budget behavior is uniform
   - Empty file detection consistency

---

## 9. POTENTIAL PITFALLS & MITIGATION

### Pitfall 1: Over-Engineering Display Paths

**Risk:** Trying to replicate filesystem's complex display semantics for remote sources

**Mitigation:** Keep it simple - remote sources have their own natural display format

### Pitfall 2: Binary Detection Performance

**Risk:** Downloading large files just to detect if they're binary

**Mitigation:** 
- Check headers first if available
- Consider `--max-size` or early-exit heuristics
- Document that remote binary detection requires download

### Pitfall 3: Depth Semantics Confusion

**Risk:** Users expect filesystem depth behavior on GitHub

**Mitigation:**
- Clear documentation
- Consistent depth=0 means "at the specified root"
- Test with nested structures

### Pitfall 4: Breaking Existing Behavior

**Risk:** Current GitHub/Website usage might break with new filters

**Mitigation:**
- Check if there are existing tests (didn't find any)
- Consider if anyone uses these adapters currently
- Default to inclusive behavior where ambiguous

---

## 10. RECOMMENDED DECISIONS (For Quick Progress)

Based on analysis, here are my suggested answers to critical questions:

### Decision 1: GitHub Display Paths
**Recommendation:** Show paths relative to the traversal root (subpath or repo root)
- `prin "" github.com/owner/repo/src` → shows `file.py`, `dir/file.py`
- Simple, predictable, matches filesystem behavior for subdirectories
- No `./` or `../` prefix support for remote sources

### Decision 2: Depth for GitHub  
**Recommendation:** Subpath is depth 0 (root of traversal), files in it are depth 1
- Matches filesystem: if you `prin "" src/`, files in `src/` are depth 1
- `--max-depth 1` shows only direct children of the specified path
- Clear, consistent with FS adapter

### Decision 3: Category Filters
**Recommendation:**
- GitHub: Respect both directory-based and extension-based filters
- Website: Extension-based filters only (no directory structure)
- Hidden files: Filter by path patterns (`.gitignore`, `*/.*`)

### Decision 4: Binary Detection
**Recommendation:** Use existing detection on fetched bytes
- Call `binary_detection.is_binary_file()` with temporary path or adapt it
- Fall back to `_is_text_bytes()` if signature detection fails
- Accept the download cost - it's unavoidable for accurate detection

### Decision 5: GitIgnore for GitHub
**Recommendation:** Keep disabled (current behavior)
- No local VCS context for remote sources
- Users can use `--exclude` for custom filtering
- Fetching remote `.gitignore` adds complexity without clear benefit

### Decision 6: Category Integration
**Recommendation:** Full integration of all category flags
- All adapters should respect: tests, lock, dependencies, docs, config, scripts, stylesheets, binary, hidden
- Behavior: Same patterns from `defaults.py`, applied to remote paths/names
- Missing categories in remote sources: Gracefully skip (e.g., no VCS ignore for GitHub)

---

## 11. OPEN QUESTIONS FOR USER

Before proceeding with implementation, please confirm or adjust:

1. **Do you agree with the recommended decisions above?** Any concerns or different preferences?

2. **For websites:** Should pattern matching work on:
   - Keys only (current)?
   - Full URLs?
   - Both?

3. **Priority:** Should I implement both adapters, or focus on GitHub first as a reference?

4. **Code extraction:** Should I extract shared HTTP caching code during this work, or defer to later refactoring?

5. **Tests:** Should I write adapter-specific tests, or rely on manual smoke testing initially?

6. **SPEC.md updates:** Should display path semantics for remote sources be added to SPEC.md, or is that out of scope?

---

## 12. NEXT STEPS

### Awaiting User Response

Once decisions are confirmed:

1. Create detailed implementation plan with task breakdown
2. Implement GitHub adapter updates (Priority 1)
3. Implement Website adapter updates (Priority 1)
4. Update PARITIES.md
5. Write/update tests
6. Run smoke tests
7. Update documentation (README.md, SPEC.md if needed)

### Estimated Scope

**GitHub Adapter:**
- ~200-300 lines of changes
- Add depth tracking: ~50 lines
- Category filtering: ~100 lines
- Binary detection: ~30 lines
- Tests: ~200 lines

**Website Adapter:**
- ~100-150 lines of changes
- Category filtering: ~80 lines
- Binary detection: ~30 lines
- Tests: ~150 lines

**Shared Code Extraction (Optional):**
- ~100 lines in new module
- ~50 lines of refactoring in adapters

**Total estimate:** 4-6 hours of focused work, plus testing and documentation.

---

## Appendix A: Adapter Method Signatures

### Current SourceAdapter Protocol
```python
class SourceAdapter(Protocol):
    def resolve(self: Self, path) -> PurePosixPath | Path: ...
    def list_dir(self: Self, dir_path) -> Iterable[Entry]: ...
    def read_file_bytes(self: Self, file_path) -> bytes: ...
    def is_empty(self: Self, file_path) -> bool: ...
    def configure(self: Self, ctx: "Context") -> None: ...
    def walk_pattern(self: Self, pattern: str, root: str | None) -> Iterable[Entry]: ...
    def should_print(self: Self, entry: Entry) -> bool: ...
    def read_body_text(self: Self, entry: Entry) -> tuple[str | None, bool]: ...
```

### Context Fields (as of current state)
```python
@dataclass
class Context:
    pattern: str
    paths: list[str]
    include_tests: bool
    include_lock: bool
    include_dependencies: bool
    include_binary: bool
    no_docs: bool
    no_config: bool
    no_scripts: bool
    no_stylesheets: bool
    include_empty: bool
    include_hidden: bool
    extensions: list[Pattern]
    exclusions: list[Pattern]
    no_exclude: bool
    no_ignore: bool
    max_depth: int | None
    min_depth: int | None
    exact_depth: int | None
    only_headers: bool
    tag: Literal["xml", "md"]
    max_files: int | None
```

---

## Appendix B: Filesystem Adapter Reference Points

Key methods to reference when implementing:

1. **Depth handling:** `FileSystemSource._walk_dfs` (lines 123-203)
   - Stack-based DFS with depth tracking
   - Depth filtering logic at file yield time

2. **Category filtering:** `FileSystemSource.should_print` (lines 335-366)
   - GitIgnore engine check first
   - `is_excluded()` delegation
   - `extension_match()` delegation
   - Empty file check last

3. **Configuration:** `FileSystemSource.configure` (lines 322-333)
   - Stores all filter-related fields
   - Initializes GitIgnore engine conditionally

4. **Display path logic:** `FileSystemSource.walk_pattern` (lines 213-319)
   - Complex rules for determining display base and prefix
   - Separation of `path` (for display/filtering) and `abs_path` (for reading)

---

**End of Analysis Document**

❗️**User thought:** we should talk about fetching llms.txt when given a `example.com/sub/something` 