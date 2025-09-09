# test_classifier.py
import pytest

# Adjust import path to package module.
from prin.path_classifier import classify_pattern

# --- One focused test per detector pattern ---


def test_anchor_start_caret():
    # ^ at the start
    assert classify_pattern("^foo") == "regex"


def test_anchor_end_dollar():
    # $ at the end
    assert classify_pattern("foo$") == "regex"


def test_unescaped_alternation_bar():
    # Unescaped |
    assert classify_pattern("foo|bar") == "regex"


def test_quantifier_exact_m():
    # {m}
    assert classify_pattern("a{2}") == "regex"


def test_quantifier_m_comma():
    # {m,}
    assert classify_pattern("a{2,}") == "regex"


def test_quantifier_comma_m():
    # {,m}
    assert classify_pattern("a{,3}") == "regex"


def test_quantifier_m_n():
    # {m,n}
    assert classify_pattern("a{2,4}") == "regex"


def test_lookaround_or_inline_flags():
    # (?=...), (?!...), (?:...), (?i)...
    assert classify_pattern("(?=foo)") == "regex"


def test_backreference_decimal():
    # \1..\9 (and beyond)
    assert classify_pattern(r"(a)\1") == "regex"
    assert classify_pattern(r"(abc)\12") == "regex"


def test_regex_shorthands_and_anchors():
    # \d, \D, \s, \S, \w, \W, \b, \B, \A, \Z
    for tok in [r"\d", r"\D", r"\s", r"\S", r"\w", r"\W", r"\b", r"\B", r"\A", r"\Z"]:
        assert classify_pattern(tok) == "regex"


def test_unicode_property_class():
    # \p{...} or \P{...}
    assert classify_pattern(r"\p{L}") == "regex"
    assert classify_pattern(r"\P{Greek}") == "regex"


def test_regex_style_escaped_metachar():
    # Escaped metachars imply regex: \. \+ \* \? \| \( \) \[ \] \{ \}
    assert classify_pattern(r"file\.txt") == "regex"
    assert classify_pattern(r"a\(b\)c") == "regex"
    assert classify_pattern(r"foo\|bar") == "regex"
    assert classify_pattern(r"\[data\]") == "regex"


def test_regexy_parens_with_alternation():
    # Unescaped '(' ... unescaped '|' ... unescaped ')'
    # NOTE: This string also matches the "unescaped |" rule; that's OK—both are valid signals.
    assert classify_pattern("foo(bar|baz)qux") == "regex"

    # Sanity: Escaped '|' inside parens shouldn't trip the parens rule,
    # but still trips "regex-style escapes" due to '\|'.
    assert classify_pattern(r"foo(bar\|baz)qux") == "regex"


# --- Final sanity: common globs should NOT be misclassified ---


@pytest.mark.parametrize(
    "pat",
    [
        "*.py",
        "src/*/test?.txt",
        "[0-9].csv",
        "**/*.md",
        "foo.*",
        "**/foo*bar.txt",
    ],
)
def test_common_globs_not_regex(pat):
    assert classify_pattern(pat) == "glob"


@pytest.mark.parametrize(
    "pat",
    [
        "Report (final).pdf",  # literal parens are fine
        "C++/a+b.txt",  # plus signs as literals
    ],
)
def test_text(pat):
    assert classify_pattern(pat) == "text"
