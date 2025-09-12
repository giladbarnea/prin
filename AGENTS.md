# Agents.md

Carefully read and internalize the 3 Markdown files of the project before starting a task:
1. README.md
2. AGENTS.md (this file)
3. PARITIES.md

Then read the entire src/prin directory. It's small; this won't clutter your context window.
Whatever you do, try to align with the existing design philosophy (What knowledge each component holds, what knowledge it intentionally does not hold, responsibility and separation, what should be reused, and so on.)

## Architecture

Engine-driven depth-first traversal with source adapters; the engine is source-agnostic while implementations (filesystem, GitHub, website) provide listing/reading. Shared filters/formatters ensure identical behavior across sources.

## Core invariants
- Engine owns traversal/filters/printing; Source adapters only list/read/is_empty.
- Explicit file paths must print regardless of filters (engine handles by treating file paths as force-include).
- Paths are printed relative to each provided root (single file path prints just its basename).
- Source adapters must share as much behavior as possible and reuse common modules. Each adapter must implement as little as possible, only accounting for the thin differentiator of its domain and delegating the rest to common modules. This serves the tool's "Sources are interchangeable" design principle, which lets users forget about the type of source and have it simply printed instead.

## Source Adapters
- File system: `is_empty` via AST; raises NotADirectoryError for files (implicit via scandir). Note: it's a hack, not something to be very proud of.
- GitHub: list via Contents API; for file paths, raise NotADirectoryError so engine force-includes; ignore local .gitignore for repos.

## CLI and flags
- One shared parser in `cli_common` used by both implementations; no interactive prompts; consistent flags (`-e`, `-E`, `--no-ignore`, `-l`, etc.).
- `prin` dispatches: GitHub URL → repo implementation; otherwise filesystem. Keep URL detection minimal and robust.
- New CLI options' defaults should be defined and imported from defaults.py. When relevant, default consts should be reused consistently.
- Some function signatures and class field lists should match CLI options, and updated accordingly when new options are added. These are the features of the tool as a whole as well as its main user interface. As of writing, these are src/prin/cli_common.Context, src/prin/core.DepthFirstPrinter.__init__, and src/prin/filters.resolve_exclusions, but there may be more — keep an eye for comments saying "{Parameter,Field} list should match CLI options."

## Filtering semantics
// missing; todo

## Installation, execution, tests and linting

Everything has be executed, installed, tested and packaged using `uv`.
**If `uv` is not installed in your environment, install it by running:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
- Ensure your PATH includes `$HOME/.local/bin` so `uv` is available in your shell.
- Test with: `./test.sh [helpful pytest flags to your liking]`.
- **Important: eagerly run tests frequently, even if the user didn't ask for it.**
 - To add or remove a dependency, use `uv add` or `uv remove`. Don't modify pyproject.toml directly.
- Lint and format with ./lint.sh and ./format.sh.
- Run `prin` with ./run.sh [options].
All .sh scripts automatically install uv if missing, take care of PATH and run with uv in the right venv automatically.


## Gotchas
- Make sure the environment in which the tests operate doesn't interfere with the test results. This can manifest as unplanned parsing of project's ignore files, inadvertedly honoring the tests directory of the project itself, and so on.

## Important: Being an Effective AI Agent

1. Know your weaknesses: your eagerness to solve a problem can cause tunnel vision. You may fix the issue but unintentionally create code duplication, deviate from the existing design, or introduce a regression in other coupled parts of the project you didn’t consider. The solution is to literally look around beyond the immediate fix, be aware of (and account for) coupling around the codebase, integrate with the existing design, and periodically refactor.
2. You do your best work when you can verify yourself. With self-verification, you can and should practice continuous trial and error instead of a single shot in the dark. See [Development Cycle (Tight TDD Loop)](AGENTS.md) for how to work, verify, and report progress.

## Development Cycle (Tight TDD Loop)

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
2. Update PARITIES.md as instructed in `[Important: Working Against and Updating PARITIES.md](AGENTS.md)` and in `[Maintaining PARITIES.md](PARITIES.md)`.
3. Run `uv run src/internal/parities_check.py`.
4. Run ./format.sh to fix any fixable issues and print remaining, usually insignificant issues.
5.	Final update to user: Summarize what passed, what changed, and what still remains to be done (if anything).

## Important: Working Against and Updating PARITIES.md

`PARITIES.md` is the source of truth for what’s going on in the project. You are responsible for keeping it accurate after you have completed your task.

Initially, before making code changes: map your plan against `PARITIES.md`. Identify which elements will be affected by your changes and have a general idea of what you’ll need to update when you’re done. 
An ‘element’ is a piece of information ranging from a reference to a single symbol to a Member line, or, rarely, an entire set.

After everything is working: return to `PARITIES.md` and surgically update any parts that are no longer accurate due to your changes. Add any new items introduced by your task, and follow the instructions in `PARITIES.md` on how to maintain it.


## A Note About Tests
1. The test suite should not have any implementation footprint, nor acrobatics to make up for what the tool does or doesn't expose. If such a need arises, the project's design is flawed and should be improved until the test suite can "just test the tool".