# Documentation Discrepancy Report

## Executive Summary
This report identifies inconsistencies between root-level markdown documentation files after reviewing README.md, SPEC.md, AGENTS.md, PARITIES.md, and ROADMAP.md against the actual codebase implementation.

---

## Critical Discrepancies

### 1. **VCS Ignore Processing Documentation Mismatch**

**Location:** README.md line 47, cli_common.py line 251, SPEC.md line 105

**Issue:** Documentation claims different ignore file sources are respected by default.

- **README.md (line 47):** Claims `.gitignore`, `.git/info/exclude`, `~/.config/git/ignore`, plus `.ignore` and `.fdignore` are honored
- **cli_common.py (line 251):** Help text mentions `.gitignore`, `.git/info/exclude`, and `~/.config/git/ignore` only
- **SPEC.md (line 105):** Matches README with all five sources mentioned
- **Implementation Reality:** `filters.py` `get_gitignore_exclusions()` returns empty list (stub implementation), and `cli_common.py` line 112 calls it but gets nothing

**Recommendation:** Either implement full gitignore support or update all docs to reflect current stub behavior.

---

### 2. **DEFAULT_TAG_CHOICES Type Annotation Error**

**Location:** defaults.py line 189

**Issue:** Type annotation is incorrect.

```python
# Current (WRONG):
DEFAULT_TAG_CHOICES: Literal["xml", "md"] = [DEFAULT_TAG, "md"]

# Should be:
DEFAULT_TAG_CHOICES: list[Literal["xml", "md"]] = [DEFAULT_TAG, "md"]
```

A `Literal["xml", "md"]` can only be the string `"xml"` OR `"md"`, not a list.

---

### 3. **Inconsistent Extension Flag Documentation**

**Location:** README.md line 131 vs cli_common.py line 241

**Issue:** Documentation mismatch on extension matching behavior.

- **README.md (line 131):** Claims `-e md -e rst -e 'md*'` will match `.md`, `.mdx`, `.mdc`, `.rst`
- **cli_common.py (line 241):** Help text says "Overrides exclusions" but doesn't mention glob expansion like `'md*'`
- **Implementation:** `_normalize_extension_to_glob()` only handles simple extensions, not wildcards within the extension itself

**Recommendation:** Clarify whether wildcard patterns in `-e` are supported or update README examples.

---

### 4. **Missing Tag Format Documentation**

**Location:** README.md lines 97-107 vs formatters.py

**Issue:** The markdown formatter output format documented in README doesn't match implementation.

**README.md shows:**
```md
## src/main.py
def main(): ...
```

**Actual implementation (formatters.py lines 26-28):**
```md
## FILE: src/main.py
====================
def main(): ...

---
```

The actual format includes "FILE: " prefix, separator line, and trailing "---".

---

### 5. **Pattern-as-File Behavior Undocumented**

**Location:** SPEC.md, README.md, prin.py lines 34-42 & 52-58

**Issue:** The pattern-as-file special case is implemented but not documented in SPEC.md or README.md.

**Current behavior:** If the pattern argument resolves to an existing file, that file is force-printed AND the pattern is still applied to subsequent paths.

**Example:**
```bash
# If AGENTS.md exists:
prin AGENTS.md src/
# Prints AGENTS.md explicitly, THEN searches src/ for files matching "AGENTS.md" pattern
```

This is mentioned in AGENTS.md line 52 but not in SPEC.md or README.md basic usage.

---

### 6. **PARITIES.md Set 4 References Non-Existent VFS**

**Location:** PARITIES.md line 101

**Issue:** References `conftest.VFS` which doesn't exist in the codebase.

```
Contract claims: "...mocks in `conftest.fs_root` and a field in `conftest.VFS`."
```

No `VFS` class/type exists in `/workspace/tests/conftest.py`.

---

### 7. **README Task Checklist References Outdated Location**

**Location:** README.md line 193

**Issue:** References `src/internal/parities_check.py` but actual path is `/workspace/src/internal/parities_check.py`

While technically the path is correct from workspace root, the checklist format is inconsistent with other references in the same file that don't use `src/` prefix for script references (e.g., line 154 uses `./test.sh` not `src/test.sh`).

---

### 8. **AGENTS.md and README.md Duplicate Parities Instructions**

