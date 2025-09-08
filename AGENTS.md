# Agents.md

Read and understand the Markdown files of the project before starting a task. 
Then read the entire codebase (besides uv.lock). It's small; this won't clutter your context window.
Whatever you do, try to align with the existing design philosophy (What knowledge each component holds, what knowledge it intentionally does not hold, responsibility and separation, what should be reused, and so on.)

## Architecture

Engine-driven depth-first traversal with source adapters; the engine is source-agnostic while implementations (filesystem, GitHub) provide listing/reading. Shared filters/formatters ensure identical behavior across sources.

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
- New CLI options' defaults should be defined and imported from defaults.py. When relevant, default consts should be reused.

## Filtering semantics
// missing; todo


## Testing and rate limits
- Use tmp_path-based tests for FS; minimize GitHub API calls in repo tests; avoid reruns; prefer single small public repo (we use TypingMind/awesome-typingmind and trouchet/rust-hello). GitHub API GET requests are cached.

## uv usage: execution, tooling and packaging
Everything has be executed, installed, tested and packaged using `uv`.
**If `uv` is not installed in your environment, install it by running:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
- Ensure your PATH includes `$HOME/.local/bin` so `uv` is available in your shell.
- Develop and test with: `uv sync`, `./test.sh [helpful flags to your liking]`.
- **Important: eagerly run tests frequently, even if the user didn't ask for it.**
- Tooling: `uv tool install . --reinstall` (and `uv tool install git+https://github.com/giladbarnea/prin.git --reinstall`). Reinstalling is required to apply code changes to the tool.

## Ongoing Documentation Maintenance
If a piece of documentation, docstring, or comment becomes no longer true due to your recent work, modify it to represent the truth or remove it. Stay terse and succinct. Avoid detailing too much.

## Gotchas
- Make sure the environment in which the tests operate doesn't interfere with the test results. This can manifest as unplanned parsing of project's ignore files, inadvertedly honoring the tests directory of the project itself, and so on.

## Important: Being an Effective AI Agent

1. Know your weaknesses: your eagerness to solve a problem can cause tunnel vision. You may fix the issue but unintentionally create code duplication, deviate from the existing design, or introduce a regression in other coupled parts of the project you didn’t consider. The solution is to literally look around beyond the immediate fix, be aware of (and account for) coupling around the codebase, integrate with the existing design, and periodically refactor.
2. You do your best work when you can verify yourself. With self-verification, you can and should practice continuous trial and error instead of a single shot in the dark. See Development Cycle (Tight TDD Loop) below for how to work, verify, and report progress.

## Development Cycle (Tight TDD Loop)

#### Prep (before any code)
1.	Read first: All root markdown docs, then all Python files. The codebase is small—load it fully.
2.	Baseline: Run the full suite via ./test.sh to establish current behavior.
3.	Targeted tests: Add minimal, surgical tests that express the desired behavior. Because this project centers on filtering/formatting, include negative tests (e.g., “filter includes all type-A and excludes all non-A”), which also clarifies the intended boundaries.

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
2.	Final update: Summarize what passed, what changed, and what remains (if anything).

#### Refactor (optional, with approval)
1.	Assess fit: Step back. Check how your changes interact with the architecture and invariants. Identify any mild refactor that would align the code with the project’s intent.
2.	Ask first: Request approval for the refactor scope.
3.	Execute safely: Refactor in small steps, running the full suite frequently.
4.	Close out: Briefly state the refactor’s purpose and what changed.