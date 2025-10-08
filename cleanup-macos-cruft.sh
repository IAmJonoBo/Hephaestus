#!/usr/bin/env bash
set -euo pipefail

MACOS_PATTERNS=(
  ".DS_Store"
  "._*"
  ".AppleDouble"
  ".AppleDesktop"
  ".AppleDB"
  "Icon?"
  "__MACOSX"
  ".DocumentRevisions-V100"
  ".Spotlight-V100"
  ".Trashes"
  ".fseventsd"
  ".TemporaryItems"
  ".LSOverride"
  ".apdisk"
)

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

ARGS=("$@")

VALUE_FLAGS=(
  "--log-format"
  "--log-level"
  "--run-id"
  "--extra-path"
  "--audit-manifest"
)

should_inject_root=true
i=0
while [[ ${i} -lt ${#ARGS[@]} ]]; do
  arg="${ARGS[$i]}"
  if [[ ${arg} == "--" ]]; then
    if [[ ${i} -lt $((${#ARGS[@]} - 1)) ]]; then
      should_inject_root=false
    fi
    break
  fi
  if [[ ${arg} == -* ]]; then
    flag_name="${arg%%=*}"
    for value_flag in "${VALUE_FLAGS[@]}"; do
      if [[ ${flag_name} == "${value_flag}" ]]; then
        if [[ ${arg} != *=* ]]; then
          ((i++))
        fi
        break
      fi
    done
  else
    should_inject_root=false
    break
  fi
  ((i++))
done

if [[ ${should_inject_root} == true ]]; then
  ARGS=("${PROJECT_ROOT}" "${ARGS[@]}")
fi

flag_present() {
  local flag="$1"
  for arg in "${ARGS[@]}"; do
    if [[ ${arg} == "${flag}" ]]; then
      return 0
    fi
  done
  return 1
}

has_deep_clean=false
for arg in "${ARGS[@]}"; do
  if [[ ${arg} == "--deep-clean" ]]; then
    has_deep_clean=true
    break
  fi
done

if [[ ${has_deep_clean} != true ]]; then
  set +e
  flag_present "--include-git"
  git_present=$?
  flag_present "--include-poetry-env"
  env_present=$?
  set -e

  if [[ ${git_present} -ne 0 ]]; then
    ARGS+=("--include-git")
  fi
  if [[ ${env_present} -ne 0 ]]; then
    ARGS+=("--include-poetry-env")
  fi
fi

unlock_apple_metadata() {
  local root="$1"
  if [[ ${OSTYPE} != darwin* ]]; then
    return 0
  fi
  if ! command -v chflags >/dev/null 2>&1; then
    return 0
  fi
  if ! command -v find >/dev/null 2>&1; then
    return 0
  fi

  local expr=()
  for pattern in "${MACOS_PATTERNS[@]}"; do
    if [[ ${#expr[@]} -gt 0 ]]; then
      expr+=(-o)
    fi
    expr+=(-name "${pattern}")
  done
  if [[ ${#expr[@]} -eq 0 ]]; then
    return 0
  fi

  find "${root}" '(' "${expr[@]}" ')' -exec chflags nouchg,noschg {} + 2>/dev/null || true
  if command -v xattr >/dev/null 2>&1; then
    find "${root}" '(' "${expr[@]}" ')' -exec xattr -c {} + 2>/dev/null || true
  fi
}

unlock_apple_metadata "${PROJECT_ROOT}"

if command -v uv >/dev/null 2>&1; then
  exec uv run hephaestus cleanup "${ARGS[@]}"
fi

if command -v hephaestus >/dev/null 2>&1; then
  exec hephaestus cleanup "${ARGS[@]}"
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="${PROJECT_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

exec "${PYTHON_BIN}" -m hephaestus.cli cleanup "${ARGS[@]}"
