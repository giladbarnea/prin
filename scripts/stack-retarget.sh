#!/usr/bin/env bash

set -euo pipefail

# Retarget PRs to create a stacked chain without rewriting history.
#
# Chain (head -> base):
#   cursor/refactor-source-adapter-traversal-logic-3aa7 -> feature/regex-default-matching
#   fs-tests-alignment -> cursor/refactor-source-adapter-traversal-logic-3aa7
#   gh-walk-fd-api -> fs-tests-alignment
#
# Behavior:
# - Detect existing open PRs for each head branch and retarget to the desired base.
# - If a PR for a head branch is missing, create it against the desired base.
# - Prefer GitHub CLI (gh) if available and authenticated; otherwise use curl with a token.
# - Minimal dynamic discovery of repo owner/name and existing PRs.
#
# Requirements for curl fallback:
# - Export one of: GH_TOKEN or GITHUB_TOKEN or GITHUB_API_TOKEN with repo:status and pull_request scopes.
#
# Usage:
#   scripts/stack-retarget.sh           # apply changes
#   DRY_RUN=1 scripts/stack-retarget.sh # print what would be done
#

DRY_RUN="${DRY_RUN:-0}"

log() {
  printf '%s\n' "$*" 1>&2
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || return 1
}

# Resolve repo (OWNER/REPO) from git remote
get_repo() {
  local url
  url=$(git config --get remote.origin.url || true)
  if [[ -z "$url" ]]; then
    log "remote.origin.url not set; are you in the repo?"; return 1
  fi
  # Accept formats:
  #   https://github.com/OWNER/REPO(.git)
  #   git@github.com:OWNER/REPO(.git)
  local owner repo
  if [[ "$url" =~ github.com[:/]+([^/]+)/([^/.]+)(\.git)?$ ]]; then
    owner="${BASH_REMATCH[1]}"
    repo="${BASH_REMATCH[2]}"
    printf '%s/%s' "$owner" "$repo"
  else
    log "Cannot parse GitHub repo from: $url"; return 1
  fi
}

have_gh() {
  if ! need_cmd gh; then return 1; fi
  if gh auth status >/dev/null 2>&1; then return 0; fi
  return 1
}

# Pick token for curl
pick_token() {
  if [[ -n "${GH_TOKEN:-}" ]]; then printf '%s' "$GH_TOKEN"; return 0; fi
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then printf '%s' "$GITHUB_TOKEN"; return 0; fi
  if [[ -n "${GITHUB_API_TOKEN:-}" ]]; then printf '%s' "$GITHUB_API_TOKEN"; return 0; fi
  return 1
}

api() {
  # $1: method, $2: path, $3: data-json(optional)
  local method="$1" path="$2" data="${3:-}"
  local token
  token=$(pick_token) || {
    log "No GitHub token found (GH_TOKEN/GITHUB_TOKEN/GITHUB_API_TOKEN)."; return 1
  }
  local hdr=(-H "Accept: application/vnd.github+json" -H "Authorization: token ${token}")
  if [[ -n "$data" ]]; then
    curl -fsS -X "$method" "https://api.github.com${path}" "${hdr[@]}" -d "$data"
  else
    curl -fsS "https://api.github.com${path}" "${hdr[@]}"
  fi
}

find_open_pr_number_for_head() {
  # $1: repo (owner/repo), $2: head branch (without owner prefix)
  local repo="$1" head="$2"
  if have_gh; then
    local num
    num=$(gh pr list --repo "$repo" --head "$head" --state open --json number --jq '.[0].number' 2>/dev/null || true)
    [[ -n "$num" && "$num" != "null" ]] && printf '%s' "$num"
    return 0
  fi
  # curl fallback
  local owner
  owner="${repo%%/*}"
  local json
  json=$(api GET "/repos/${repo}/pulls?state=open&head=${owner}:${head}" || true)
  # naive parse first PR number
  printf '%s' "$json" | sed -n 's/^\s*"number"\s*:\s*\([0-9][0-9]*\).*/\1/p' | head -n1
}

retarget_pr() {
  # $1: repo, $2: pr_number, $3: new base
  local repo="$1" num="$2" base="$3"
  log "Retarget PR #$num -> base '$base'"
  if [[ "$DRY_RUN" = "1" ]]; then return 0; fi
  if have_gh; then
    gh pr edit "$num" --repo "$repo" --base "$base"
    return $?
  fi
  api PATCH "/repos/${repo}/pulls/${num}" "{\"base\":\"${base}\"}" >/dev/null
}

create_pr() {
  # $1: repo, $2: head, $3: base
  local repo="$1" head="$2" base="$3"
  local title body
  title="${head} -> ${base} (stacked)"
  body="Automated PR for stacked review: change base to '${base}'."
  log "Create PR: head='$head' base='$base'"
  if [[ "$DRY_RUN" = "1" ]]; then return 0; fi
  if have_gh; then
    gh pr create --repo "$repo" --head "$head" --base "$base" --title "$title" --body "$body" --fill-verbose || true
    return 0
  fi
  # curl fallback
  api POST "/repos/${repo}/pulls" "{\"title\":\"${title//\"/\\\"}\",\"head\":\"${head}\",\"base\":\"${base}\",\"body\":\"${body//\"/\\\"}\"}" >/dev/null
}

main() {
  need_cmd git || { log "git is required"; exit 1; }
  local repo
  repo=$(get_repo)
  log "Repo: $repo"

  # Define stacking map (heads and desired bases)
  local heads=(
    "cursor/refactor-source-adapter-traversal-logic-3aa7"
    "fs-tests-alignment"
    "gh-walk-fd-api"
  )
  local bases=(
    "feature/regex-default-matching"
    "cursor/refactor-source-adapter-traversal-logic-3aa7"
    "fs-tests-alignment"
  )

  # Verify remote branches exist (best-effort)
  for br in "${heads[@]}" "${bases[@]}"; do
    if ! git ls-remote --exit-code --heads origin "${br}" >/dev/null 2>&1; then
      log "Warning: origin/${br} not found; continuing anyway."
    fi
  done

  # For each head->base, find or create PR, then retarget to base
  local i
  for ((i=0; i<${#heads[@]}; i++)); do
    local head="${heads[$i]}" base="${bases[$i]}"
    log "---"
    log "Head: ${head} | Base: ${base}"
    local pr
    pr=$(find_open_pr_number_for_head "$repo" "$head" || true)
    if [[ -n "$pr" ]]; then
      log "Found existing PR #$pr for head '${head}'."
      retarget_pr "$repo" "$pr" "$base"
    else
      log "No open PR found for '${head}'. Creating one against '${base}'."
      create_pr "$repo" "$head" "$base"
    fi
  done

  log "Done. If DRY_RUN=1 was set, no changes were made."
}

main "$@"

