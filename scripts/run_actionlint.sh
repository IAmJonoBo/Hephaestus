#!/bin/bash
# Install and run actionlint for GitHub Actions workflow validation
#
# This script downloads actionlint if not available and runs it on all workflow files.
# actionlint is not a Python package and must be installed separately.
# Features auto-remediation and resilient error handling.

set -euo pipefail

ORIGINAL_DIR=$(pwd)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel 2>/dev/null || dirname "${SCRIPT_DIR}")

cd "${REPO_ROOT}"
trap 'cd "${ORIGINAL_DIR}"' EXIT

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_status() {
  echo -e "${CYAN}→${NC} $1"
}

print_success() {
  echo -e "${GREEN}✓${NC} $1"
}

print_error() {
  echo -e "${RED}✗${NC} $1" >&2
}

print_warning() {
  echo -e "${YELLOW}⚠${NC} $1"
}

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
  print_error "Unsupported OS: ${UNAME_OS}"
  echo "  Supported: Linux, Darwin (macOS)"
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
  print_error "Unsupported architecture: ${UNAME_ARCH}"
  echo "  Supported: x86_64, arm64, aarch64"
  exit 1
  ;;
esac

ACTIONLINT_URL="https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_${OS_SUFFIX}_${ARCH_SUFFIX}.tar.gz"
INSTALL_DIR="${HOME}/.local/bin"
ACTIONLINT_BIN="${INSTALL_DIR}/actionlint"

# Create install directory if it doesn't exist
mkdir -p "${INSTALL_DIR}"

print_status "Checking for actionlint..."

CURRENT_BIN=$(command -v actionlint || true)
NEED_INSTALL=true

if [[ -n ${CURRENT_BIN} ]]; then
  if "${CURRENT_BIN}" --version >/dev/null 2>&1; then
    if "${CURRENT_BIN}" --version | grep -q "actionlint v${ACTIONLINT_VERSION}"; then
      ACTIONLINT_BIN="${CURRENT_BIN}"
      NEED_INSTALL=false
      print_success "actionlint ${ACTIONLINT_VERSION} found at ${CURRENT_BIN}"
    else
      print_warning "Found actionlint at ${CURRENT_BIN} but need version ${ACTIONLINT_VERSION}"
      print_status "Will install correct version..."
    fi
  else
    print_warning "Found actionlint at ${CURRENT_BIN} but it is not executable"
    print_status "Reinstalling..."
  fi
else
  print_status "actionlint not found, installing..."
fi

if [[ ${NEED_INSTALL} == true ]]; then
  print_status "Installing actionlint ${ACTIONLINT_VERSION} for ${OS_SUFFIX}/${ARCH_SUFFIX}..."

  TEMP_DIR=$(mktemp -d)
  trap 'rm -rf "${TEMP_DIR}"' EXIT

  if curl -L "${ACTIONLINT_URL}" -o "${TEMP_DIR}/actionlint.tar.gz" 2>/dev/null; then
    if tar xzf "${TEMP_DIR}/actionlint.tar.gz" -C "${TEMP_DIR}" 2>/dev/null; then
      if install -m 755 "${TEMP_DIR}/actionlint" "${ACTIONLINT_BIN}" 2>/dev/null; then
        print_success "actionlint installed to ${ACTIONLINT_BIN}"
      else
        print_error "Failed to install actionlint to ${ACTIONLINT_BIN}"
        echo "  Try: sudo install -m 755 ${TEMP_DIR}/actionlint ${ACTIONLINT_BIN}"
        exit 1
      fi
    else
      print_error "Failed to extract actionlint archive"
      exit 1
    fi
  else
    print_error "Failed to download actionlint from ${ACTIONLINT_URL}"
    echo "  Check your internet connection or download manually"
    exit 1
  fi
fi

# Run actionlint on workflow files
print_status "Running actionlint on workflow files..."
if [[ ! -d ".github/workflows" ]]; then
  print_error ".github/workflows directory not found"
  exit 1
fi

# Find all workflow files
shopt -s nullglob
WORKFLOW_FILES=(.github/workflows/*.yml .github/workflows/*.yaml)
shopt -u nullglob

if [[ ${#WORKFLOW_FILES[@]} -eq 0 ]]; then
  print_warning "No workflow files found in .github/workflows"
  exit 0
fi

if "${ACTIONLINT_BIN}" "${WORKFLOW_FILES[@]}" 2>&1; then
  print_success "All ${#WORKFLOW_FILES[@]} workflow file(s) passed actionlint validation"
  exit 0
else
  EXIT_CODE=$?
  print_error "Some workflow files have validation errors (see above)"
  exit "${EXIT_CODE}"
fi
