# Agents

This file contains instructions for AI agents to adhere to throughout an entire task lifespan.

Carefully read and internalize the 3 Markdown files of the project before starting a task:
1. README.md
2. AGENTS.md (this file)
3. PARITIES.md

Whatever you do, try to align with the existing design philosophy (What knowledge each component holds, what knowledge it intentionally does not hold, responsibility and separation, what should be reused, and so on.)

## Architecture

Adapters own traversal. The printer (engine) is source-agnostic and is limited to printing with a formatter and enforcing a file budget. Implementations (filesystem, GitHub, website) provide traversal and I/O, and may delegate filtering/emptiness to shared helpers.

## Core invariants
- Adapters own traversal and include/exclude/emptiness/I/O. Printer owns printing, budget, and formatter.
- Printer delegates decisions via `SourceAdapter.should_print(entry)` and reading via `SourceAdapter.read_body_text(entry)`.
- Explicit file roots must print regardless of filters (signaled via `Entry.explicit=True` and honored by adapter `should_print`).
- Paths are printed relative to the adapter-chosen display base (typically anchor when under it; otherwise the root itself).
- Adapters should share behavior where possible by delegating to common modules (filters, emptiness) while keeping a uniform interface.

## Source Adapters
- File system: owns DFS via `walk(token)` and `walk_dfs(root)`, config via `configure(ctx)`, include/exclude via `should_print(entry)`, and body reads via `read_body_text(entry)` (may delegate to shared emptiness/text detection).
- GitHub: should expose the same shape: `configure`, `walk`, `should_print`, `read_body_text`. `.gitignore` semantics are independent.
- Website: // todo

## CLI and flags
- One shared parser in `cli_common`; no interactive prompts; consistent flags.
- `prin` dispatches: GitHub URL → repo implementation; otherwise filesystem. Keep URL detection minimal and robust. // todo: missing website
- New CLI options' defaults should be defined and imported from defaults.py. When relevant, default consts should be reused consistently.
- Adapters consume config via `SourceAdapter.configure(Context)`; keep `Context` in sync with CLI options.

## Filtering semantics

prin matches tokens in two modes, uniformly across adapters:

- Existing path mode: If a positional token resolves to an existing root (file or directory) in the adapter’s domain, traversal starts at that root and printed paths are relative to the chosen base (typically the adapter anchor/root). Explicit file roots are force-included regardless of filters.
- Pattern mode: If a token does not resolve as a path, it is treated as a pattern:
  - Classifier distinguishes `glob` vs `regex`.
  - Matching is performed against the full display-relative path (not just the basename).
  - Case sensitivity follows the underlying engine (Python `re` for regex, `fnmatch` for globs).
  - Default filters (docs, binary, tests, hidden, etc.) still apply unless toggled.

For GitHub URLs, subpaths may include literal segments and a trailing pattern segment. The literal base is traversed and the pattern matches the full display-relative path under that base.

## How to install, execute, test and lint

### Use test.sh, run.sh and format.sh for testing, running `prin` and formatting

All .sh scripts automatically install uv if missing, take care of PATH and execute with the right venv to spare you from doing that yourself.

- **Important: eagerly run tests frequently, even if the user didn't ask for it.**

 - To add or remove a dependency, use `uv add` or `uv remove`. Don't modify pyproject.toml directly.

## Gotchas
- Make sure the environment in which the tests operate doesn't interfere with the test results. This can manifest as unplanned parsing of project's ignore files, inadvertedly honoring the tests directory of the project itself, and so on.

## Important: Being an Effective AI Agent

1. Know your weaknesses: your eagerness to solve a problem can cause tunnel vision. You may fix the issue but unintentionally create code duplication, deviate from the existing design, or introduce a regression in other coupled parts of the project you didn’t consider. The solution is to literally look around beyond the immediate fix, be aware of (and account for) coupling around the codebase, integrate with the existing design, and periodically refactor.
2. You do your best work when you can verify yourself. With self-verification, you can and should practice continuous trial and error instead of a single shot in the dark. See [Development Cycle (Tight TDD Loop)](AGENTS.md) for how to work, verify, and report progress.

## Development Conventions

- Prefer `pathlib` to `os.path`. For example, use `Path.open()` instead of `open()`, and `Path.glob` instead of `glob`.
- NEVER use Pytest's `tmp_path` fixture. Use the custom `prin_tmp_path` instead.

---

## Important: Development Cycle (Tight TDD Loop)

#### Prep (before any code)
1.	Read first: README.md and PARITIES.md.
2. Recognize elements in PARITIES.md relevant to your plan. You'll then know what your changes will affect around the project.
3. Baseline: Run the full suite via ./test.sh to establish current behavior.
4. Targeted tests: Add minimal, surgical tests that express the desired behavior. Because this project centers on filtering/formatting, include negative tests (e.g., “filter includes all type-A and excludes all non-A”), which also clarifies the intended boundaries.

#### The loop
Repeat the following until all new tests pass:
1.	Smallest viable change: Implement the minimal change to pass the next failing test.
2.	Verify: Run that test and the pre-existing suite to catch regressions.
3.	Report (each iteration): Post a short update: what you tried, current result, and your next step.
4.	Branch:
	- If passing: Move to the next failing test.
	- If stuck: Assume an “unknown unknown.” Form a hypothesis, try a focused fix. After a few failed attempts, stop and tell me: what’s failing, what you tried, and your current hypothesis.

#### After the loop
1.	Full verification: Run the entire suite again with ./test.sh.
2. Update PARITIES.md as instructed in [Important: Working Against and Updating PARITIES.md](AGENTS.md) and in [Maintaining PARITIES.md](PARITIES.md).
3. Run `uv run src/internal/parities_check.py`.
4. Run ./format.sh to fix any fixable issues and print remaining, usually insignificant issues.
5.	Final update to user: Summarize what passed, what changed, and what still remains to be done (if anything).

**always add an item to every to-do list you create throughout the entire session saying 'ensure I remember the instructions about maintaining and updating PARITIES.md and the instructions about the TDD dev cycle'.**

## Important: Work Against and Update PARITIES.md

1. **`PARITIES.md` is the source of truth** for what’s going on in the project. You are responsible for keeping it accurate after you have completed your task.
2. Initially, before making code changes: **map your plan against `PARITIES.md`.** Identify which elements will be affected by your changes and have a general idea of what you’ll need to update when you’re done. 
* An ‘element’ is a piece of information ranging from a reference to a single symbol to a Member line, or, rarely, an entire set.
3. After everything is working: **return to `PARITIES.md` and surgically update** any parts that are no longer accurate due to your changes. **Add any new items introduced by your task**, and **follow the instructions in [Maintaining PARITIES.md](PARITIES.md)**.
