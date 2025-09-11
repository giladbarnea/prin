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
SECTION_RE = re.compile(
    r"^\s*(?:\*\*(Members|Contract|Triggers|Tests)\*\*|#{3,6}\s*(Members|Contract|Triggers|Tests))\s*$"
)
BULLET_RE = re.compile(r"^\s*-\s+(.*)$")
BACKTICK_TOKEN_RE = re.compile(r"`([^`]+)`")
SET_REF_RE = re.compile(r"\bSet\s+(\d+)\b")
TEST_SPEC_RE = re.compile(r"^(?P<path>[^:]+?)(?:::(?P<test>[A-Za-z_][A-Za-z0-9_]*))?$")

# Accepted as a file path for existence checks if it looks like a repo path or common file name
LIKELY_FILE_RE = re.compile(
    r"/|\\|\.(py|md|rst|txt|json|jsonl|toml|yaml|yml|ini|cfg|lock|rs|ts|tsx|js|jsx|sh|bat|cfg|conf|lock|mdx)$",
    re.IGNORECASE,
)

CLI_FLAG_RE = re.compile(r"^-{1,3}[A-Za-z][A-Za-z-]*$|^-u{2,3}$")
CLI_FLAG_FINDER_RE = re.compile(r"(?<!\S)(-{1,3}[A-Za-z][A-Za-z-]*|-u{2,3})(?!\S)")


def normalize_symbol_token(token: str) -> str:
    """Normalize a backticked token for AST resolution.

    Rules:
    - Strip trailing parentheses with optional ellipsis: "foo(...)" → "foo", "bar()" → "bar".
    - Trim whitespace around the token.
    - Preserve glob-like tokens such as "DEFAULT_*" as-is.
    - Leave file paths unchanged (they won't match the parens pattern).
    """
    t = token.strip()
    # Remove trailing () or (...)
    t = re.sub(r"\s*\((?:\s*\.\.\.\s*)?\)\s*$", "", t)
    return t


def extract_ast_tokens_from_members(member_lines: List[str]) -> List[str]:
    """Extract and normalize tokens from **Members** lines suitable for AST lookup.

    This collects all backticked tokens from the lines and applies normalization
    so that function/symbol names are resolvable by AST tools (e.g., symbex).
    """
    tokens: List[str] = []
    for line in member_lines:
        raw_tokens = BACKTICK_TOKEN_RE.findall(line)
        for raw in raw_tokens:
            token = normalize_symbol_token(raw)
            # Skip file-like tokens
            if LIKELY_FILE_RE.search(token) or token in {"README.md", "LICENSE"}:
                continue
            # Skip wildcard patterns like DEFAULT_*
            if "*" in token:
                continue
            # Skip ALL_CAPS constants which symbex cannot resolve
            if re.fullmatch(r"[A-Z0-9_]+", token):
                continue
            tokens.append(token)
    return tokens


@dataclass
class SetBlock:
    sid: int
    heading_line: int
    title: str
    sections: Dict[str, List[str]] = field(
        default_factory=lambda: {"Members": [], "Contract": [], "Triggers": [], "Tests": []}
    )

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
                # Only accept likely file paths (to avoid treating prose tokens as tests)
                if CLI_FLAG_RE.match(tok):
                    continue
                if not ("/" in tok or tok.endswith(".py")):
                    continue
                m = TEST_SPEC_RE.match(tok)
                if not m:
                    continue
                specs.append((m.group("path").strip(), (m.group("test") or None)))
        return specs

    def backtick_tokens_in_sections(self, section_names: Optional[List[str]] = None) -> List[str]:
        """Return all backticked tokens from specified sections (defaults to all)."""
        tokens: List[str] = []
        sections = section_names or list(self.sections.keys())
        for name in sections:
            for line in self.sections.get(name, []):
                tokens.extend([tok.strip() for tok in BACKTICK_TOKEN_RE.findall(line)])
        return tokens

    def cli_flags_in_tests(self) -> List[str]:
        """Extract CLI flags (e.g., --hidden, -uu) mentioned in **Tests** lines.

        Matches flags that are backticked or raw text.
        """
        flags: List[str] = []
        for line in self.tests_text:
            # First, capture backticked tokens that are flags
            for tok in BACKTICK_TOKEN_RE.findall(line):
                tok = tok.strip()
                if CLI_FLAG_RE.match(tok):
                    flags.append(tok)
            # Then, capture any raw flags not in backticks
            for m in CLI_FLAG_FINDER_RE.finditer(line):
                flags.append(m.group(1))
        # preserve order; de-duplicate
        seen: set = set()
        unique_flags: List[str] = []
        for f in flags:
            if f not in seen:
                seen.add(f)
                unique_flags.append(f)
        return unique_flags


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
        block_lines = lines[start_line:end_line]
        # parse sections
        section = None
        sections: Dict[str, List[str]] = {
            "Members": [],
            "Contract": [],
            "Triggers": [],
            "Tests": [],
        }
        in_fence = False
        for _j, raw in enumerate(block_lines, start=start_line + 1):
            if raw.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            sm = SECTION_RE.match(raw)
            if sm:
                section = sm.group(1) or sm.group(2)
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


