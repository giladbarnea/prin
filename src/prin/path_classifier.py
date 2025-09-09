import os
import re
from typing import Literal, TypeIs

from prin.types import TExtension, TGlob, TRegex

# Each entry is a *single* regex that indicates "this looks like a regex, not a Python glob".
# We join them with ' | ' and compile with re.VERBOSE for readability.
_REGEX_ONLY_PATTERNS = [
    # ^ anchor at the start
    r"^\^",
    # $ anchor at the end
    r"\$$",
    # Unescaped alternation bar anywhere
    r"(?<!\\)\|",
    # Quantifier {m}
    r"(?<!\\)\{\d+\}",
    # Quantifier {m,}
    r"(?<!\\)\{\d+,\}",
    # Quantifier {,m}  (PCRE-style; not Python 're', but still "regex intent")
    r"(?<!\\)\{,\d+\}",
    # Quantifier {m,n}
    r"(?<!\\)\{\d+,\d+\}",
    # Lookarounds / non-capturing / inline flags: (?=  (?!  (?:  (?i  ...
    r"\(\?",
    # Backreferences like \1, \2, ... (allow multi-digit)
    r"\\[1-9]\d*",
    # Regex shorthands & anchors: \d \D \s \S \w \W \b \B \A \Z
    r"\\[dDsSwWbBAAzZ]",
    # Unicode property classes: \p{...} or \P{...}
    r"\\[pP]\{[^}]+\}",
    # Regex-style escapes of metacharacters: \. \+ \* \? \| \( \) \[ \] \{ \}
    r"\\[.^$|?*+()[\]{}]",
    # REGEXY PARENS: unescaped '(' ... (contains an unescaped '|') ... unescaped ')'
    # This is deliberately careful about ignoring escaped '|' and '\)'.
    r"(?<!\\)\((?:\\.|[^\\)])*?(?<!\\)\|(?:\\.|[^\\)])*?(?<!\\)\)",
]

_RE_SIGNS = re.compile(" | ".join(_REGEX_ONLY_PATTERNS), re.VERBOSE)


def classify_pattern(string: str) -> Literal["regex", "glob", "text"]:
    # Should model fd regarding patterns that are neither regexes nor globs.
    # ❯ fd '*.md' .
    # [fd error]: regex parse error:
    # *.md
    # ^
    # error: repetition operator missing expression
    if is_regex(string):
        return "regex"
    if is_glob(string):
        return "glob"
    return "text"


def is_regex(string) -> TypeIs[TRegex]:
    if not isinstance(string, str):
        return False
    return bool(_RE_SIGNS.search(string))


def is_glob(string) -> TypeIs[TGlob]:
    if not isinstance(string, str):
        return False
    if is_regex(string):
        return False
    return any(glob_sym in string for glob_sym in "*?[")


def is_extension(string) -> TypeIs[TExtension]:
    if not isinstance(string, str):
        return False
    return string.startswith(".") and os.path.sep not in string
