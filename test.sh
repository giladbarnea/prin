#!/usr/bin/env bash

main() {
    source .common.sh
    ensure_uv
    export GITHUB_TOKEN="${GITHUB_TOKEN:-$(cat ~/.github-token 2>/dev/null || true)}"
    if [[ -t 1 && -t 0 
        && "$USER" = giladbarnea 
        && "$LOGNAME" = giladbarnea 
        && "$__CFBundleIdentifier" != com.jetbrains.pycharm 
        && -z "$CURSOR_AGENT" 
        && "$TERM_PROGRAM" != vscode 
        && "$VSCODE_INJECTION" != 1
        && -z "$CURSOR_TRACE_ID" ]];
    then
        uv run --with=pytest-clarity,pytest-sugar,pytest-pudb python -m pytest -s tests --color=yes --code-highlight=yes -vv "$@"
    else
        uv run --with=pytest-clarity,pytest-sugar python -m pytest -s tests --color=no --code-highlight=no -vv "$@" 2>&1 | decolor
    fi
}

main "$@"