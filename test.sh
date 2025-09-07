#!/usr/bin/env bash
if [[ -t 1 && -t 0 && "$USER" = giladbarnea && "$LOGNAME" = giladbarnea && "$CURSOR_AGENT" != 1 ]]; then
    GITHUB_TOKEN="$(cat ~/.github-token || true)" uv run python -m pytest -s tests --color=yes --code-highlight=yes "$@"
else
    GITHUB_TOKEN="$(cat ~/.github-token || true)" uv run python -m pytest -s tests --color=no --code-highlight=no -vv "$@"
fi
