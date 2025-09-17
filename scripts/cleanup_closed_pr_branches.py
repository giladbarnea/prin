import argparse
import os
import re
import subprocess
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import requests


GITHUB_API = "https://api.github.com"


def _get_env_token() -> Optional[str]:
    candidates = [
        "GITHUB_API_TOKEN",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "GITHUB_PAT",
        "GIT_TOKEN",
    ]
    for key in candidates:
        value = os.environ.get(key)
        if value:
            return value
    return None


def _get_token_with_fallback() -> Optional[str]:
    token = _get_env_token()
    if token:
        return token
    # Fallback: try to extract token embedded in origin URL credentials
    try:
        origin = _run(["git", "remote", "get-url", "origin"]).strip()
    except Exception:
        return None
    # Compact accidental line-breaks/spaces
    origin_compact = origin.replace("\n", "").replace(" ", "")
    # Match https://user:token@host/owner/repo(.git)?
    m = re.match(r"^[a-z]+://([^:]+):([^@]+)@[^/]+/[^/]+/[^/]+(?:\.git)?$", origin_compact)
    if m:
        user, pwd = m.group(1), m.group(2)
        # GitHub embeds tokens as password; user often 'x-access-token'
        if pwd and len(pwd) >= 20:
            return pwd
    return None


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
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "branch-cleanup-script",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get_with_pagination(url: str, headers: Dict[str, str], params: Optional[Dict[str, str]] = None) -> Iterable[dict]:
    session = requests.Session()
    while True:
        resp = session.get(url, headers=headers, params=params, timeout=30)
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
        # Ensure consistent format
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.isoformat()
    except Exception:
        return dt_str


def discover_repo_owner_and_name(explicit_owner: Optional[str], explicit_repo: Optional[str]) -> Tuple[str, str]:
    if explicit_owner and explicit_repo:
        return explicit_owner, explicit_repo
    origin = _run(["git", "remote", "get-url", "origin"]).strip()
    return _parse_owner_repo_from_origin(origin)


def get_default_branch(headers: Dict[str, str], owner: str, repo: str) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["default_branch"]


def get_open_pr_head_refs(headers: Dict[str, str], owner: str, repo: str) -> Dict[str, List[int]]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
    params = {"state": "open", "per_page": "100"}
    branch_to_prs: Dict[str, List[int]] = {}
    for pr in _get_with_pagination(url, headers, params):
        head = pr.get("head") or {}
        head_repo = (head.get("repo") or {}).get("full_name")
        head_ref = head.get("ref")
        if head_repo == f"{owner}/{repo}" and head_ref:
            branch_to_prs.setdefault(head_ref, []).append(int(pr["number"]))
    return branch_to_prs


def get_closed_prs_from_same_repo(headers: Dict[str, str], owner: str, repo: str) -> List[dict]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
    params = {"state": "closed", "per_page": "100"}
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


def branch_exists(headers: Dict[str, str], owner: str, repo: str, branch: str) -> bool:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/refs/heads/{branch}"
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    return True


def is_branch_protected(headers: Dict[str, str], owner: str, repo: str, branch: str) -> bool:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/branches/{branch}"
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    data = resp.json()
    return bool(data.get("protected"))


def delete_branch(headers: Dict[str, str], owner: str, repo: str, branch: str) -> None:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/refs/heads/{branch}"
    resp = requests.delete(url, headers=headers, timeout=30)
    # 204 No Content indicates success
    if resp.status_code not in (204,):
        resp.raise_for_status()


def find_candidate_branches(headers: Dict[str, str], owner: str, repo: str) -> List[Tuple[str, dict, str]]:
    default_branch = get_default_branch(headers, owner, repo)
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
        if not branch_exists(headers, owner, repo, branch):
            continue
        if is_branch_protected(headers, owner, repo, branch):
            continue
        # Fetch details for precise merged/closed time
        number = int(pr["number"])  # type: ignore[index]
        details = get_pr_details(headers, owner, repo, number)
        merged_at = _iso(details.get("merged_at"))
        closed_at = _iso(details.get("closed_at")) or _iso(pr.get("closed_at"))
        when = merged_at or closed_at or ""
        # Keep the latest timestamp per branch
        prev = candidates.get(branch)
        if prev is None:
            candidates[branch] = (details, when)
        else:
            _, prev_when = prev
            if when and (not prev_when or when > prev_when):
                candidates[branch] = (details, when)

    # Return as list of tuples for printing: (branch, pr_details, when)
    results: List[Tuple[str, dict, str]] = []
    for branch, (details, when) in candidates.items():
        results.append((branch, details, when))
    # Sort by time descending
    results.sort(key=lambda x: (x[2] or ""), reverse=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete remote branches that were heads of merged/closed PRs. Dry-run by default.")
    parser.add_argument("--owner", help="GitHub repo owner (optional; auto-detected if omitted)")
    parser.add_argument("--repo", help="GitHub repo name (optional; auto-detected if omitted)")
    parser.add_argument("--execute", action="store_true", help="Actually delete branches (otherwise dry-run)")
    args = parser.parse_args()

    token = _get_token_with_fallback()
    if args.execute and not token:
        raise SystemExit("GitHub token not found. Set one of: GITHUB_API_TOKEN, GITHUB_TOKEN, GH_TOKEN, GITHUB_PAT, GIT_TOKEN, or embed in origin URL.")

    owner, repo = discover_repo_owner_and_name(args.owner, args.repo)
    headers = _api_headers(token)

    try:
        candidates = find_candidate_branches(headers, owner, repo)
    except requests.HTTPError as e:
        # If auth failed but we have a token (possibly expired/invalid), retry without auth for public repos
        if getattr(e, "response", None) is not None and e.response.status_code == 401 and token:
            headers = _api_headers(None)
            candidates = find_candidate_branches(headers, owner, repo)
        else:
            raise

    if not candidates:
        print("No branches eligible for deletion were found.")
        return

    print(f"Candidates: {len(candidates)}")
    for branch, pr, when in candidates:
        number = pr.get("number")
        title = pr.get("title")
        merged_at = _iso(pr.get("merged_at"))
        closed_at = _iso(pr.get("closed_at"))
        status = "merged" if merged_at else "closed"
        ts = merged_at or closed_at or when or ""
        print(f"- {branch} — PR #{number}: {title!s} — {status} at {ts}")

    if not args.execute:
        print("\nDRY-RUN: No branches were deleted. Re-run with --execute to delete the above branches.")
        return

    print("\nDeleting branches...")
    for branch, pr, _ in candidates:
        try:
            delete_branch(headers, owner, repo, branch)
            print(f"Deleted: {branch} (PR #{pr.get('number')})")
        except requests.HTTPError as e:
            print(f"Failed to delete {branch}: {e}")


if __name__ == "__main__":
    main()

