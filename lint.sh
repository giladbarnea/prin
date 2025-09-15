set -uo pipefail
source .common.sh

function main(){
	ensure_uv
	local failures=0
	uv run ruff check . --unsafe-fixes --preview --diff --target-version=py313 || failures=$((failures + 1))
	uv run ruff format . --check --preview --diff --target-version=py313 || failures=$((failures + 1))
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
	return $failures
}


main