def rule_line_growth(current: str, baseline: Optional[str]) -> List[Message]:
    msgs: List[Message] = []
    if baseline is None:
        msgs.append(Message("INFO", "LineGrowth", "No baseline provided; skipping growth check."))
        return msgs
    delta = len(current) - len(baseline)
    if delta > FAIL_GROWTH:
        msgs.append(
            Message("ERROR", "LineGrowth", f"+{delta} chars exceeds fail threshold {FAIL_GROWTH}")
        )
    elif delta >= WARN_GROWTH:
        msgs.append(Message("WARN", "LineGrowth", f"+{delta} chars ≥ warn threshold {WARN_GROWTH}"))
    else:
        msgs.append(
            Message(
                "INFO",
                "LineGrowth",
                f"+{delta} chars within thresholds (warn={WARN_GROWTH}, fail={FAIL_GROWTH})",
            )
        )
    return msgs


def rule_id_uniqueness(parsed_parities: ParsedParities) -> List[Message]:
    seen: Dict[int, int] = {}
    msgs: List[Message] = []
    for set_id, set_block in parsed_parities.sets.items():
        if set_id in seen:
            msgs.append(
                Message(
                    "ERROR",
                    "IDUniqueness",
                    f"Duplicate Set {set_id} (lines {seen[set_id]} and {set_block.heading_line})",
                )
            )
        else:
            seen[set_id] = set_block.heading_line
    if not msgs:
        msgs.append(Message("INFO", "IDUniqueness", f"{len(seen)} unique Set IDs found"))
    return msgs


def rule_cross_ref(parsed_parities: ParsedParities) -> List[Message]:
    msgs: List[Message] = []
    valid = set(parsed_parities.sets.keys())
    for reference_id, uses in parsed_parities.references.items():
        if reference_id not in valid:
            for line_no, line in uses:
                msgs.append(
                    Message(
                        "ERROR",
                        "CrossRef",
                        f"Reference to Set {reference_id} on line {line_no} is unresolved: {line}",
                    )
                )
    if not msgs:
        msgs.append(Message("INFO", "CrossRef", "All referenced Set IDs resolve"))
    return msgs


def _exists_cwd(p: str) -> bool:
    return (Path.cwd() / p).exists()


def rule_dangling_refs(parsed_parities: ParsedParities) -> List[Message]:
    msgs: List[Message] = []
    missing: List[Tuple[int, str]] = []
    for set_id, set_block in parsed_parities.sets.items():
        for path in set_block.member_paths():
            if not _exists_cwd(path):
                missing.append((set_id, path))
    for set_id, path in missing:
        msgs.append(
            Message(
                "ERROR", "DanglingMembers", f"Set {set_id}: member path not found (CWD): {path}"
            )
        )
    if not msgs:
        msgs.append(
            Message("INFO", "DanglingMembers", "All member file paths exist (relative to CWD)")
        )
    return msgs


