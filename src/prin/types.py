import inspect
import re
from typing import NewType

TPath = NewType("TPath", str)


class TReCompilable(str):
    """A raw string containing regex syntax which (probably) can be compiled with re.compile. Can only be annointed as such by path_classifier.is_regex."""

    __slots__ = ()


class Glob(str):
    """
    Purely nominal type to enable 'pre-compiling' globs and avoid the classification process.
    Helps disambiguate with e.g. `Glob(".*")`."""

    __slots__ = ()


Pattern = TPath | TReCompilable | re.Pattern | Glob
"""
Pattern is a union of:
- TPath: A string representing a file or directory path. Compiled and matched as regex.
- Glob: A string representing a glob pattern. Matched by `fnmatch`.
- TReCompilable: A raw string containing regex syntax which (probably) can be compiled with re.compile. Can only be annointed as such by path_classifier.is_regex.
- re.Pattern: A compiled regex pattern. Matched by `re.search`.
"""


def _describe_predicate(pred: Pattern) -> str:
    if isinstance(pred, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        return pred
    if isinstance(pred, re.Pattern):
        return pred.pattern
    raise type("ShouldNotHappenError", (Exception,), {})(
        "We no longer support callable predicates. Got: {pred!r}"
    )
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
