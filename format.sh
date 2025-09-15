#!/usr/bin/env bash
set -uo pipefail
source .common.sh

function main(){
	ensure_uv_installed
	set -x
	uv run ruff check . --fix --preview --unsafe-fixes --target-version=py313
	uv run ruff format . --preview --target-version=py313
	set +x
}

main

