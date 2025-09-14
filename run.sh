#!/usr/bin/env bash
set -uo pipefail
source .common.sh

function main(){
    ensure_uv_installed
    uv tool run --refresh "$@"
}

main
