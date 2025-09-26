#!/usr/bin/env bash

main() {
  source .common.sh
  ensure_uv
  if [[ -t 1 && -t 0 &&
    "$USER" = giladbarnea &&
    "$LOGNAME" = giladbarnea &&
    "$__CFBundleIdentifier" != com.jetbrains.pycharm &&
    -z "$CURSOR_AGENT" &&
    "$TERM_PROGRAM" != vscode &&
    "$VSCODE_INJECTION" != 1 &&
    -z "$CURSOR_TRACE_ID" ]]; then
    uv run python -m prin.prin "$@"
  else
    uv run python -m prin.prin "$@" 2>&1 | decolor
  fi
}

main "$@"
