#!/usr/bin/env bash
set -uo pipefail
source .common.sh

function main(){
    ensure_uv_installed
    set -e
    set -x
    uv run coverage run --source=. -m pytest --no-network "$@"
    uv run coverage report --show-missing
    uv run coverage xml -o coverage.xml
    uv run coverage html --title "${@-coverage}"
}

main