**Location:** AGENTS.md lines 119-125, README.md lines 192-193, PARITIES.md lines 394-400

**Issue:** Three places describe the same process for updating PARITIES.md with slight wording variations. This violates DRY principle and creates maintenance burden.

- AGENTS.md section "Important: Work Against and Update PARITIES.md"
- README.md Task Completion Checklist step 3
- PARITIES.md section "Work Against and Update PARITIES.md"

**Recommendation:** Consolidate to one canonical location (PARITIES.md) and have others reference it.

---

### 9. **Hidden Files Representation Inconsistency**

**Location:** PARITIES.md line 102 vs defaults.py line 15

**Issue:** PARITIES.md claims hidden category uses files under dot-directories, but defaults.py defines it as glob pattern `.*`.

- **PARITIES.md:** "Hidden category in the FS fixture is represented by files under dot-directories (e.g., `.github/config`, `app/submodule/.git/config`); directories themselves are not printed."
- **defaults.py line 15:** `Hidden = Glob(".*")` - This matches dot-files AND dot-directories at ANY level

The contract note in PARITIES seems to describe test fixture expectations, not the actual filter behavior.

---

### 10. **Coverage Badge Hardcoded**

**Location:** README.md line 13

**Issue:** Coverage percentage is hardcoded in badge rather than auto-generated.

```markdown
[![coverage](https://img.shields.io/badge/coverage-56%25-red)](#)
```

This will become stale and is already inconsistent with the previous line's dynamic coverage badge (line 12).

---

### 11. **ROADMAP.md P0 Bugs Already Addressed?**

**Location:** ROADMAP.md lines 15-23

**Issue:** The positional parsing cases described as bugs appear to be the intended design per SPEC.md and AGENTS.md.

ROADMAP lists as "bugs":
- Case 1: `prin --no-docs AGENTS.md .`
- Case 2: `prin --no-docs AGENTS.md edge_config.py`

But AGENTS.md line 52 explicitly states: "If the pattern itself resolves to an existing file, that file is force-printed (explicit) regardless of filters, AND the pattern is applied to each specified path."

This suggests the behavior is by design, not a bug. Either ROADMAP needs updating or the design needs clarification.

---

### 12. **Cache Exclusion Pattern Documentation Gap**

**Location:** defaults.py line 26, ROADMAP.md line 16

**Issue:** The cache exclusion regex was recently fixed to avoid false positives (not exclude `edge_cache.py`), but:

1. The fix comment in defaults.py is verbose and technical
2. ROADMAP.md line 16 still lists "False exclusion of files like `edge_config_cache.py`" as a bug
3. The pattern `r"(^|/)[^/]*cache(/|$)"` should exclude path segments ENDING with 'cache', which WOULD still exclude `edge_cache.py` if it's in a file named `something_cache/edge_config.py`

**Recommendation:** Verify the fix actually works as intended and update ROADMAP.md accordingly.

---

### 13. **Build Directory Exclusion Pattern Inconsistency**

**Location:** PARITIES.md line 103 vs defaults.py lines 19-22

**Issue:** Documentation claims different pattern semantics than implementation.

- **PARITIES.md:** "Build directory exclusion uses path-bounded regex `(^|/)build(/|$)`"
- **defaults.py line 20:** `re.compile(r"(^|/)build(/|$)")`
- **defaults.py line 21:** `re.compile(r"^bin(/|$)")` - Note: `bin` only matches at START, not anywhere
- **defaults.py line 22:** `re.compile("dist")` - Matches anywhere, not path-bounded

The patterns are inconsistent in their bounding approach.

---

### 14. **Doc Extensions Incomplete**

**Location:** ROADMAP.md line 42, defaults.py line 61, cli_common.py line 217

**Issue:** ROADMAP suggests adding `.rtf` to doc extensions, but:

1. It's in P1, not completed
2. No ticket/issue references
3. defaults.py line 61 includes `.1` (man pages) but this isn't documented in README.md

**Recommendation:** Add `.rtf` and document `.1` in README, or clarify why `.1` is included but not documented.

---

### 15. **Alias Expansion Incomplete**

**Location:** cli_common.py lines 37-39, PARITIES.md line 180

**Issue:** Only `-uu` alias is implemented, but docs suggest `-uuu` should work.

