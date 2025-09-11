set -uo pipefail
source .common.sh

function main(){
	ensure_uv_installed
	set -x
	uv run ruff check . --unsafe-fixes --preview
	uv run ruff format . --check --preview
	set +x
	uv run --with=mypy mypy src 2>&1 \
		| grep -v -F \
			-e '[list-item]' \
			-e '[var-annotated]' \
			-e '[assignment]' \
			-e '[arg-type]' \
			-e '[import-untyped]' \
			-e ': note: ' \
			-e '[return-value]' \
			-e '[func-returns-value]'
}


main

