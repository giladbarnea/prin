from __future__ import annotations

import contextlib
import functools
import inspect
from typing import Any, Callable, Iterable, TypeVar, cast

from prin.adapters import github


def is_github_url(token: str) -> bool:
    try:
        # Accept common GitHub hosts/forms, including raw and ssh
        hostish = (
            ("github.com" in token)
            or ("raw.githubusercontent.com" in token)
            or token.startswith("git@github.com:")
        )
        return bool(hostish and github.parse_github_url(token))
    except ValueError:
        return False


def is_http_url(token: str) -> bool:
    tok = token.strip().lower()
    return tok.startswith("http://") or tok.startswith("https://") or tok.startswith("www")


def find_github_url(argv: Iterable[str]) -> tuple[int, str] | None:
    for i, tok in enumerate(argv):
        if is_github_url(tok):
            return i, tok
    return None


# ---[ Functional ]---


F = TypeVar("F", bound=Callable[..., Any])


def _assigned_defaults() -> tuple[str, ...]:
    base = getattr(
        functools,
        "WRAPPER_ASSIGNMENTS",
        ("__module__", "__name__", "__qualname__", "__doc__", "__annotations__", "__type_params__"),
    )
    extra = ("__defaults__", "__kwdefaults__", "__text_signature__")
    # dedupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for x in (*base, *extra):
        if x not in seen:
            seen.add(x)
            out.append(x)
    return tuple(out)


def wraps(
    wrapped: F,
    assigned: tuple[str, ...] = _assigned_defaults(),
    updated: tuple[str, ...] = ("__dict__",),
    copy_signature: bool = True,
) -> Callable[[F], F]:
    """
    A typed drop-in for functools.wraps, using wrapt if available.
    Returns a decorator that accepts a wrapper of the same callable type as `wrapped`
    and returns a callable of that same type.
    """
    try:
        import wrapt  # type: ignore[import-not-found]

        use_wrapt = True
    except Exception:
        use_wrapt = False

    if not use_wrapt:
        # functools-only fallback that still preserves types and metadata
        def decorator(user_wrapper: F) -> F:
            wrapped_wrapper: F = functools.update_wrapper(
                user_wrapper, wrapped, assigned=assigned, updated=updated
            )
            if copy_signature:
                with contextlib.suppress(ValueError, TypeError):
                    # __signature__ is set at runtime only; ignore attr checkers
                    setattr(wrapped_wrapper, "__signature__", inspect.signature(wrapped))
            return wrapped_wrapper

        return decorator

    # wrapt path
    def decorator(user_wrapper: F) -> F:
        @wrapt.decorator
        def _wrapt_deco(_wrapped, instance, args, kwargs):
            # Inject instance for methods/classmethods; omit for functions/staticmethods.
            if instance is None:
                return user_wrapper(*args, **kwargs)
            else:
                return user_wrapper(instance, *args, **kwargs)

        result = cast(F, _wrapt_deco(wrapped))
        functools.update_wrapper(result, wrapped, assigned=assigned, updated=updated)
        if copy_signature:
            with contextlib.suppress(ValueError, TypeError):
                setattr(result, "__signature__", inspect.signature(wrapped))
        return result

    return decorator
