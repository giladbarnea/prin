import contextlib
import re
from re import Pattern
from typing import Literal, TypeIs

from prin.types import Glob, TReCompilable

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

_RE_SIGNS: Pattern[str] = re.compile(" | ".join(_REGEX_ONLY_PATTERNS), re.VERBOSE)


def classify_pattern(pattern) -> Literal["regex", "glob"]:
    """Return pattern kind: glob if it looks like a glob, else regex by default."""
    if is_glob(pattern):
        return "glob"
    return "regex"


def is_regex(pattern) -> TypeIs[TReCompilable]:
    if isinstance(pattern, (re.Pattern, TReCompilable)):
        return True
    if isinstance(pattern, Glob):
        return False
    if not isinstance(pattern, str):
        return False
    return bool(_RE_SIGNS.search(pattern))


def is_glob(pattern) -> TypeIs[Glob]:
    if isinstance(pattern, Glob):
        return True
    if not isinstance(pattern, str):
        return False
    if isinstance(pattern, TReCompilable) or is_regex(pattern):
        return False
    return any(glob_sym in pattern for glob_sym in "*?[")


def is_extension(pattern) -> TypeIs[Glob]:
    if isinstance(pattern, (re.Pattern, TReCompilable)):
        raise NotImplementedError(
            "We should theoretically be able to check if a regex is an extension, but we don't yet. Got: {string!r}"
        )
    if not isinstance(pattern, str):
        return False
    from prin.cli_common import _normalize_extension_to_glob

    with contextlib.suppress(ValueError):
        return pattern == _normalize_extension_to_glob(pattern)
    return False
