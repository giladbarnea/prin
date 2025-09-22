#!/usr/bin/env bash
set -eo pipefail
source .common.sh

function main(){
	ensure_uv

	message "Installing prin..."
	uv tool --no-cache install --refresh . --reinstall
	message "prin installed. Usage:"
	prin --help
}

main