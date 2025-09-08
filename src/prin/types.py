import inspect
import os
from typing import Annotated, Callable, NewType

from annotated_types import Predicate
from typeguard import typechecked

from .path_classifier import _is_glob

TPath = NewType("TPath", str)


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