def rule_tests(parsed_parities: ParsedParities) -> List[Message]:
    msgs: List[Message] = []
    for set_id, set_block in parsed_parities.sets.items():
        for path, test_name in set_block.test_specs():
            file_path = Path.cwd() / path
            if not file_path.exists():
                msgs.append(Message("ERROR", "Tests", f"Set {set_id}: test file missing: {path}"))
                continue
            if test_name:
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception as e:
                    msgs.append(Message("ERROR", "Tests", f"Set {set_id}: cannot read {path}: {e}"))
                    continue
                if not re.search(rf"\bdef\s+{re.escape(test_name)}\s*\(", text):
                    msgs.append(
                        Message(
                            "ERROR",
                            "Tests",
                            f"Set {set_id}: test function not found: {path}::{test_name}",
                        )
                    )
    if not [m for m in msgs if m.severity == "ERROR"]:
        msgs.append(Message("INFO", "Tests", "All referenced tests/files are present"))
    return msgs


def rule_merge_opportunities(parsed_parities: ParsedParities) -> List[Message]:
    msgs: List[Message] = []
    # Build member sets per set ID
    members: Dict[int, set] = {
        set_id: set(set_block.member_paths()) for set_id, set_block in parsed_parities.sets.items()
    }
    set_ids = sorted(members.keys())
    for i in range(len(set_ids)):
        for j in range(i + 1, len(set_ids)):
            a, b = set_ids[i], set_ids[j]
            A, B = members[a], members[b]
            if not A or not B:
                continue
            intersection = A & B
            if not intersection:
                continue
            jaccard = len(intersection) / len(A | B)
            if len(intersection) >= 2 or jaccard >= 0.5:
                msgs.append(
                    Message(
                        "WARN",
                        "MergeOpportunity",
                        f"Sets {a} and {b} share {len(intersection)} member paths (Jaccard={jaccard:.2f}): {sorted(list(intersection))[:5]}...",
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
        out = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.STDOUT
        )
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
    argument_parser = argparse.ArgumentParser(description="Diagnostics for PARITIES.md")
    # Positional optional: parities path (defaults to PARITIES.md)
    argument_parser.add_argument(
        "parities",
        nargs="?",
        default="PARITIES.md",
        help="Path to PARITIES.md (default: PARITIES.md)",
    )
    # Second positional optional: baseline (commit-ish, rev:path, or file path)
    argument_parser.add_argument(
        "baseline",
        nargs="?",
        help=(
            "Baseline file or git ref. If a path exists on disk, it is read as file. "
            "If it contains a colon, it is treated as 'rev:path'. Otherwise it is a commit-ish and "
            "the same relative path as PARITIES is used. Default: origin/<current-branch>:PARITIES.md"
        ),
    )

    args = argument_parser.parse_args(argv)

    parities_path = Path(args.parities).resolve()
    if not parities_path.exists():
        print(f"[ERROR] Input: file not found: {parities_path}")
        return 2

    current_text = read_file_text(parities_path)

    # Determine baseline text
    baseline_text: Optional[str] = None
    if args.baseline:
        # If baseline is an existing file -> read; elif contains ':' -> treat as rev:path; else treat as rev only
        baseline_path = Path(args.baseline)
        if baseline_path.exists():
            try:
                baseline_text = read_file_text(baseline_path)
            except Exception:
                baseline_text = None
        elif ":" in args.baseline:
            baseline_text = read_git_blob_spec(args.baseline)
        else:
            # treat as rev only
            relative_path = os.path.relpath(parities_path, Path.cwd())
            baseline_text = read_git_blob_rev_path(args.baseline, relative_path)
            if baseline_text is None:
                print(
                    f"[WARN] Baseline: git show {args.baseline}:{relative_path} failed; skipping growth check"
                )
    else:
        # Default: origin/<current-branch>:<relpath>
        branch = git_current_branch() or "HEAD"
        relative_path = os.path.relpath(parities_path, Path.cwd())
        spec = f"origin/{branch}:{relative_path}"
        baseline_text = read_git_blob_spec(spec)
        if baseline_text is None:
            print(f"[WARN] Baseline: git show {spec} failed; skipping growth check")

    parsed_parities = parse_parities(current_text)

    messages: List[Message] = []
    messages += rule_line_growth(current_text, baseline_text)
    messages += rule_id_uniqueness(parsed_parities)
    messages += rule_cross_ref(parsed_parities)
    messages += rule_dangling_refs(parsed_parities)
    messages += rule_tests(parsed_parities)
    messages += rule_merge_opportunities(parsed_parities)

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
