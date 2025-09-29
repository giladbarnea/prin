#!/usr/bin/env bash
set -euo pipefail

# Smoke test runner for prin
# Prints category-based expectations before each run

source ./.common.sh

# Helper to print a descriptive expectation message
say() { message "$1"; }

# Warm-up (prints CLI help)
say "Running 'prin --help': Help text should be printed"
./run.sh --help | head -30 | cat

# --- Pattern variants (what-then-where) ---
# Regex '.' in pattern position
say "Running 'prin . -l': default filters apply → include docs and regular files; exclude tests, locks, binaries, hidden, build artifacts, caches, logs, secrets"
./run.sh . -l | head -30 | cat

# Regex '.' then explicit '.' search_path
say "Running 'prin . . -l': same categories as above; display is dot-relative"
./run.sh . . -l | head -30 | cat

# Regex '.' then absolute PWD search_path
say "Running 'prin . $PWD -l': same categories as above; display uses absolute path base"
./run.sh . "$PWD" -l | head -30 | cat

# Glob '*' variants
say "Running 'prin "*" -l': glob matches all paths; default filters still apply (docs + regular; non-test, non-lock, non-binary, non-hidden)"
./run.sh '*' -l | head -30 | cat

say "Running 'prin "*" . -l': same categories; dot-relative display"
./run.sh '*' . -l | head -30 | cat

say "Running 'prin "*" $PWD -l': same categories; absolute display base"
./run.sh '*' "$PWD" -l | head -30 | cat

# Regex '.*' variants (quote to avoid shell expansion)
say "Running 'prin ".*" -l': regex matches all paths; default filters still apply (docs + regular; non-test, non-lock, non-binary, non-hidden)"
./run.sh '.*' -l | head -30 | cat

say "Running 'prin ".*" . -l': same categories; dot-relative display"
./run.sh '.*' . -l | head -30 | cat

say "Running 'prin ".*" $PWD -l': same categories; absolute display base"
./run.sh '.*' "$PWD" -l | head -30 | cat

# --- One line per CLI option ---
# -H, --hidden
say "Running 'prin . -H -l': include hidden files and dot-directories in addition to default inclusions (docs + regular); still exclude tests, locks, binaries"
./run.sh . -H -l | head -30 | cat

# -I, --no-ignore (gitignore currently stubbed; no effect today)
say "Running 'prin . -I -l': disable gitignore processing (no effect with current stub); default categories otherwise"
./run.sh . -I -l | head -30 | cat

# -E, --exclude (repeatable)
say "Running 'prin . -E "*.md" -l': exclude Markdown docs; print regular, non-doc files; still exclude tests, locks, binaries, hidden"
./run.sh . -E '*.md' -l | head -30 | cat

# -e, --extension (repeatable)
say "Running 'prin . -e md -l': include only Markdown docs; overrides defaults; still excludes hidden unless -H; tests/locks/binaries unaffected unless matching md"
./run.sh . -e md -l | head -30 | cat

# -T, --include-tests
say "Running 'prin . -T -l': include tests in addition to default inclusions; still exclude locks, binaries, hidden"
./run.sh . -T -l | head -30 | cat

# -K, --include-lock
say "Running 'prin . -K -l': include lock files in addition to default inclusions; still exclude tests, binaries, hidden"
./run.sh . -K -l | head -30 | cat

# -d, --no-docs
say "Running 'prin . -d -l': exclude docs; include regular code and config; still exclude tests, locks, binaries, hidden"
./run.sh . -d -l | head -30 | cat

# -M, --include-empty
say "Running 'prin . -M -l': include empty files (and semantically-empty Python) in addition to default inclusions; still exclude tests, locks, binaries, hidden"
./run.sh . -M -l | head -30 | cat

# -l, --only-headers (header-only listing)
say "Running 'prin . -l': only headers (paths) are printed; categories unchanged (docs + regular; non-test, non-lock, non-binary, non-hidden)"
./run.sh . -l | head -30 | cat

# -t, --tag {xml|md}
say "Running 'prin . -t md': output tag/format changes (Markdown) but categories unchanged"
./run.sh . -t md | head -30 | cat

# --max-files <n>
say "Running 'prin . --max-files 5 -l': same categories as default; output limited to 5 files globally"
./run.sh . --max-files 5 -l | head -30 | cat

# -a, --text/--include-binary/--binary
say "Running 'prin . -a -l': include binary files in addition to default inclusions; still exclude hidden unless -H"
./run.sh . -a -l | head -30 | cat

# -uu alias (expands to --hidden --no-ignore)
say "Running 'prin . -uu -l': include hidden; disable gitignore processing (no effect with current stub); otherwise default categories"
./run.sh . -uu -l | head -30 | cat

# -uuu/--no-exclude/--include-all
say "Running 'prin . -uuu -l': include everything (overrides exclusions): docs, tests, locks, binaries, hidden, and build artifacts"
./run.sh . -uuu -l | head -30 | cat

