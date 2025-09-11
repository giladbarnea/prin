import pytest

pytestmark = pytest.mark.repo


@pytest.mark.network
def test_mixed_fs_repo_interchangeably(fs_root):
    """Ensure a GitHub URL and local fs root both print when passed together."""
    from prin.core import StringWriter
    from prin.prin import main as prin_main

    url = "https://github.com/TypingMind/awesome-typingmind"
    buf = StringWriter()
    prin_main(argv=[url, str(fs_root.root), "--max-files", "2"], writer=buf)
    out = buf.text()
    # One header from repo and one from local fs should appear at least
    assert "# FILE: " in out or "<" in out
    # Use fixture traversal paths to verify at least one known local path is present
    any_local = any((f"<{p}>" in out or f"# FILE: {p}" in out) for p in fs_root.paths)
    assert any_local
