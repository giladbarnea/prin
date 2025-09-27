#!/usr/bin/env bash
set -o pipefail

function main(){
    source .common.sh
    ensure_uv
    set -e
    set -x
    uv run coverage run --source=. -m pytest tests
    uv run coverage report --show-missing
    uv run coverage xml -o coverage.xml
    uv run coverage html --title "${@-coverage}"
}

main
