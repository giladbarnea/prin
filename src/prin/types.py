import inspect
from typing import Callable, NewType

TPath = NewType("TPath", str)


TGlob = NewType("TGlob", str)  # Extensions are normalized to globs
TRegex = NewType("TRegex", str)

TExclusion = TPath | TGlob | Callable[[TPath | TGlob], bool]
"""
TExclusion is a union of:
- TPath: A string representing a file or directory path. Matches by substring (e.g., "foo/bar" matches "foo/bar/baz").
- TGlob: A string representing a glob pattern.
- Callable[[TPath | TGlob], bool]: A function that takes a TPath or TGlob and returns a boolean.
"""


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
