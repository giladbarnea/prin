#!/usr/bin/env bash
set -uo pipefail
source .common.sh

function main(){
	ensure_uv_installed
	set -x
	uv run ruff check . --fix --preview --unsafe-fixes
	uv run ruff format . --preview
	set +x
}

main

