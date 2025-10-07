#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if PROJECT_ROOT=$(cd "${SCRIPT_DIR}" && git rev-parse --show-toplevel 2>/dev/null); then
  PROJECT_ROOT=${PROJECT_ROOT%$'\n'}
else
  PROJECT_ROOT=${SCRIPT_DIR}
fi

if [[ -z ${PROJECT_ROOT} ]]; then
  echo "Unable to determine project root." >&2
  exit 1
fi

cd "${PROJECT_ROOT}" || exit 1

if command -v uv >/dev/null 2>&1; then
  exec uv run hephaestus cleanup "$@"
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="${PROJECT_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

exec "${PYTHON_BIN}" -m hephaestus.cli cleanup "$@"
