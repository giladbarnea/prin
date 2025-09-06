import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _ensure_github_token():
    if os.environ.get("GITHUB_TOKEN"):
        return
    token_path = Path.home() / ".github-token"
    try:
        token = token_path.read_text().strip()
    except Exception:
        token = ""
    if token:
        os.environ["GITHUB_TOKEN"] = token

