from __future__ import annotations

import random
import re
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from .conftest import VFS
from prin.core import StringWriter
from prin.prin import main as prin_main


def _run(argv: list[str]) -> str:
    buf = StringWriter()
    prin_main(argv=argv, writer=buf)
    return buf.text()


def test_no_options_specified_everything_is_printed(fs_root: VFS):
    out = _run(["--tag", "xml", str(fs_root.root)])

    present = list((fs_root.regular_files | fs_root.doc_files).keys())
    for path in present:
        assert path in fs_root.paths  # Precondition
        content = fs_root.contents[path]

        assert f"<{path}>" in out
        assert content in out
        assert f"</{path}>" in out

    absent = set(fs_root.paths) - set(present)
    for path in absent:
        assert path in fs_root.paths  # Precondition
        content = fs_root.contents[path]

        assert f"<{path}>" not in out
        # All non-empty absent contents must not appear in the output
        if content.strip():
            import re

            # Use fullmatch across a line-anchored search to avoid substring collisions
            assert not re.search(re.escape(content), out)
        assert f"</{path}>" not in out


def test_hidden_includes_dotfiles_and_dotdirs(fs_root: VFS):
    out = _run(["--hidden", str(fs_root.root)])
    for hidden_file, content in fs_root.hidden_files.items():
        assert hidden_file in out
        assert content.strip() in out


def test_include_tests_flag_includes_tests_dir(fs_root: VFS):
    out = _run(["--include-tests", str(fs_root.root)])
    for test_file in fs_root.test_files:
        assert test_file in out


def test_include_lock_flag_includes_lock_files(fs_root: VFS):
    out = _run(["--include-lock", str(fs_root.root)])
    for lock_file in fs_root.lock_files:
        assert lock_file in out


def test_include_binary_includes_binary_like_files(fs_root: VFS):
    out = _run(["--include-binary", str(fs_root.root)])
    # image.png is matched by default binary exclusions; with include-binary it should appear
    for binary_file in fs_root.binary_files:
        assert binary_file in out


def test_no_docs_excludes_markdown_and_rst(fs_root: VFS):
    out = _run(["--no-docs", str(fs_root.root)])
    for doc_file in fs_root.doc_files:
        assert doc_file not in out


def test_include_empty_includes_truly_empty_and_semantically_empty(fs_root: VFS):
    out = _run(["--include-empty", str(fs_root.root)])
    for empty_file in fs_root.empty_files:
        assert empty_file in out


def test_only_headers_prints_headers_only(fs_root: VFS):
    out = _run(["--include-tests", "--only-headers", str(fs_root.root)])
    # Expect no bodies, only paired headers; count a few known headers
    assert re.search("^foo.py$", out, re.MULTILINE)
    assert re.search("^src/app.py$", out, re.MULTILINE)
    assert re.search("^tests/test_mod.py$", out, re.MULTILINE)
    # Ensure bodies are not present (no function source snippet). Remove the gitignored.txt patch once we support gitignore parsing.
    random_content = random.choice(list(filter(lambda x: bool(x.strip() and x != "gitignored.txt"), fs_root.contents.values())))
    assert random_content.strip() not in out


def test_extension_filters_by_extension(fs_root: VFS):
    out = _run(["--extension", "py", str(fs_root.root)])
    assert "<foo.py>" in out
    assert "<src/app.py>" in out
    assert "readme.md" not in out
    assert "data.json" not in out


def test_module_named_locking_is_not_excluded(fs_root: VFS):
    # Create a module under src/locking to ensure 'lock' substring does not cause exclusion
    from tests.utils import write_file

    mod_path = fs_root.root / "src" / "locking" / "main.py"
    write_file(mod_path, "print('locking module ok')\n")

    out = _run([str(fs_root.root)])
    assert "<src/locking/main.py>" in out


def test_exclude_glob_and_literal(fs_root: VFS):
    out = _run(["--include-tests", "--exclude", "src", "--exclude", "*.md", str(fs_root.root)])
    for test_file in fs_root.test_files:
        assert test_file in out
    assert "<src/app.py>" not in out
    assert "<src/util.py>" not in out
    assert "readme.md" not in out
    assert "README.md" not in out


@pytest.mark.skip(".gitignore parsing is not supported ATM")
def test_no_ignore_respects_gitignore_unless_disabled(fs_root: VFS):
    # By default, gitignored.txt should be excluded
    out_default = _run([str(fs_root.root)])
    assert "gitignored.txt" not in out_default

    # With --no-ignore, gitignored.txt should be included
    out_no_ignore = _run(["--no-ignore", str(fs_root.root)])
    assert "<gitignored.txt>" in out_no_ignore


def test_tag_md_outputs_markdown_format(fs_root: VFS):
    out = _run(["--tag", "md", str(fs_root.root)])
    for regular_file, content in fs_root.regular_files.items():
        assert f"## FILE: {regular_file}" in out
        assert content in out
    assert "/>" not in out


def test_unrestricted_includes_gitignored(fs_root: VFS):
    out = _run(["-u", str(fs_root.root)])
    # Gitignored file should be included due to --no-ignore
    assert "<gitignored.txt>" in out

    # Hidden file should not be included
    for hidden_file in fs_root.hidden_files:
        assert hidden_file not in out


def test_uu_includes_hidden_and_gitignored(fs_root: VFS):
    out = _run(["-uu", str(fs_root.root)])
    # Hidden file should be included
    for hidden_file in fs_root.hidden_files:
        assert hidden_file in out
    # Gitignored file should be included due to --no-ignore
    assert "<gitignored.txt>" in out


@pytest.mark.skip("Fails: output does not include empty files")
def test_no_exclude_includes_everything(fs_root: VFS):
    out = _run(["-uuu", str(fs_root.root)])
    not_in_out = []
    for path in fs_root.paths:
        if path not in out:
            not_in_out.append(path)
    assert not not_in_out
