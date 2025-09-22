#!/usr/bin/env bash
set -euo pipefail

# Requires: GH_TOKEN in env (a repo-scoped token is sufficient)
# Auto-detect owner/repo from git remote
repo_url="$(git remote get-url origin 2>/dev/null || true)"
if [ -z "${repo_url}" ]; then
  echo "Could not determine git remote 'origin' URL." >&2
  exit 1
fi

# Extract owner/repo from typical forms
owner_repo=""
case "${repo_url}" in
  *github.com/*)
    owner_repo="${repo_url#*github.com/}"
    ;;
  git@github.com:*)
    owner_repo="${repo_url#git@github.com:}"
    ;;
  *)
    echo "Unrecognized remote URL format: ${repo_url}" >&2
    exit 1
    ;;
esac
owner_repo="${owner_repo%.git}"
owner="${owner_repo%%/*}"
repo="${owner_repo#*/}"

api="https://api.github.com/repos/${owner}/${repo}/issues"

if [ -z "${GH_TOKEN:-}" ]; then
  echo "GH_TOKEN is not set." >&2
  exit 1
fi

# 1) Git ignore handling
title1="Implement .gitignore/VCS ignore semantics"
body1="Current ignore handling is stubbed off. Implement fast, correct ignore processing (dir-level, per-root, overrides), aligned with fd/rg.
Include: directory rules, per-root .gitignore, .git/info/exclude, global excludes, precedence, and tests across FS/GH (GH may ignore local ignores).
Performance: cache and incremental evaluation."

# 2) Unified pattern matching across adapters
title2="Unify glob/regex matching across adapters"
body2="Filesystem has path-based matching; GH/Website don’t interpret tokens yet.
Implement consistent glob/regex semantics across sources (segment-aware like fd), ensure display-relative matching, and add tests for FS/GH/Website.
Consider smart-case and escaping rules."

# 3) Performance/scalability for remote sources
title3="Scale remote traversal (GH/Website): perf and robustness"
body3="Optimize traversal for GitHub/Website: pagination & fewer calls, robust rate-limit/backoff (Retry-After, reset), ETag/conditional GET, bounded concurrency for listing/fetch, content-type/encoding detection, and strict timeouts.
Add stress tests and profiling."

# 4) Emptiness detection not only Python
title4="Extend emptiness detection beyond Python"
body4="Currently emptiness is Python-specific. Add language-agnostic heuristics and (optionally) per-language plugins.
Apply consistently across adapters. Include tests for common cases and ensure --include-empty correctly toggles behavior."

# 5) Binary detection improvements
title5="Improve binary detection (all adapters)"
body5="Augment byte-level NUL scan with adapter-specific hints: Content-Type on GH/Website; magic signatures where available.
Ensure consistent behavior for header-only vs body printing, and add tests for PDFs/images/archives, etc."

# 6) Symlink behavior and loop-proofing
title6="Symlink behavior: loops and explicit follow"
body6="FS ignores symlinks today. Add loop-protection tests and, optionally, a follow-symlinks mode behind a flag.
Ensure no hangs on cyclical links, and keep DFS order stable. Document behavior."

create_issue() {
  local title="$1"
  local body="$2"
  # Use curl with form fields to avoid manual JSON escaping. Parse html_url with Python (no sed/jq).
  resp=$(curl -sS -X POST "${api}" \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -F "title=${title}" \
    -F "body=${body}" || true)
  url=$(python - "$resp" <<'PY'
import sys, json
data = sys.argv[1]
try:
    obj = json.loads(data)
    print(obj.get('html_url',''))
except Exception:
    print('')
PY
)
  if [ -n "$url" ]; then
    echo "Created: $url"
  else
    echo "Failed to create issue: $title" >&2
    # Optionally echo response for troubleshooting
    # echo "$resp" >&2
  fi
}

echo "Creating issues in ${owner}/${repo} ..."
create_issue "${title1}" "${body1}"
create_issue "${title2}" "${body2}"
create_issue "${title3}" "${body3}"
create_issue "${title4}" "${body4}"
create_issue "${title5}" "${body5}"
create_issue "${title6}" "${body6}"
echo "Done."

