#!/usr/bin/env bash
<<<<<<< HEAD
uv tool run --refresh . -- "$@"
=======
set -uo pipefail
source .common.sh

function main(){
    ensure_uv_installed
    uv tool run --refresh "$@"
}

main
>>>>>>> master
