import itertools
from typing import Callable, Dict, List, Set, Tuple

import pytest

from prin.adapters.github import GitHubURL, parse_github_url


OwnerRepo = Tuple[str, str]
Exp = Tuple[str | None, str]  # (ref, subpath)

OWNER, REPO = "TypingMind", "awesome-typingmind"
REF = "deadbeefcafebabe"
SUBPATH_DIR = "docs"
SUBPATH_FILE = "docs/Guide.md"


# Real/base formats (host+path without scheme); value is (builder, expected)
# Builders return host+path without any scheme or modifiers, alongside expected (ref, subpath)
RealBuilder = Callable[[OwnerRepo], Tuple[str, Exp]]


def _standard_root(or_: OwnerRepo) -> Tuple[str, Exp]:
    o, r = or_
    return (f"github.com/{o}/{r}", (None, ""))


def _standard_subpath(or_: OwnerRepo) -> Tuple[str, Exp]:
    o, r = or_
    return (f"github.com/{o}/{r}/{SUBPATH_FILE}", (None, SUBPATH_FILE))


def _tree_root(or_: OwnerRepo) -> Tuple[str, Exp]:
    o, r = or_
    return (f"github.com/{o}/{r}/tree/{REF}", (REF, ""))


def _tree_subpath(or_: OwnerRepo) -> Tuple[str, Exp]:
    o, r = or_
    return (f"github.com/{o}/{r}/tree/{REF}/{SUBPATH_DIR}", (REF, SUBPATH_DIR))


def _blob_file(or_: OwnerRepo) -> Tuple[str, Exp]:
    o, r = or_
    return (f"github.com/{o}/{r}/blob/{REF}/{SUBPATH_FILE}", (REF, SUBPATH_FILE))


def _commit(or_: OwnerRepo) -> Tuple[str, Exp]:
    o, r = or_
    return (f"github.com/{o}/{r}/commit/{REF}", (REF, ""))


def _api_contents_root(or_: OwnerRepo) -> Tuple[str, Exp]:
    o, r = or_
    return (f"api.github.com/repos/{o}/{r}/contents?ref={REF}", (REF, ""))


def _api_contents_file(or_: OwnerRepo) -> Tuple[str, Exp]:
    o, r = or_
    return (f"api.github.com/repos/{o}/{r}/contents/{SUBPATH_FILE}?ref={REF}", (REF, SUBPATH_FILE))


def _api_git_trees(or_: OwnerRepo) -> Tuple[str, Exp]:
    o, r = or_
    return (f"api.github.com/repos/{o}/{r}/git/trees/{REF}", (REF, ""))


def _raw_file(or_: OwnerRepo) -> Tuple[str, Exp]:
    o, r = or_
    return (f"raw.githubusercontent.com/{o}/{r}/{REF}/{SUBPATH_FILE}", (REF, SUBPATH_FILE))


REAL_FORMATS: Dict[str, RealBuilder] = {
    "standard_root": _standard_root,
    "standard_subpath": _standard_subpath,
    "tree_root": _tree_root,
    "tree_subpath": _tree_subpath,
    "blob_file": _blob_file,
    "commit": _commit,
    "api_contents_root": _api_contents_root,
    "api_contents_file": _api_contents_file,
    "api_git_trees": _api_git_trees,
    "raw_file": _raw_file,
}


# Fake modifiers
# semantics:
# - https: prepend "https://"
# - www: replace leading host "github.com" with "www.github.com"
# - trailing_slash: append "/"
# - trailing_git: append ".git" (only at repository root)
# - git_plus: replace leading "https://" with "git+https://" (requires https)
MOD_HTTPS = "https"
MOD_WWW = "www"
MOD_TRAIL_SLASH = "trailing_slash"
MOD_TRAIL_GIT = "trailing_git"
MOD_GIT_PLUS = "git_plus"

ALL_MODS: Set[str] = {MOD_HTTPS, MOD_WWW, MOD_TRAIL_SLASH, MOD_TRAIL_GIT, MOD_GIT_PLUS}

