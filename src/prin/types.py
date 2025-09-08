import inspect
import os
from typing import Annotated, Callable, NewType, Literal

from annotated_types import Predicate
from typeguard import typechecked

TPath = NewType("TPath", str)

import re

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

_RE_SIGNS = re.compile(' | '.join(_REGEX_ONLY_PATTERNS), re.VERBOSE)

def classify_pattern(p: str) -> Literal["regex", "glob"]:
    """Return 'regex' if p looks like a regular expression, else 'glob'."""
    return "regex" if _RE_SIGNS.search(p) else "glob"


def _is_glob(path) -> bool:
    if not isinstance(path, str):
        return False
    return any(c in path for c in "*?![]")


def _is_extension(name: str) -> bool:
    return name.startswith(".") and os.path.sep not in name


TGlob = Annotated[NewType("TGlob", str), Predicate(_is_glob)]
TExtension = Annotated[NewType("TExtension", str), Predicate(_is_extension)]

TExclusion = TPath | TGlob | Callable[[TPath | TGlob], bool]
"""
TExclusion is a union of:
- TPath: A string representing a file or directory path. Matches by substring (e.g., "foo/bar" matches "foo/bar/baz").
- TGlob: A string representing a glob pattern.
- Callable[[TPath | TGlob], bool]: A function that takes a TPath or TGlob and returns a boolean.
"""


@typechecked
def _describe_predicate(pred: TExclusion) -> str:
    if isinstance(pred, str):
        return pred

    pred_closure_vars = inspect.getclosurevars(pred)
    if pred_closure_vars.unbound == {"startswith"}:
        startswith = pred.__code__.co_consts[1]
        return f"paths starting with {startswith!r}"
    if pred_closure_vars.unbound == {"endswith"}:
        endswith = pred.__code__.co_consts[1]
        return f"paths ending with {endswith!r}"
    if " in " in inspect.getsource(pred):
        contains = pred.__code__.co_consts[1]
        return f"paths containing {contains!r}"
    msg = f"Unknown predicate: {pred}"
    raise ValueError(msg)
