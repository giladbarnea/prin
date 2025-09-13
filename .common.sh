#!/usr/bin/env bash
# Common functions for the scripts in this repository
set -uo pipefail

function message(){
	local string=$1
	local string_length=${#string}
	if [[ $string_length -gt 80 ]]; then
		string_length=80
	fi
	# Use `--` so printf doesn't parse the format starting with '-' as an option
	local horizontal_line=$(printf -- '-%.0s' $(seq 1 $string_length))
	echo "$horizontal_line"
	echo "$string"
	echo "$horizontal_line"
}

function ensure_uv_installed(){
	local quiet="${1:-false}"
	if [[ "$quiet" == "--quiet" || "$quiet" == "-q" ]]; then
		quiet=true
	fi
	if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
		export PATH="$HOME/.local/bin:$PATH"
	fi
	if ! command -v uv &> /dev/null; then
		message "uv is not installed, installing it with 'curl -LsSf https://astral.sh/uv/install.sh | sh'"
		curl -LsSf https://astral.sh/uv/install.sh | sh
		if ! command -v uv &> /dev/null; then
			message "[ERROR] After installing uv, 'command -v uv' returned a non-zero exit code. uv is probably installed but not in the PATH."
			return 1
		fi
		if ! "$quiet"; then
			message "uv installed and in the PATH"
		fi
	fi
	return 0
}