# Per real format, which modifiers may apply in principle
REAL_TO_ALLOWED_MODS: Dict[str, Set[str]] = {
    # Web pages on github.com may accept https, www, trailing slash; some can accept git+ (root only) and .git (root only)
    "standard_root": {MOD_HTTPS, MOD_WWW, MOD_TRAIL_SLASH, MOD_TRAIL_GIT, MOD_GIT_PLUS},
    "standard_subpath": {MOD_HTTPS, MOD_WWW, MOD_TRAIL_SLASH},
    "tree_root": {MOD_HTTPS, MOD_WWW, MOD_TRAIL_SLASH},
    "tree_subpath": {MOD_HTTPS, MOD_WWW, MOD_TRAIL_SLASH},
    "blob_file": {MOD_HTTPS, MOD_WWW, MOD_TRAIL_SLASH},
    "commit": {MOD_HTTPS, MOD_WWW, MOD_TRAIL_SLASH},
    # API/raw do not accept www/git_plus/.git and are sensitive to trailing slash
    "api_contents_root": {MOD_HTTPS},
    "api_contents_file": {MOD_HTTPS},
    "api_git_trees": {MOD_HTTPS},
    "raw_file": {MOD_HTTPS},
}


def _host_of(base: str) -> str:
    return base.split("/", 1)[0]


def _apply_modifiers(base: str, mods: Set[str]) -> str:
    host = _host_of(base)
    url = base

    # www only for github.com hosts
    if MOD_WWW in mods:
        assert host == "github.com"
        url = url.replace("github.com", "www.github.com", 1)
        host = "www.github.com"

    # scheme
    if MOD_HTTPS in mods:
        url = f"https://{url}"
    # git+ requires https scheme
    if MOD_GIT_PLUS in mods:
        assert MOD_HTTPS in mods
        assert host in ("github.com", "www.github.com")
        url = url.replace("https://", "git+https://", 1)

    # trailing git at end
    if MOD_TRAIL_GIT in mods:
        # only valid at repo root on github.com
        assert _host_of(base) == "github.com"
        assert base.count("/") == 2  # github.com/<o>/<r>
        url = f"{url}.git"

    if MOD_TRAIL_SLASH in mods:
        # safe for pages (not for api/raw)
        url = f"{url}/"

    return url


def _valid_combo(real_key: str, mods: Set[str], base: str) -> bool:
    host = _host_of(base)
    # www only for github.com
    if MOD_WWW in mods and host != "github.com":
        return False
    # git+ requires https
    if MOD_GIT_PLUS in mods and MOD_HTTPS not in mods:
        return False
    # .git only for standard_root
    if MOD_TRAIL_GIT in mods and real_key != "standard_root":
        return False
    # trailing slash not for api/raw
    if MOD_TRAIL_SLASH in mods and host in ("api.github.com", "raw.githubusercontent.com"):
        return False
    return True


def _generate_urls() -> List[Tuple[str, Exp]]:
    out: List[Tuple[str, Exp]] = []
    for real_key, builder in REAL_FORMATS.items():
        base, exp = builder((OWNER, REPO))
        allowed = REAL_TO_ALLOWED_MODS[real_key]
        # generate all subsets of allowed mods (up to size 2 to keep the set compact)
        allowed_list = sorted(allowed)
        mod_subsets: List[Set[str]] = [set()]
        # singletons
        mod_subsets.extend({m} for m in allowed_list)
        # pairs
        for a, b in itertools.combinations(allowed_list, 2):
            mod_subsets.append({a, b})
        # selected triples that are common: https+www+trailing_slash; https+git_plus+trailing_git
        triples = [
            {MOD_HTTPS, MOD_WWW, MOD_TRAIL_SLASH},
            {MOD_HTTPS, MOD_GIT_PLUS, MOD_TRAIL_GIT},
        ]
        for tri in triples:
            if tri.issubset(allowed):
                mod_subsets.append(tri)

        for mods in mod_subsets:
            if not _valid_combo(real_key, mods, base):
                continue
            url = _apply_modifiers(base, mods)
            out.append((url, exp))
    return out


@pytest.mark.parametrize("url,exp", _generate_urls())
def test_parse_github_url_combinations(url: str, exp: Exp) -> None:
    parsed: GitHubURL = parse_github_url(url)
    assert parsed["owner"] == OWNER
    assert parsed["repo"] == REPO
    assert parsed["ref"] == exp[0]
    assert parsed["subpath"] == exp[1]