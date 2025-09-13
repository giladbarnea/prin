#!/usr/bin/env python3
"""
parities_check.py — Interactive/CI diagnostics for PARITIES.md

Rules implemented (configurable severities via constants):
- Line-growth gate: WARN if growth > FAIL_GROWTH (20 chars), SUGGESTION if growth ≥ WARN_GROWTH (5 chars).
- ID uniqueness: warn on duplicate Set IDs.
- Cross-ref integrity: warn if any referenced "Set <ID>" (outside headings) does not exist.
- Dangling references: warn if any **Members** file path does not exist (relative to CWD).
- Test presence (unified reference check): for each **Tests** entry like
  "path/to/test_file.py::test_name", warn if the file is missing or if the
  test function is not present; if only a file is given, warn if missing.
- Merge opportunities (heuristic): SUGGESTION when two sets share ≥2 member paths or
  Jaccard similarity ≥ 0.5 (Members only). This is advisory.

Usage examples:
    # Default PARITIES and baseline = origin/<current-branch>:PARITIES.md
    python tools/parities_check.py

    # Explicit PARITIES, baseline from a commit-ish (uses same relative path)
    python tools/parities_check.py PARITIES.md abc1234

    # Explicit PARITIES and a baseline file on disk
    python tools/parities_check.py docs/PARITIES.md /tmp/old_PARITIES.md

Exit code: non-zero if any WARN was emitted.
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

GLOB_CHARS_RE = re.compile(r"[\*\?\[]")


def normalize_symbol_token(token: str) -> str:
    """
    Normalize a backticked token for AST resolution.

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
    """
    Extract and normalize tokens from **Members** lines suitable for AST lookup.

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


def extract_constant_tokens_from_members(member_lines: List[str]) -> List[str]:
    """
    Extract constant-like tokens (e.g., DEFAULT_*, DEFAULT_TAG_CHOICES) from Members lines.

    - Includes ALL_CAPS tokens and wildcard constant patterns like DEFAULT_*.
    - Excludes file-like tokens.
    """
    constants: List[str] = []
    for line in member_lines:
        for raw in BACKTICK_TOKEN_RE.findall(line):
            token = raw.strip()
            if LIKELY_FILE_RE.search(token) or token in {"README.md", "LICENSE"}:
                continue
            if "*" in token or re.fullmatch(r"[A-Z0-9_]+", token):
                constants.append(token)
    # preserve order, de-duplicate
    seen: set = set()
    unique_constants: List[str] = []
    for c in constants:
        if c not in seen:
            seen.add(c)
            unique_constants.append(c)
    return unique_constants


def _is_file_like_token(token: str) -> bool:
    """
    Heuristic for file-like tokens.

    Rules:
    - Exact names like README.md and LICENSE are accepted.
    - Bare filenames with known extensions must have no whitespace.
    - Slash-based paths must have no whitespace and not look like CLI flag pairs.
    - Excludes pytest specs containing '::'.
    """
    t = token.strip()
    if "::" in t:
        return False
    if t in {"README.md", "LICENSE"}:
        return True
    # Bare filename with extension
    if re.fullmatch(
        r"\S+\.(py|md|rst|txt|json|jsonl|toml|yaml|yml|ini|cfg|lock|rs|ts|tsx|js|jsx|sh|bat|conf|mdx)",
        t,
        flags=re.IGNORECASE,
    ):
        return True
    # Slash-based path with no whitespace
    if "/" in t and not re.search(r"\s", t):
        # Guard against combined CLI flags like -f/--foo
        parts = re.split(r"/", t)
        if parts and all(not CLI_FLAG_RE.match(p or "") for p in parts):
            return True
    return False


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
                # If this looks like a pytest spec (contains ::), don't treat as a file path here
                if "::" in tok:
                    continue
                # Skip CLI flags accidentally included in Members
                if CLI_FLAG_RE.match(tok):
                    continue
                # Skip combined CLI flags like "-l/--only-headers" or with commas
                if "/" in tok or "," in tok:
                    parts = re.split(r"\s*[/,]\s*", tok)
                    if parts and all(CLI_FLAG_RE.match(p.strip() or "") for p in parts):
                        continue
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

    def _extract_cli_flags_from_lines(self, lines: List[str]) -> List[str]:
        flags: List[str] = []
        separators = re.compile(r"\s*[/,]\s*")

        def _add_from_token(token: str) -> None:
            t = token.strip()
            if t.startswith("(") and t.endswith(")"):
                t = t[1:-1].strip()
            if t.startswith("`") and t.endswith("`") and len(t) >= 2:
                t = t[1:-1].strip()
            if CLI_FLAG_RE.match(t):
                flags.append(t)
                return
            for part in separators.split(t):
                part = part.strip()
                if CLI_FLAG_RE.match(part):
                    flags.append(part)

        for line in lines:
            # capture backticked flags (single or combined)
            for tok in BACKTICK_TOKEN_RE.findall(line):
                _add_from_token(tok)
            # capture raw flags
            for m in CLI_FLAG_FINDER_RE.finditer(line):
                flags.append(m.group(1))
        # de-duplicate preserving order
        seen: set = set()
        uniq: List[str] = []
        for f in flags:
            if f not in seen:
                seen.add(f)
                uniq.append(f)
        return uniq

    def cli_flags_all_sections(self) -> List[str]:
        # Flatten all section lines
        lines: List[str] = []
        for name in self.sections:
            lines.extend(self.sections.get(name, []))
        return self._extract_cli_flags_from_lines(lines)

    def cli_flags_in_tests(self) -> List[str]:
        return self._extract_cli_flags_from_lines(self.tests_text)

    def pytest_specs_all_sections(self) -> List[Tuple[str, Optional[str]]]:
        specs: List[Tuple[str, Optional[str]]] = []
        lines: List[str] = []
        for name in self.sections:
            lines.extend(self.sections.get(name, []))
        for line in lines:
            toks = BACKTICK_TOKEN_RE.findall(line) or [line]
            for tok in toks:
                tok = tok.strip()
                m = TEST_SPEC_RE.match(tok)
                if m and m.group("test"):
                    specs.append((m.group("path").strip(), m.group("test")))
        # de-dup
        seen: set = set()
        uniq: List[Tuple[str, Optional[str]]] = []
        for p in specs:
            if p not in seen:
                seen.add(p)
                uniq.append(p)
        return uniq

    def file_paths_all_sections(self) -> List[str]:
        """
        Collect file-like tokens from all sections (backticked or raw) excluding CLI flags and pytest specs.

        Recognizes file tokens by extension or presence of path separators, plus special names like README.md.
        """
        paths: List[str] = []
        lines: List[str] = []
        for name in self.sections:
            lines.extend(self.sections.get(name, []))

        def _maybe_add(token: str) -> None:
            t = token.strip()
            if _is_file_like_token(t):
                paths.append(t)

        for line in lines:
            toks = BACKTICK_TOKEN_RE.findall(line)
            if toks:
                for tok in toks:
                    _maybe_add(tok)
            else:
                _maybe_add(line)
        # de-dup preserving order
        seen: set = set()
        uniq: List[str] = []
        for p in paths:
            if p not in seen:
                seen.add(p)
                uniq.append(p)
        return uniq


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
            Message("WARN", "LineGrowth", f"+{delta} chars exceeds fail threshold {FAIL_GROWTH}")
        )
    elif delta >= WARN_GROWTH:
        msgs.append(
            Message("SUGGESTION", "LineGrowth", f"+{delta} chars ≥ warn threshold {WARN_GROWTH}")
        )
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
                    "WARN",
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
                        "WARN",
                        "CrossRef",
                        f"Reference to Set {reference_id} on line {line_no} is unresolved: {line}",
                    )
                )
    if not msgs:
        msgs.append(Message("INFO", "CrossRef", "All referenced Set IDs resolve"))
    return msgs


def _exists_cwd(p: str) -> bool:
    return (Path.cwd() / p).exists()


def _exists_cwd_or_glob(p: str) -> bool:
    """Return True if the given path exists or if a glob pattern matches any files."""
    # Fast path: exact exists
    if _exists_cwd(p):
        return True
    # If looks like a glob, try globbing relative to CWD
    if GLOB_CHARS_RE.search(p):
        from glob import glob

        matches = glob(str(Path.cwd() / p))
        return len(matches) > 0
    # If it's a bare filename with extension, search recursively under CWD
    if re.fullmatch(
        r"\S+\.(py|md|rst|txt|json|jsonl|toml|yaml|yml|ini|cfg|lock|rs|ts|tsx|js|jsx|sh|bat|conf|mdx)",
        p,
        flags=re.IGNORECASE,
    ):
        from glob import glob

        matches = glob(str(Path.cwd() / "**" / p), recursive=True)
        return len(matches) > 0
    return False


def rule_dangling_refs(parsed_parities: ParsedParities) -> List[Message]:
    msgs: List[Message] = []
    missing: List[Tuple[int, str]] = []
    for set_id, set_block in parsed_parities.sets.items():
        for path in set_block.file_paths_all_sections():
            if not _exists_cwd_or_glob(path):
                missing.append((set_id, path))
    for set_id, path in missing:
        msgs.append(
            Message("WARN", "DanglingMembers", f"Set {set_id}: member path not found (CWD): {path}")
        )
    if not msgs:
        msgs.append(
            Message("INFO", "DanglingMembers", "All member file paths exist (relative to CWD)")
        )
    return msgs


def rule_tests(parsed_parities: ParsedParities) -> List[Message]:
    msgs: List[Message] = []
    for set_id, set_block in parsed_parities.sets.items():
        # Accept pytest specs from any section
        for path, test_name in set_block.pytest_specs_all_sections():
            file_path = Path.cwd() / path
            # Allow glob patterns for test files; if present, succeed on any match
            if GLOB_CHARS_RE.search(path):
                from glob import glob

                matches = glob(str(file_path))
                if not matches:
                    msgs.append(
                        Message("WARN", "Tests", f"Set {set_id}: test file missing: {path}")
                    )
                continue
            if not file_path.exists():
                msgs.append(Message("WARN", "Tests", f"Set {set_id}: test file missing: {path}"))
                continue
            if test_name:
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception as e:
                    msgs.append(Message("WARN", "Tests", f"Set {set_id}: cannot read {path}: {e}"))
                    continue
                if not re.search(rf"\bdef\s+{re.escape(test_name)}\s*\(", text):
                    msgs.append(
                        Message(
                            "WARN",
                            "Tests",
                            f"Set {set_id}: test function not found: {path}::{test_name}",
                        )
                    )
    if not [m for m in msgs if m.severity == "WARN"]:
        msgs.append(Message("INFO", "Tests", "All referenced tests/files are present"))
    return msgs


def rule_merge_opportunities(parsed_parities: ParsedParities) -> List[Message]:
    msgs: List[Message] = []
    # Compare Set title IDs only: e.g., [CLI-CTX-DEFAULTs-README] → parts: {CLI, CTX, DEFAULTs, README}
    id_parts: Dict[int, set] = {}
    for sid, block in parsed_parities.sets.items():
        m = re.search(r"\[(?P<id>[^\]]+)\]", block.title)
        if not m:
            continue
        parts = [p.casefold() for p in re.split(r"-+", m.group("id")) if p]
        id_parts[sid] = set(parts)

    set_ids = sorted(id_parts.keys())
    for i in range(len(set_ids)):
        for j in range(i + 1, len(set_ids)):
            a, b = set_ids[i], set_ids[j]
            A, B = id_parts[a], id_parts[b]
            if not A or not B:
                continue
            shared = A & B
            if len(shared) >= 2:
                msgs.append(
                    Message(
                        "SUGGESTION",
                        "MergeOpportunity",
                        f"Sets {a} and {b} share {len(shared)} ID parts: {sorted(shared)}",
                    )
                )
    if not [m for m in msgs if m.severity == "SUGGESTION"]:
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
        print(f"[WARN] Input: file not found: {parities_path}")
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
                    f"[SUGGESTION] Baseline: git show {args.baseline}:{relative_path} failed; skipping growth check"
                )
    else:
        # Default: origin/<current-branch>:<relpath>
        branch = git_current_branch() or "HEAD"
        relative_path = os.path.relpath(parities_path, Path.cwd())
        spec = f"origin/{branch}:{relative_path}"
        baseline_text = read_git_blob_spec(spec)
        if baseline_text is None:
            print(f"[SUGGESTION] Baseline: git show {spec} failed; skipping growth check")

    parsed_parities = parse_parities(current_text)

    messages: List[Message] = []
    messages += rule_line_growth(current_text, baseline_text)
    messages += rule_id_uniqueness(parsed_parities)
    messages += rule_cross_ref(parsed_parities)
    messages += rule_dangling_refs(parsed_parities)
    messages += rule_tests(parsed_parities)
    messages += rule_merge_opportunities(parsed_parities)

    # Print grouped output
    severity_order = {"WARN": 0, "SUGGESTION": 1, "INFO": 2}
    messages.sort(key=lambda m: (severity_order.get(m.severity, 3), m.rule))
    has_error = False
    for m in messages:
        print(str(m))
        if m.severity == "WARN":
            has_error = True

    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
