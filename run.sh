#!/usr/bin/env bash
# Run prin [args...].
set -euo pipefail
source .common.sh

function main(){
	ensure_uv_installed

	uv tool run --refresh "$@"
}

main "$@"



