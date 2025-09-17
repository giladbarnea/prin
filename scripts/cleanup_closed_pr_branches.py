import argparse
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Tuple, Any
from functools import lru_cache
import sys

import requests


GITHUB_API = "https://api.github.com"
API_VERSION = "2022-11-28"
HTTP_TIMEOUT_SECS = 30
PER_PAGE = 100


def _get_env_token() -> Optional[str]:
    candidates = ["GITHUB_TOKEN", "GITHUB_API_TOKEN", "GH_TOKEN", "GITHUB_PAT", "GIT_TOKEN"]
    for key in candidates:
        value = os.environ.get(key)
        if value:
            return value
    # Fallback: read from user file
    try:
        p = os.path.expanduser("~/.github-token")
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as fh:
                token = fh.read().strip()
                return token or None
    except Exception:
        pass
    return None


def _get_token_with_fallback() -> Optional[str]:
    return _get_env_token()


def _run(cmd: List[str]) -> str:
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _parse_owner_repo_from_origin(origin_url: str) -> Tuple[str, str]:
    # Handles: https://github.com/owner/repo(.git)? and ssh: git@github.com:owner/repo(.git)?
    origin_url = origin_url.strip()
    # Remove any embedded credentials
    origin_url = re.sub(r"://[^@]+@", "://", origin_url)
    https_match = re.match(r"^https?://[^/]+/([^/]+)/([^/]+?)(?:\.git)?$", origin_url)
    if https_match:
        return https_match.group(1), https_match.group(2)
    ssh_match = re.match(r"^git@[^:]+:([^/]+)/([^/]+?)(?:\.git)?$", origin_url)
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)
    # Some tools split lines unexpectedly; try to join if whitespace-split occurred
    compact = origin_url.replace("\n", "").replace(" ", "")
    https_match = re.match(r"^https?://[^/]+/([^/]+)/([^/]+?)(?:\.git)?$", compact)
    if https_match:
        return https_match.group(1), https_match.group(2)
    raise ValueError(f"Cannot parse owner/repo from origin URL: {origin_url}")


def _api_headers(token: Optional[str]) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "branch-cleanup-script",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get_with_pagination(url: str, headers: Dict[str, str], params: Optional[Dict[str, str]] = None) -> Iterable[dict]:
    session = requests.Session()
    while True:
        resp = session.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT_SECS)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            for item in data:
                yield item
        else:
            yield data
        # Parse Link header for pagination
        link = resp.headers.get("Link")
        if not link:
            break
        next_url = None
        for part in link.split(","):
            section = part.split(";")
            if len(section) < 2:
                continue
            url_part = section[0].strip()
            rel_part = section[1].strip()
            if rel_part == 'rel="next"':
                next_url = url_part.strip(" <>")
                break
        if next_url:
            url = next_url
            params = None  # URL already contains the params
            continue
        break


def _iso(dt_str: Optional[str]) -> Optional[str]:
    if not dt_str:
        return None
    try:
        # Normalize to aware UTC
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return dt_str


def _parse_iso_to_dt(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _fmt(dt: Optional[datetime], with_seconds: bool = False) -> str:
    if not dt:
        return "unknown"
    return dt.strftime("%Y-%m-%d %H:%M:%S" if with_seconds else "%Y-%m-%d %H:%M")


def discover_repo_owner_and_name(explicit_owner: Optional[str], explicit_repo: Optional[str]) -> Tuple[str, str]:
    if explicit_owner and explicit_repo:
        return explicit_owner, explicit_repo
    origin = _run(["git", "remote", "get-url", "origin"]).strip()
    return _parse_owner_repo_from_origin(origin)


def get_default_branch(headers: Dict[str, str], owner: str, repo: str) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT_SECS)
    resp.raise_for_status()
    return resp.json()["default_branch"]


def get_open_pr_head_refs(headers: Dict[str, str], owner: str, repo: str) -> Dict[str, List[int]]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
    params = {"state": "open", "per_page": str(PER_PAGE)}
    branch_to_prs: Dict[str, List[int]] = {}
    for pr in _get_with_pagination(url, headers, params):
        head = pr.get("head") or {}
        head_repo = (head.get("repo") or {}).get("full_name")
        head_ref = head.get("ref")
        if head_repo == f"{owner}/{repo}" and head_ref:
            branch_to_prs.setdefault(head_ref, []).append(int(pr["number"]))
    return branch_to_prs


def list_branches(headers: Dict[str, str], owner: str, repo: str) -> List[dict]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/branches"
    params = {"per_page": str(PER_PAGE)}
    return list(_get_with_pagination(url, headers, params))


