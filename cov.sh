#!/usr/bin/env bash

set -e
set -x

# Run tests with coverage, defaulting to skipping network tests. Extra args are forwarded to pytest.
uv run coverage run --source=. -m pytest --no-network "$@"
uv run coverage report --show-missing
uv run coverage xml -o coverage.xml
uv run coverage html --title "${@-coverage}"
