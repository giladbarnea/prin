#!/usr/bin/env bash
set -uo pipefail
source .common.sh

function main(){
    ensure_uv_installed
    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        export GITHUB_TOKEN="$(cat ~/.github-token 2>/dev/null || true)"
    fi
    if [[ -t 1 && -t 0 \
        && "$USER" = giladbarnea \
        && "$LOGNAME" = giladbarnea \
        && "$__CFBundleIdentifier" != com.jetbrains.pycharm \
        && -z "$CURSOR_AGENT" \
        && "$TERM_PROGRAM" != vscode \
        && "$VSCODE_INJECTION" != 1 \
        && -z "$CURSOR_TRACE_ID" ]];
    then
        uv run python -m pytest -s tests --color=yes --code-highlight=yes -vv "$@"
    else
        uv run python -m pytest -s tests --color=no --code-highlight=no -vv "$@"
    fi
}

main
