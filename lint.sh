set -uo pipefail
source .common.sh

function main(){
	ensure_uv_installed
	set -x
	uv run ruff check . --unsafe-fixes --preview
	uv run ruff format . --check --preview
	set +x
}


main

