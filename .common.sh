#!/usr/bin/env bash
# Common functions for the scripts in this repository
set -o pipefail

decolor () {
    local text="${1:-$(cat /dev/stdin)}"
    # Remove ANSI color codes step by step using basic bash parameter expansion
    # Remove escape sequences like \033[0m, \033[31m, \033[1;31m, etc.
    
    # Remove \033[*m patterns (any characters between [ and m)
    while [[ "$text" == *$'\033['*m* ]]; do
        text="${text//$'\033['*m/}"
    done
    
    # Also handle \e[*m patterns (alternative escape sequence format)
    while [[ "$text" == *$'\e['*m* ]]; do
        text="${text//$'\e['*m/}"
    done
    
    echo -n "$text"
}

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

# # ensure_uv [-q,-quiet]
function ensure_uv(){
	local quiet=false
	if [[ "$1" == "--quiet" || "$1" == "-q" ]]; then
		quiet=true
	fi
	if [[ ":${PATH:_}:" != *":$HOME/.local/bin:"* ]]; then
		export PATH="$HOME/.local/bin:$PATH"
	fi
	if ! command -v uv 2>&1 1>/dev/null; then
		message "uv is not installed, installing it with 'curl -LsSf https://astral.sh/uv/install.sh | sh'"
		curl -LsSf https://astral.sh/uv/install.sh | sh
		if ! command -v uv 2>&1 1>/dev/null; then
			message "[ERROR] After installing uv, 'command -v uv' returned a non-zero exit code. uv is probably installed but not in the PATH."
			return 1
		fi
		if ! "$quiet"; then
			message "uv installed and in the PATH"
		fi
	fi
	return 0
}
