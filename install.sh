#!/usr/bin/env bash
set -euo pipefail
source .common.sh

function main(){
	ensure_uv_installed

	message "Installing prin..."
	uv tool --no-cache install --refresh . --reinstall
	message "prin installed. Usage:"
	prin --help
}

main