# Agents.md

Read and understand the Markdown files of the project before starting a task. 
Then read the entire codebase (besides uv.lock). It's small; this won't clutter your context window.
Whatever you do, try to align with the existing design philosophy (What knowledge each component holds, what knowledge it intentionally does not hold, responsibility and separation, what should be reused, and so on.)

### Architecture

Engine-driven depth-first traversal with source adapters; the engine is source-agnostic while implementations (filesystem, GitHub) provide listing/reading. Shared filters/formatters ensure identical behavior across sources.

### Core invariants
- Engine owns traversal/filters/printing; Source adapters only list/read/is_empty.
- Explicit file paths must print regardless of filters (engine handles by treating file paths as force-include).
- Paths are printed relative to each provided root (single file path prints just its basename).
- Source adapters must share as much behavior as possible and reuse common modules. Each adapter must implement as little as possible, only accounting for the thin differentiator of its domain and delegating the rest to common modules. This serves the tool's "Sources are interchangeable" design principle, which lets users forget about the type of source and have it simply printed instead.

### Source Adapters
- File system: `is_empty` via AST; raises NotADirectoryError for files (implicit via scandir). Note: it's a hack, not something to be very proud of.
- GitHub: list via Contents API; for file paths, raise NotADirectoryError so engine force-includes; ignore local .gitignore for repos.

### CLI and flags
- One shared parser in `cli_common` used by both implementations; no interactive prompts; consistent flags (`-e`, `-E`, `--no-ignore`, `-l`, etc.).
- `prin` dispatches: GitHub URL → repo implementation; otherwise filesystem. Keep URL detection minimal and robust.
- New CLI options' defaults should be defined and imported from defaults.py. When relevant, default consts should be reused.

### Filtering semantics
<outdated: ignore>
- Extension-based inclusions
</outdated: ignore>


### Testing and rate limits
- Use tmp_path-based tests for FS; minimize GitHub API calls in repo tests; avoid reruns; prefer single small public repo (we use TypingMind/awesome-typingmind and trouchet/rust-hello).

### uv usage: execution, tooling and packaging
Everything has be executed, installed, tested and packaged using `uv`.
**If `uv` is not installed in your environment, install it.**
- Develop and test with: `uv sync`, `./test.sh [helpful flags to your liking]`.
- **Important: eagerly run tests frequently, even if the user didn't ask for it.**
- Tooling: `uv tool install . --reinstall` (and `uv tool install git+https://github.com/giladbarnea/prin.git --reinstall`). Reinstalling is required to apply code changes to the tool.

## Ongoing Documentation Maintenance
If a piece of documentation, docstring, or comment becomes no longer true due to your recent work, modify it to represent the truth or remove it. Stay terse and succinct. Avoid detailing too much.

### Gotchas
- Don’t apply local `.gitignore` to remote repos. It is illogical: by definition, nothing in .gitignore will match remote files.

## Being an Effective AI Agent

1. You do your best work when you have a way to verify yourself. Run test.sh frequently. With self-verification, you can and should practice continuous trial and error instead of a single shot in the dark. When testing, run both problem-specific tests and wider tests to discover potential regression problems. Trial & error loop goes like this: Run tests; Give me clear and succinct status update; tell me your planned changes; apply them; repeat.
2. Know your weaknesses: your eagerness to solve a problem can lead to tunnel vision. You may fix the issue but unintentionally create code duplication, deviate from the existing design, or introduce a regression in other coupled parts of the project you didn’t consider. The solution is to often literally look around beyond the immediate problem, be aware of (and account for) coupling around the codebase, try to integrate with the existing design, and periodically refactor.
3. Do TDD when possible. Write a few simple tests before starting development. Work against them.
