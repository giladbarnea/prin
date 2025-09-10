#!/usr/bin/env python3
"""
parities_check.py — Interactive/CI diagnostics for PARITIES.md

Rules implemented (configurable severities via constants):
- Line-growth gate: ERROR if growth > FAIL_GROWTH (20 chars), WARN if growth ≥ WARN_GROWTH (5 chars).
- ID uniqueness: error on duplicate Set IDs.
- Cross-ref integrity: error if any referenced "Set <ID>" (outside headings) does not exist.
- Dangling references: error if any **Members** file path does not exist (relative to CWD).
- Test presence (unified reference check): for each **Tests** entry like
  "path/to/test_file.py::test_name", error if the file is missing or if the
  test function is not present; if only a file is given, error if missing.
- Merge opportunities (heuristic): WARN when two sets share ≥2 member paths or
  Jaccard similarity ≥ 0.5 (Members only). This is advisory.

Usage examples:
    # Default PARITIES and baseline = origin/<current-branch>:PARITIES.md
    python tools/parities_check.py

    # Explicit PARITIES, baseline from a commit-ish (uses same relative path)
    python tools/parities_check.py PARITIES.md abc1234

    # Explicit PARITIES and a baseline file on disk
    python tools/parities_check.py docs/PARITIES.md /tmp/old_PARITIES.md

Exit code: non-zero if any ERROR was emitted.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# ---------------------- Severity thresholds ----------------------------------
WARN_GROWTH = 5
FAIL_GROWTH = 20

# ---------------------- Messaging -------------------------------------------

@dataclass
class Message:
    severity: str  # "ERROR" | "WARN" | "INFO"
    rule: str
    text: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule}: {self.text}"


# ---------------------- Parsing ---------------------------------------------

SET_HEADING_RE = re.compile(r"^\s*#{2,}\s*Set\s+(\d+)\s*(?:\[[^\]]*\])?:.*$")
SECTION_RE = re.compile(r"^\s*\*\*(Members|Contract|Triggers|Tests)\*\*\s*$")
BULLET_RE = re.compile(r"^\s*-\s+(.*)$")
BACKTICK_TOKEN_RE = re.compile(r"`([^`]+)`")
SET_REF_RE = re.compile(r"\bSet\s+(\d+)\b")
TEST_SPEC_RE = re.compile(r"^(?P<path>[^:]+?)(?:::(?P<test>[A-Za-z_][A-Za-z0-9_]*))?$")

# Accepted as a file path for existence checks if it looks like a repo path or common file name
LIKELY_FILE_RE = re.compile(
    r"/|\\|\.(py|md|rst|txt|json|jsonl|toml|yaml|yml|ini|cfg|lock|rs|ts|tsx|js|jsx|sh|bat|cfg|conf|lock|mdx)$",
    re.IGNORECASE,
)


@dataclass
class SetBlock:
    sid: int
    heading_line: int
    title: str
    sections: Dict[str, List[str]] = field(default_factory=lambda: {"Members": [], "Contract": [], "Triggers": [], "Tests": []})

    @property
    def members_text(self) -> List[str]:
        return self.sections.get("Members", [])

    @property
    def tests_text(self) -> List[str]:
        return self.sections.get("Tests", [])

    def member_paths(self) -> List[str]:
        paths: List[str] = []
        for line in self.members_text:
            # Prefer backticked tokens
            toks = BACKTICK_TOKEN_RE.findall(line)
            candidates = toks if toks else [line]
            for tok in candidates:
                tok = tok.strip()
                # filter obvious non-paths
                if LIKELY_FILE_RE.search(tok) or tok in {"README.md", "LICENSE"}:
                    paths.append(tok)
        return paths

    def test_specs(self) -> List[Tuple[str, Optional[str]]]:
        specs: List[Tuple[str, Optional[str]]] = []
        for line in self.tests_text:
            # allow inline backticks or raw
            toks = BACKTICK_TOKEN_RE.findall(line) or [line]
            for tok in toks:
                tok = tok.strip()
                m = TEST_SPEC_RE.match(tok)
                if not m:
                    continue
                specs.append((m.group("path").strip(), (m.group("test") or None)))
        return specs


@dataclass
class ParsedParities:
    sets: Dict[int, SetBlock]
    references: Dict[int, List[Tuple[int, str]]]  # lines that reference Set <id>
    text: str


def parse_parities(text: str) -> ParsedParities:
    lines = text.splitlines()
    sets: Dict[int, SetBlock] = {}
    references: Dict[int, List[Tuple[int, str]]] = {}

    # First pass: locate set headings and block ranges
    heading_indices: List[Tuple[int, int, str]] = []  # (sid, line_no, title)
    for i, raw in enumerate(lines, start=1):
        m = SET_HEADING_RE.match(raw)
        if m:
            sid = int(m.group(1))
            heading_indices.append((sid, i, raw.strip()))

    # Build blocks
    for idx, (sid, start_line, title) in enumerate(heading_indices):
        end_line = heading_indices[idx + 1][1] - 1 if idx + 1 < len(heading_indices) else len(lines)
        block_lines = lines[start_line: end_line]
        # parse sections
        section = None
        sections: Dict[str, List[str]] = {"Members": [], "Contract": [], "Triggers": [], "Tests": []}
        in_fence = False
        for j, raw in enumerate(block_lines, start=start_line + 1):
            if raw.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            sm = SECTION_RE.match(raw)
            if sm:
                section = sm.group(1)
                continue
            if section and (bm := BULLET_RE.match(raw)):
                sections.setdefault(section, []).append(bm.group(1).strip())
        sets[sid] = SetBlock(sid=sid, heading_line=start_line, title=title, sections=sections)

    # Cross-references outside headings (ignore headings and code fences)
    in_fence = False
    for i, raw in enumerate(lines, start=1):
        if raw.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if SET_HEADING_RE.match(raw):
            continue
        for m in SET_REF_RE.finditer(raw):
            rid = int(m.group(1))
            references.setdefault(rid, []).append((i, raw.strip()))

    return ParsedParities(sets=sets, references=references, text=text)


# ---------------------- Rules ------------------------------------------------

def rule_line_growth(curr: str, baseline: Optional[str]) -> List[Message]:
    msgs: List[Message] = []
    if baseline is None:
        msgs.append(Message("INFO", "LineGrowth", "No baseline provided; skipping growth check."))
        return msgs
    d = len(curr) - len(baseline)
    if d > FAIL_GROWTH:
        msgs.append(Message("ERROR", "LineGrowth", f"+{d} chars exceeds fail threshold {FAIL_GROWTH}"))
    elif d >= WARN_GROWTH:
        msgs.append(Message("WARN", "LineGrowth", f"+{d} chars ≥ warn threshold {WARN_GROWTH}"))
    else:
        msgs.append(Message("INFO", "LineGrowth", f"+{d} chars within thresholds (warn={WARN_GROWTH}, fail={FAIL_GROWTH})"))
    return msgs


def rule_id_uniqueness(pp: ParsedParities) -> List[Message]:
    seen: Dict[int, int] = {}
    msgs: List[Message] = []
    for sid, sb in pp.sets.items():
        if sid in seen:
            msgs.append(Message("ERROR", "IDUniqueness", f"Duplicate Set {sid} (lines {seen[sid]} and {sb.heading_line})"))
        else:
            seen[sid] = sb.heading_line
    if not msgs:
        msgs.append(Message("INFO", "IDUniqueness", f"{len(seen)} unique Set IDs found"))
    return msgs


def rule_cross_ref(pp: ParsedParities) -> List[Message]:
    msgs: List[Message] = []
    valid = set(pp.sets.keys())
    for rid, uses in pp.references.items():
        if rid not in valid:
            for line_no, line in uses:
                msgs.append(Message("ERROR", "CrossRef", f"Reference to Set {rid} on line {line_no} is unresolved: {line}"))
    if not msgs:
        msgs.append(Message("INFO", "CrossRef", "All referenced Set IDs resolve"))
    return msgs


def _exists_cwd(p: str) -> bool:
    return (Path.cwd() / p).exists()


def rule_dangling_refs(pp: ParsedParities) -> List[Message]:
    msgs: List[Message] = []
    missing: List[Tuple[int, str]] = []
    for sid, sb in pp.sets.items():
        for p in sb.member_paths():
            if not _exists_cwd(p):
                missing.append((sid, p))
    for sid, p in missing:
        msgs.append(Message("ERROR", "DanglingMembers", f"Set {sid}: member path not found (CWD): {p}"))
    if not msgs:
        msgs.append(Message("INFO", "DanglingMembers", "All member file paths exist (relative to CWD)"))
    return msgs


def rule_tests(pp: ParsedParities) -> List[Message]:
    msgs: List[Message] = []
    for sid, sb in pp.sets.items():
        for path, tname in sb.test_specs():
            fp = Path.cwd() / path
            if not fp.exists():
                msgs.append(Message("ERROR", "Tests", f"Set {sid}: test file missing: {path}"))
                continue
            if tname:
                try:
                    text = fp.read_text(encoding="utf-8", errors="ignore")
                except Exception as e:
                    msgs.append(Message("ERROR", "Tests", f"Set {sid}: cannot read {path}: {e}"))
                    continue
                if not re.search(rf"\bdef\s+{re.escape(tname)}\s*\(", text):
                    msgs.append(Message("ERROR", "Tests", f"Set {sid}: test function not found: {path}::{tname}"))
    if not [m for m in msgs if m.severity == "ERROR"]:
        msgs.append(Message("INFO", "Tests", "All referenced tests/files are present"))
    return msgs


def rule_merge_opportunities(pp: ParsedParities) -> List[Message]:
    msgs: List[Message] = []
    # Build member sets per set ID
    members: Dict[int, set] = {sid: set(sb.member_paths()) for sid, sb in pp.sets.items()}
    sids = sorted(members.keys())
    for i in range(len(sids)):
        for j in range(i + 1, len(sids)):
            a, b = sids[i], sids[j]
            A, B = members[a], members[b]
            if not A or not B:
                continue
            inter = A & B
            if not inter:
                continue
            jaccard = len(inter) / len(A | B)
            if len(inter) >= 2 or jaccard >= 0.5:
                msgs.append(
                    Message(
                        "WARN",
                        "MergeOpportunity",
                        f"Sets {a} and {b} share {len(inter)} member paths (Jaccard={jaccard:.2f}): {sorted(list(inter))[:5]}...",
                    )
                )
    if not [m for m in msgs if m.severity == "WARN"]:
        msgs.append(Message("INFO", "MergeOpportunity", "No obvious merge candidates"))
    return msgs


# ---------------------- Baseline helpers ------------------------------------

def read_file_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def git_current_branch() -> Optional[str]:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.STDOUT)
        return out.decode("utf-8", errors="ignore").strip() or None
    except Exception:
        return None


def read_git_blob_spec(spec: str) -> Optional[str]:
    """Read git blob using full "rev:path" spec."""
    try:
        out = subprocess.check_output(["git", "show", spec], stderr=subprocess.STDOUT)
        return out.decode("utf-8", errors="ignore")
    except Exception:
        return None


def read_git_blob_rev_path(rev: str, relpath: str) -> Optional[str]:
    try:
        out = subprocess.check_output(["git", "show", f"{rev}:{relpath}"], stderr=subprocess.STDOUT)
        return out.decode("utf-8", errors="ignore")
    except Exception:
        return None


# ---------------------- Main -------------------------------------------------

def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Diagnostics for PARITIES.md")
    # Positional optional: parities path (defaults to PARITIES.md)
    ap.add_argument("parities", nargs="?", default="PARITIES.md", help="Path to PARITIES.md (default: PARITIES.md)")
    # Second positional optional: baseline (commit-ish, rev:path, or file path)
    ap.add_argument(
        "baseline",
        nargs="?",
        help=(
            "Baseline file or git ref. If a path exists on disk, it is read as file. "
            "If it contains a colon, it is treated as 'rev:path'. Otherwise it is a commit-ish and "
            "the same relative path as PARITIES is used. Default: origin/<current-branch>:PARITIES.md"
        ),
    )

    args = ap.parse_args(argv)

    parities_path = Path(args.parities).resolve()
    if not parities_path.exists():
        print(f"[ERROR] Input: file not found: {parities_path}")
        return 2

    curr_text = read_file_text(parities_path)

    # Determine baseline text
    baseline_text: Optional[str] = None
    if args.baseline:
        # If baseline is an existing file -> read; elif contains ':' -> treat as rev:path; else treat as rev only
        bp = Path(args.baseline)
        if bp.exists():
            try:
                baseline_text = read_file_text(bp)
            except Exception:
                baseline_text = None
        elif ":" in args.baseline:
            baseline_text = read_git_blob_spec(args.baseline)
        else:
            # treat as rev only
            rel = os.path.relpath(parities_path, Path.cwd())
            baseline_text = read_git_blob_rev_path(args.baseline, rel)
            if baseline_text is None:
                print(f"[WARN] Baseline: git show {args.baseline}:{rel} failed; skipping growth check")
    else:
        # Default: origin/<current-branch>:<relpath>
        branch = git_current_branch() or "HEAD"
        rel = os.path.relpath(parities_path, Path.cwd())
        spec = f"origin/{branch}:{rel}"
        baseline_text = read_git_blob_spec(spec)
        if baseline_text is None:
            print(f"[WARN] Baseline: git show {spec} failed; skipping growth check")

    pp = parse_parities(curr_text)

    messages: List[Message] = []
    messages += rule_line_growth(curr_text, baseline_text)
    messages += rule_id_uniqueness(pp)
    messages += rule_cross_ref(pp)
    messages += rule_dangling_refs(pp)
    messages += rule_tests(pp)
    messages += rule_merge_opportunities(pp)

    # Print grouped output
    severity_order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    messages.sort(key=lambda m: (severity_order.get(m.severity, 3), m.rule))
    has_error = False
    for m in messages:
        print(str(m))
        if m.severity == "ERROR":
            has_error = True

    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