- **cli_common.py:** Only defines `-uu` in `CLI_OPTIONS_ALIASES`
- **README.md line 225:** Documents `-uuu` as alias for `--no-exclude`/`--include-all`
- **cli_common.py line 258:** Defines `-uuu` directly in argparse, not via alias expansion

This is inconsistent - either all multi-flag shortcuts should use alias expansion, or none should.

---

## Minor Discrepancies

### 16. **Formatter Tag Naming**

**Location:** README.md line 84 vs ROADMAP.md line 65

**Issue:** ROADMAP suggests introducing `--format`/`--output-format` as "stable aliases" for `--tag`, implying current naming might change. README doesn't mention this potential instability.

---

### 17. **File Budget Behavior Underdocumented**

**Location:** README.md line 221, core.py lines 154-174

**Issue:** `--max-files` behavior is implemented but edge cases aren't documented:

- What happens when budget is exhausted mid-directory?
- Is it per-path or global? (Implementation: global per PARITIES Set 9)
- Does it count binary files shown as headers-only?

---

### 18. **Empty Python File Detection Specificity**

**Location:** cli_common.py line 224, core.py lines 60-98

**Issue:** Help text for `-M` says "Python files that only contain imports, comments, and `__all__=...` expressions" but:

1. Doesn't mention docstrings (which are allowed per implementation)
2. Only applies to `.py` and `.pyi` files (per `core.py` line 123)

---

### 19. **Metadata Frontmatter Inconsistency**

**Location:** All five .md files

**Issue:** All docs have YAML frontmatter with `audience`, `description`, `updated`, `authority rank`, but:

- **ROADMAP.md line 5:** "Has high authority over immediate plans" - subjective language
- **PARITIES.md line 5:** "Eventual source of truth" vs "source of truth" in description - contradictory
- **README.md line 5:** Says it's "Not a source of truth" but should be "derived from SPEC.md and AGENTS.md" - this creates circular dependency since SPEC also derives from requirements

---

### 20. **SPEC.md Example Path Confusion**

**Location:** SPEC.md lines 12-18, 43-87

**Issue:** Examples assume `cwd = /home` which is unusual (typically would be `/home/user` or `/home/username`). While technically valid, it creates cognitive load.

More importantly, line 66-67 shows:
```bash
$ prin main ../
../home/foo/main.py
../home/bar/main.py
```

If cwd is `/home`, then `../` is `/` (root), so the output should be:
```bash
../home/foo/main.py  # Correct: relative to / shows ../home
```

But this also means files OUTSIDE `/home` would show as `../etc/...`, `../usr/...`, etc. The example only shows results from `/home` subtree, which may be misleading.

---

## Recommendations Summary

1. **High Priority:**
   - Fix `DEFAULT_TAG_CHOICES` type annotation (breaking type error)
   - Clarify gitignore implementation status across all docs
   - Update markdown formatter documentation to match implementation
   - Remove or clarify `conftest.VFS` reference in PARITIES.md

2. **Medium Priority:**
   - Consolidate PARITIES.md update instructions to single location
   - Clarify pattern-as-file behavior in SPEC.md and README.md
   - Update ROADMAP.md to reflect which P0 items are actually bugs vs. design
   - Make build/dist/bin exclusion patterns consistent
   - Document `.1` man page extension inclusion

3. **Low Priority:**
   - Replace hardcoded coverage badge with dynamic one
   - Expand `--max-files` documentation with edge cases
   - Clarify `-M` flag help text to mention docstrings
   - Improve SPEC.md examples with more typical paths
   - Standardize alias expansion approach

---

## Files Requiring Updates

1. **README.md** - Lines 47, 97-107, 131, 192-193, 13
2. **defaults.py** - Line 189 (type error)
3. **SPEC.md** - Missing pattern-as-file documentation
4. **PARITIES.md** - Line 101 (VFS reference), lines 102-103 (pattern descriptions)
5. **ROADMAP.md** - Lines 15-23 (bug vs. feature), line 16 (already fixed?), line 42 (.rtf status)
6. **cli_common.py** - Lines 217, 224, 251 (help text improvements)
7. **AGENTS.md** - Lines 119-125 (consolidate with PARITIES.md)

---

**Report Generated:** 2025-09-30  
**Total Critical Issues:** 15  
**Total Minor Issues:** 5  
**Files Analyzed:** 5 markdown files + 5 source files