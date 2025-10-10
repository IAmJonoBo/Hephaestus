#!/bin/bash
# Install and run actionlint for GitHub Actions workflow validation
#
# This script downloads actionlint if not available and runs it on all workflow files.
# actionlint is not a Python package and must be installed separately.

set -euo pipefail

ACTIONLINT_VERSION="1.7.7"
UNAME_OS=$(uname -s)
UNAME_ARCH=$(uname -m)

case "${UNAME_OS}" in
Linux)
  OS_SUFFIX="linux"
  ;;
Darwin)
  OS_SUFFIX="darwin"
  ;;
*)
  echo "Unsupported OS: ${UNAME_OS}" >&2
  exit 1
  ;;
esac

case "${UNAME_ARCH}" in
x86_64)
  ARCH_SUFFIX="amd64"
  ;;
arm64 | aarch64)
  ARCH_SUFFIX="arm64"
  ;;
*)
  echo "Unsupported architecture: ${UNAME_ARCH}" >&2
  exit 1
  ;;
esac

ACTIONLINT_URL="https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_${OS_SUFFIX}_${ARCH_SUFFIX}.tar.gz"
INSTALL_DIR="${HOME}/.local/bin"
ACTIONLINT_BIN="${INSTALL_DIR}/actionlint"

# Create install directory if it doesn't exist
mkdir -p "${INSTALL_DIR}"

CURRENT_BIN=$(command -v actionlint || true)
NEED_INSTALL=true

if [[ -n ${CURRENT_BIN} ]]; then
  if "${CURRENT_BIN}" --version >/dev/null 2>&1; then
    if "${CURRENT_BIN}" --version | grep -q "actionlint v${ACTIONLINT_VERSION}"; then
      ACTIONLINT_BIN="${CURRENT_BIN}"
      NEED_INSTALL=false
    else
      echo "Found actionlint at ${CURRENT_BIN} but need version ${ACTIONLINT_VERSION}; reinstalling..."
    fi
  else
    echo "Found actionlint at ${CURRENT_BIN} but it is not executable; reinstalling..."
  fi
fi

if [[ ${NEED_INSTALL} == true ]]; then
  echo "Installing actionlint ${ACTIONLINT_VERSION} for ${OS_SUFFIX}/${ARCH_SUFFIX}..."

  TEMP_DIR=$(mktemp -d)
  trap 'rm -rf "${TEMP_DIR}"' EXIT

  curl -L "${ACTIONLINT_URL}" -o "${TEMP_DIR}/actionlint.tar.gz"
  tar xzf "${TEMP_DIR}/actionlint.tar.gz" -C "${TEMP_DIR}"

  install -m 755 "${TEMP_DIR}/actionlint" "${ACTIONLINT_BIN}"
  echo "✓ actionlint installed to ${ACTIONLINT_BIN}"
fi

# Run actionlint on workflow files
echo "Running actionlint on workflow files..."
"${ACTIONLINT_BIN}" .github/workflows/*.yml
