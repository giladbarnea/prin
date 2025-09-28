---
audience: contributors
description: Feature roadmap for prin, prioritized FS-first; adapters parked for later
updated: keep in sync with README and SPEC
authority rank: planning doc (derive behavior from SPEC.md)
---

# Roadmap (Filesystem-first)

Guiding principle: maximize filesystem feature breadth and polish before investing in network adapters (GitHub/Website). SPEC.md governs behavior; this doc captures priorities.

## P0 — Critical UX and bugs

- Fix positional parsing bug with dot + file + filters: `prin --no-docs -E 'tests' -E internal . -E '*.sh' README.md`.
- Zero-results hint: when matches are suppressed by default filters, suggest relevant include flags.
- Add `.rtf` to docs extensions.
- Introduce `--format`/`--output-format` as stable aliases for `-t/--tag` (keep `--tag` for compatibility). (AI suggestion)

## P1 — Filesystem breadth (core)

- Depth controls: `--max-depth`, `--min-depth`, `--exact-depth`.
- Symlink handling: `-L/--follow` (and document default behavior clearly).
- Case sensitivity toggles: `-s/--case-sensitive`, `-i/--ignore-case`; default remains smart-case.
- Forced glob mode: `-g/--glob` to treat pattern as a glob when it looks like regex.
- Ignore file support: `--ignore-file <path>` (repeatable). Precedence: CLI excludes > ignore-file(s) > VCS ignore; last matching rule wins; negations honored. (AI suggestion)
- Size filters: `-S/--size <±NUMUNIT>` (e.g., `+10k`, `-2M`).
- Line numbers: `-n/--line-number`.
- Output throttling: `--limit-output <N>` to cap total printed lines.
- Category expansions:
  - `--include-types` and default exclusion for generated type files and type sheds.
  - `--exclude-config` (opt-in) with complementary `--include-config` semantics.
  - `--no-scripts`: exclude shell scripts and `scripts/` directory.
- Matching semantics and parity:
  - Regex/glob classifier correctness and smart-case (verify vs SPEC; ensure tests).
  - fd-compat behavior (e.g., token matching like `prin /tmp/par` → `/tmp/parts.md`, `/tmp/foo/non-partisan.md`).
- Decision: `-A/--absolute-paths` — do not implement; SPEC ties display form to the “where” token shape. (AI suggestion)

## P2 — Output formats and explainability

- Structured output: `-o/--output {json,yaml,csv}` with a stable, lossless schema.
- Explainability: show top-N include/exclude reasons and sample file:line matches per token (capped) to debug filters.
- Tree/listing modes: richer header-only displays (e.g., `--tree`) building on `--only-headers`. (AI suggestion)

## P3 — Performance and ergonomics (FS-focused)

- Large-tree performance profiling and optimizations (traversal, filters, formatter I/O). (AI suggestion)
- File budget polish: predictable global budget behavior across multiple FS roots; fast-stop on exhaustion. (AI suggestion)
- Shell completions and `--version` flag. (AI suggestion)

## Parked — Adapters and network concerns (post FS breadth)

- Website adapter completeness: URL manifest parsing, dedup/key rules; documentation examples.
- GitHub URL subpath + pattern routing parity and tests.
- Network requests cache TTL; `--no-cache` flag.

## Tooling and maintainability

- PARITIES automation: stronger symbol verification (AST scan for module-level constants), argparse-introspection to diff flags/aliases/defaults vs `README.md` and `defaults.py`.
- PARITIES suppressions: inline opt-outs via `// noqa: <token[, token...]>`.

## Cross-references

- Source lists: `README.md` (overview and CLI), `AGENTS.md` (adapter notes and development cycle), `SPEC.md` (source of truth for behavior).