def get_branch_tip_commit_iso_datetime(headers: Dict[str, str], owner: str, repo: str, branch: str) -> Optional[str]:
    # Use commits API to get the latest commit on the branch
    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
    params = {"sha": branch, "per_page": "1"}
    resp = requests.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT_SECS)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list) or not data:
        return None
    commit = data[0]
    date_str = (((commit.get("commit") or {}).get("committer") or {}).get("date"))
    return _iso(date_str)


@lru_cache(maxsize=1024)
def get_ahead_behind_cached(owner: str, repo: str, default_branch: str, branch: str, auth_key: str) -> Tuple[int, int]:
    # Compare base...head where base is default
    url = f"{GITHUB_API}/repos/{owner}/{repo}/compare/{default_branch}...{branch}"
    headers = _api_headers(auth_key or None)
    resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT_SECS)
    resp.raise_for_status()
    data = resp.json()
    return int(data.get("ahead_by", 0)), int(data.get("behind_by", 0))


def get_closed_prs_from_same_repo(headers: Dict[str, str], owner: str, repo: str) -> List[dict]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
    params = {"state": "closed", "per_page": str(PER_PAGE)}
    closed_prs: List[dict] = []
    for pr in _get_with_pagination(url, headers, params):
        head = pr.get("head") or {}
        head_repo = (head.get("repo") or {}).get("full_name")
        if head_repo == f"{owner}/{repo}":
            closed_prs.append(pr)
    return closed_prs


def get_pr_details(headers: Dict[str, str], owner: str, repo: str, number: int) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{number}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


@lru_cache(maxsize=4096)
def branch_exists_cached(owner: str, repo: str, branch: str, auth_key: str) -> bool:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/refs/heads/{branch}"
    headers = _api_headers(auth_key or None)
    resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT_SECS)
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    return True


@lru_cache(maxsize=4096)
def is_branch_protected_cached(owner: str, repo: str, branch: str, auth_key: str) -> bool:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/branches/{branch}"
    headers = _api_headers(auth_key or None)
    resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT_SECS)
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    data = resp.json()
    return bool(data.get("protected"))


def delete_branch(headers: Dict[str, str], owner: str, repo: str, branch: str) -> None:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/refs/heads/{branch}"
    resp = requests.delete(url, headers=headers, timeout=HTTP_TIMEOUT_SECS)
    # 204 No Content indicates success
    if resp.status_code not in (204,):
        resp.raise_for_status()


