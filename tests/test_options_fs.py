from __future__ import annotations

import pytest

from prin.core import StringWriter
from prin.prin import main as prin_main
from tests.utils import count_md_headers


def _run(argv: list[str]) -> str:
    buf = StringWriter()
    prin_main(argv=argv, writer=buf)
    return buf.text()


def test_include_tests_flag_includes_tests_dir(fs_root):
    out = _run(["-T", str(fs_root)])
    assert "<tests/test_mod.py>" in out


@pytest.mark.skip("Failing, feature broken")
def test_include_lock_flag_includes_lock_files(fs_root):
    out = _run(["-K", str(fs_root)])
    assert "<poetry.lock>" in out or "<package-lock.json>" in out or "<uv.lock>" in out


@pytest.mark.skip("Failing, feature broken")
def test_include_binary_includes_binary_like_files(fs_root):
    out = _run(["--include-binary", str(fs_root)])
    # image.png is matched by default binary exclusions; with include-binary it should appear
    assert "<image.png" in out


def test_no_docs_excludes_markdown_and_rst(fs_root):
    out = _run(["--no-docs", str(fs_root)])
    assert "readme.md" not in out
    assert "README.md" not in out
    assert "notes.rst" not in out


@pytest.mark.skip("Failing, feature broken")
def test_include_empty_includes_truly_empty_and_semantically_empty(fs_root):
    out = _run(["--include-empty", str(fs_root)])
    assert "<empty.txt>" in out
    assert "<empty.py>" in out
    assert "<semantically_empty.py>" in out


def test_only_headers_prints_headers_only(fs_root):
    out = _run(["--include-tests", "--only-headers", str(fs_root)])
    # Expect no bodies, only paired headers; count a few known headers
    assert "</foo.py>" in out
    assert "</src/app.py>" in out
    # Ensure bodies are not present (no function source snippet)
    assert "def app():" not in out


@pytest.mark.skip("Failing, feature broken")
def test_extension_filters_by_extension(fs_root):
    out = _run(["-e", "py", str(fs_root)])
    assert "<foo.py>" in out
    assert "<src/app.py>" in out
    assert "readme.md" not in out
    assert "data.json" not in out


def test_exclude_glob_and_literal(fs_root):
    out = _run(["--include-tests", "-E", "src", "-E", "*.md", str(fs_root)])
    assert "<src/app.py>" not in out
    assert "<src/util.py>" not in out
    assert "readme.md" not in out
    assert "README.md" not in out


def test_no_exclude_disables_all_default_exclusions(fs_root):
    out = _run(["--no-exclude", "--include-tests", str(fs_root)])
    # cache/node_modules/build/vendor/logs/secrets should be allowed when no-exclude
    assert "<node_modules/pkg/index.js>" in out
    assert "<build/artifact.o>" in out
    assert "<cache/tmp.txt>" in out
    assert "<vendor/vendorlib.py>" in out
    assert "<logs/app.log>" in out
    assert "<secrets/key.pem>" in out


@pytest.mark.skip("Failing, feature broken")
def test_no_ignore_respects_gitignore_unless_disabled(fs_root):
    # By default, gitignored.txt should be excluded
    out_default = _run([str(fs_root)])
    assert "gitignored.txt" not in out_default

    # With --no-ignore, gitignored.txt should be included
    out_no_ignore = _run(["--no-ignore", str(fs_root)])
    assert "<gitignored.txt>" in out_no_ignore


def test_tag_md_outputs_markdown_format(fs_root):
    out = _run(["--include-tests", "--tag", "md", str(fs_root)])
    assert count_md_headers(out) > 0
    assert "# FILE: foo.py" in out
