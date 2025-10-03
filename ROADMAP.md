---
audience: AI agents and humans
description: Feature roadmap for prin, prioritized FS-first; adapters parked for later. Presents what WILL BE (planned features and priorities), whether immediate or long-term.
updated: When any of its items are implemented or discarded.
authority rank: Has high authority over immediate plans as well as future plans. All features start here.
---

# Roadmap (Filesystem-first)

Guiding principle: maximize filesystem feature breadth and polish before investing in network adapters (GitHub/Website). SPEC.md governs existing behavior; this doc captures plans and priorities.

## P0 — Critical UX and bugs

### Features
- Ignore (binary formats):
  * .webp, .tif, .tiff - Additional image formats
  * .tgz - Compressed archive
  * .ogg, .webm, .flv - Additional media formats
  * .m4a, .aac, .flac - Audio formats
  * .mkv, .wmv, .m4v - Video formats
  * .eps, .ai, .psd - Design/graphics files
  * .sketch - Sketch design files
  * .fig - Figma files (though these are usually cloud-based)
  * .cab, .iso - Package/disk image formats (.deb and .rpm already handled)
  * .beam - Erlang/Elixir bytecode
  * .rlib - Rust library
  * .a - Static library
  * .otc, .ttc, .pfb, .pfm - Additional font files (.otf, .ttf, .woff, .woff2, .eot already handled)
- Detect binary files dynamically like `fd` does.
- `--no-config` (`json`, `yaml`, `toml`, `ini`, `cfg`, etc.)
- `--no-web` (`html*`, stylesheets, `*js*`, `ts*`, etc.)  // This would be the first flag overlapping another flag (e.g., `--no-style`). I don‘t know if this hurts product precision.

## P1 — Filesystem features breadth (core)

- Symlink handling: `-L/--follow` (and document default behavior clearly).
- Case sensitivity toggles: `-s/--case-sensitive`, `-i/--ignore-case`; default remains smart-case.
- Forced glob mode: `--glob` to force treat pattern as a glob.
- Forced regex mode: `--regex` to force treat pattern as a regex.
- Ignore file support: `--ignore-file <path>` (repeatable). Precedence: CLI excludes > ignore-file(s) > VCS ignore; last matching rule wins; negations honored. (AI suggestion)
- Size filters: `-S/--size <±NUMUNIT>` (e.g., `+10k`, `-2M`).
- Line numbers: `-n/--line-number`.
- Output throttling: `--limit-output <N>` to cap total printed lines.
- Absolute paths: `-A/--absolute-paths` to always print absolute paths regardless of `where` value.
- Structured output: `-o/--output {json,yaml,csv}` with a stable, lossless (roundtrippable) schema.

## P2 — Output formats and explainability

- Introduce `--format`/`--output-format` as stable aliases for `-t/--tag` (keep `--tag` for compatibility). (AI suggestion)
- Shell completions and `--version` flag. (AI suggestion)
- File budget polish: predictable global budget behavior across multiple FS roots; fast-stop on exhaustion. (AI suggestion)

## P3 — Performance and ergonomics (FS-focused)

- Zero-results hint: when matches are suppressed by default filters, suggest relevant include flags.
- Tree/listing modes: richer header-only displays (e.g., `--tree`) building on `--only-headers`. (AI suggestion)
- Large-tree performance profiling and optimizations (traversal, filters, formatter I/O). (AI suggestion)
- Explainability: show top-N include/exclude reasons and sample file:line matches per token (capped) to debug filters.

## Parked — Adapters and network concerns (post FS breadth)

- Website adapter completeness: URL manifest parsing, dedup/key rules; documentation examples.
- GitHub URL subpath + pattern routing parity and tests.
- Network requests cache TTL; `--no-cache` flag.

## Tooling and maintainability

- PARITIES automation: stronger symbol verification (AST scan for module-level constants), argparse-introspection to diff flags/aliases/defaults vs `README.md` and `defaults.py`.
- PARITIES suppressions: inline opt-outs via `// noqa: <token[, token...]>`.