def find_candidate_branches(headers: Dict[str, str], owner: str, repo: str, default_branch: str, auth_key: str) -> List[Tuple[str, dict, str]]:
    open_refs = get_open_pr_head_refs(headers, owner, repo)
    closed_prs = get_closed_prs_from_same_repo(headers, owner, repo)

    # Map branch -> most relevant PR (latest merged_at/closed_at)
    candidates: Dict[str, Tuple[dict, str]] = {}
    for pr in closed_prs:
        branch = (pr.get("head") or {}).get("ref")
        if not branch:
            continue
        if branch in open_refs:
            continue  # Still used by open PR(s)
        if branch == default_branch:
            continue
        if not branch_exists_cached(owner, repo, branch, auth_key):
            continue
        if is_branch_protected_cached(owner, repo, branch, auth_key):
            continue
        # Use fields directly from PR payload; avoid N+1 details lookups
        merged_at = _iso(pr.get("merged_at"))
        closed_at = _iso(pr.get("closed_at"))
        when = merged_at or closed_at or ""
        # Keep the latest timestamp per branch
        prev = candidates.get(branch)
        if prev is None:
            candidates[branch] = (pr, when)
        else:
            _, prev_when = prev
            if when and (not prev_when or when > prev_when):
                candidates[branch] = (pr, when)

    # Return as list of tuples for printing: (branch, pr_details, when)
    results: List[Tuple[str, dict, str]] = []
    for branch, (details, when) in candidates.items():
        results.append((branch, details, when))
    # Sort by time descending
    results.sort(key=lambda x: (x[2] or ""), reverse=True)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete remote branches that were heads of merged/closed PRs. Dry-run by default.")
    parser.add_argument("--owner", help="GitHub repo owner (optional; auto-detected if omitted)")
    parser.add_argument("--repo", help="GitHub repo name (optional; auto-detected if omitted)")
    parser.add_argument("--execute", action="store_true", help="Actually delete branches (otherwise dry-run)")
    # Stale detection
    parser.add_argument("--stale", action="store_true", help="List stale branches (no deletion)")
    parser.add_argument("--behind", type=int, default=10, help="Minimum commits behind default to consider stale")
    parser.add_argument("--days", type=int, default=7, help="Minimum days since last commit to consider stale")
    parser.add_argument("-s", "--with-stale", action="store_true", help="Include stale branches (>= --behind behind and >= --days days old) in deletion candidates, regardless of PR association")
    parser.add_argument("--delete-stale-with-open-prs", action="store_true", help="Allow deletion of stale branches that currently have an open PR")
    args = parser.parse_args()

    token = _get_token_with_fallback()
    if args.execute and not token:
        print("GitHub token not found. Set one of: GITHUB_TOKEN, GITHUB_API_TOKEN, GH_TOKEN, GITHUB_PAT, GIT_TOKEN, or put a token in ~/.github-token", file=sys.stderr)
        return 1

    owner, repo = discover_repo_owner_and_name(args.owner, args.repo)
    headers = _api_headers(token)
    # Compute once per run
    default_branch = get_default_branch(headers, owner, repo)

    # If user requested stale listing, do that and exit
    if args.stale:
        open_refs = get_open_pr_head_refs(headers, owner, repo)
        branches = list_branches(headers, owner, repo)
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)

        stale: List[Tuple[str, int, int, Optional[str]]] = []
        for b in branches:
            name = b.get("name")
            if not name or name == default_branch:
                continue
            # Skip branches with open PRs
            if name in open_refs:
                continue
            # Exclude protected branches from stale reporting? Keep them, but just report.
            ahead, behind = get_ahead_behind_cached(owner, repo, default_branch, name, headers.get("Authorization", ""))
            # Last commit on branch
            tip_iso = get_branch_tip_commit_iso_datetime(headers, owner, repo, name)
            tip_dt = _parse_iso_to_dt(tip_iso)
            is_old_enough = tip_dt is None or tip_dt <= cutoff
            if behind >= args.behind and is_old_enough:
                stale.append((name, ahead, behind, tip_iso))

        if not stale:
            print("No stale branches found.")
            return 0
        print(f"Stale branches (>= {args.behind} behind and >= {args.days} days since last commit, no open PR): {len(stale)}")
        for name, ahead, behind, tip_iso in sorted(stale, key=lambda x: (x[2], x[0]), reverse=True):
            print(f"- {name} — {ahead} ahead, {behind} behind — last commit {_fmt(_parse_iso_to_dt(tip_iso))}")
        return 10

    # Standard behavior: list/delete PR-closed branches; optionally include stale branches
    auth_key = headers.get("Authorization", "")
    pr_candidates = find_candidate_branches(headers, owner, repo, default_branch, auth_key)

    def _branch_commit_times(name: str) -> Tuple[int, int, Optional[str], Optional[str]]:
        ahead, behind = get_ahead_behind_cached(owner, repo, default_branch, name, headers.get("Authorization", ""))
        last_iso = get_branch_tip_commit_iso_datetime(headers, owner, repo, name)
        first_iso = last_iso
        try:
            if ahead > 0:
                # Fetch compare commits to identify the first unique commit on branch
                url = f"{GITHUB_API}/repos/{owner}/{repo}/compare/{default_branch}...{name}"
                resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT_SECS)
                resp.raise_for_status()
                data = resp.json()
                commits = data.get("commits") or []
                if commits:
                    c0 = commits[0]
                    first_iso = _iso((((c0.get("commit") or {}).get("committer") or {}).get("date")))
        except requests.HTTPError as e:
            if getattr(e, "response", None) is not None and e.response.status_code == 401 and token:
                # retry unauthenticated
                ah = _api_headers(None)
                ahead, behind = get_ahead_behind_cached(owner, repo, default_branch, name, "")
                last_iso = get_branch_tip_commit_iso_datetime(ah, owner, repo, name)
        return ahead, behind, first_iso, last_iso

    # Prepare PR list entries (B+PR)
    pr_by_branch: Dict[str, Tuple[dict, str]] = {}
    for branch, pr, when in pr_candidates:
        pr_by_branch[branch] = (pr, when)

    # Optional stale scan to include branches regardless of PR association
    stale_by_branch: Dict[str, Dict[str, Any]] = {}
    if args.with_stale:
        cutoff = datetime.utcnow() - timedelta(days=args.days)
        branches = list_branches(headers, owner, repo)
        for b in branches:
            name = b.get("name")
            if not name or name == default_branch:
                continue
            # Skip default and non-existent handled above; keep protected branches in listing but they'll be filtered on delete
            ahead, behind, first_iso, last_iso = _branch_commit_times(name)
            # Parse last commit iso to datetime for staleness
            last_dt = None
            if last_iso:
                try:
                    last_dt = datetime.fromisoformat(last_iso.replace("Z", "+00:00")).astimezone(tz=None).replace(tzinfo=None)
                except Exception:
                    last_dt = None
            is_old_enough = last_dt is None or last_dt <= cutoff
            if behind >= args.behind and is_old_enough:
                stale_by_branch[name] = {
                    "ahead": ahead,
                    "behind": behind,
                    "first_iso": first_iso,
                    "last_iso": last_iso,
                    "has_open_pr": name in get_open_pr_head_refs(headers, owner, repo),
                }

    # Merge and de-duplicate (prefer PR info for branches that appear in both)
    merged_entries: List[Dict[str, Any]] = []
    seen: set[str] = set()

    # Add PR-based entries first
    for branch, (pr, when) in pr_by_branch.items():
        ahead, behind, first_iso, last_iso = _branch_commit_times(branch)
        merged_entries.append({
            "branch": branch,
            "kind": "with_pr",
            "pr": pr,
            "recent_iso": when,
            "ahead": ahead,
            "behind": behind,
            "first_iso": first_iso,
            "last_iso": last_iso,
        })
        seen.add(branch)

    # Add stale-only branches that weren't in PR list
    if args.with_stale:
        for branch, info in stale_by_branch.items():
            if branch in seen:
                continue
            merged_entries.append({
                "branch": branch,
                "kind": "without_pr",
                "recent_iso": info.get("last_iso") or "",
                "ahead": info.get("ahead", 0),
                "behind": info.get("behind", 0),
                "first_iso": info.get("first_iso"),
                "last_iso": info.get("last_iso"),
            })
            seen.add(branch)

    # If not executing, present the list; else proceed to delete
    if not args.execute:
        if not merged_entries:
            if args.with_stale:
                print("No branches eligible for deletion were found (including stale criteria).")
            else:
                print("No branches eligible for deletion were found.")
            return 0

        # Sort by recent first: PR merged/closed time for with_pr; last commit for without_pr
        def _recent_key(entry: Dict[str, Any]) -> str:
            iso = entry.get("recent_iso") or ""
            return iso

        merged_entries.sort(key=_recent_key, reverse=True)

        # Numbered plaintext list with requested formats
        print(f"Candidates: {len(merged_entries)}")
        for idx, entry in enumerate(merged_entries, start=1):
            branch = entry["branch"]
            ahead = entry.get("ahead", 0)
            behind = entry.get("behind", 0)
            first_iso = entry.get("first_iso") or ""
            last_iso = entry.get("last_iso") or ""
            flag = ""
            if entry.get("kind") == "without_pr" and entry.get("has_open_pr") and not args.delete_stale_with_open_prs:
                flag = "[!] "

            if entry["kind"] == "without_pr":
                print(f"{idx}. {flag}{branch} — {ahead} ahead, {behind} behind — first commit {_fmt(_parse_iso_to_dt(first_iso))} — last commit {_fmt(_parse_iso_to_dt(last_iso))}")
            else:
                pr = entry["pr"]
                number = pr.get("number")
                title = pr.get("title")
                merged_at = _iso(pr.get("merged_at"))
                closed_at = _iso(pr.get("closed_at"))
                when = merged_at or closed_at or entry.get("recent_iso") or ""
                print(f"{idx}. {branch} — PR #{number}: {title!s} — first commit {_fmt(_parse_iso_to_dt(first_iso))} — last commit {_fmt(_parse_iso_to_dt(last_iso))}")
                print(f"— merged at {_fmt(_parse_iso_to_dt(when), with_seconds=True)}")

        print("\nDRY-RUN: No branches were deleted. Re-run with --execute to delete the above branches.")
        return 10

    # Execute deletion path
    # Build final deletion set from merged entries, re-check safety filters
    deletion_order = merged_entries
    # If no stale requested, deletion_order is PR-based only
    branches_to_delete: List[str] = []
    not_deleted_open_pr: List[str] = []
    for entry in deletion_order:
        branch = entry["branch"]
        if branch == default_branch:
            continue
        if not branch_exists_cached(owner, repo, branch, headers.get("Authorization", "")):
            continue
        if is_branch_protected_cached(owner, repo, branch, headers.get("Authorization", "")):
            continue
        if entry.get("kind") == "without_pr" and entry.get("has_open_pr") and not args.delete_stale_with_open_prs:
            not_deleted_open_pr.append(branch)
            continue
        branches_to_delete.append(branch)

    if not branches_to_delete:
        print("No branches passed deletion safety checks. Nothing to delete.")
        return 0

    print("\nDeleting branches...")
    for branch in branches_to_delete:
        try:
            delete_branch(headers, owner, repo, branch)
            print(f"Deleted: {branch}")
        except requests.HTTPError as e:
            print(f"Failed to delete {branch}: {e}")
    if not_deleted_open_pr:
        print("\nNot deleted due to having an open PR (use --delete-stale-with-open-prs to delete):")
        for b in not_deleted_open_pr:
            print(f"- {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

