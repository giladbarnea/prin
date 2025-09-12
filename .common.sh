#!/usr/bin/env sh
# Common functions for the scripts in this repository
set -eu

message(){
	string=$1
	string_length=${#string}
	if [ "$string_length" -gt 80 ]; then
		string_length=80
	fi
	# Use `--` so printf doesn't parse the format starting with '-' as an option
	horizontal_line=$(printf -- '-%.0s' $(seq 1 $string_length))
	echo "$horizontal_line"
	echo "$string"
	echo "$horizontal_line"
}

ensure_uv_installed(){
	quiet="${1:-false}"
	if [ "$quiet" = "--quiet" ] || [ "$quiet" = "-q" ]; then
		quiet=true
	fi
	case ":$PATH:" in
	*":"$HOME/.local/bin":*) ;;
	*) export PATH="$HOME/.local/bin:$PATH" ;;
	esac
	if ! command -v uv >/dev/null 2>&1; then
		message "uv is not installed, installing it with 'curl -LsSf https://astral.sh/uv/install.sh | sh'"
		curl -LsSf https://astral.sh/uv/install.sh | sh
		if ! command -v uv >/dev/null 2>&1; then
			message "[ERROR] After installing uv, 'command -v uv' returned a non-zero exit code. uv is probably installed but not in the PATH."
			return 1
		fi
		if [ "$quiet" != "true" ]; then
			message "uv installed and in the PATH"
		fi
	fi
	return 0
}
