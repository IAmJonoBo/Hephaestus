#!/bin/bash
# Install and run actionlint for GitHub Actions workflow validation
#
# This script downloads actionlint if not available and runs it on all workflow files.
# actionlint is not a Python package and must be installed separately.

set -euo pipefail

ACTIONLINT_VERSION="1.7.7"
ACTIONLINT_URL="https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz"
INSTALL_DIR="${HOME}/.local/bin"
ACTIONLINT_BIN="${INSTALL_DIR}/actionlint"

# Create install directory if it doesn't exist
mkdir -p "${INSTALL_DIR}"

# Download and install actionlint if not present
if ! command -v actionlint &> /dev/null; then
    echo "Installing actionlint ${ACTIONLINT_VERSION}..."
    
    # Download to temp directory
    TEMP_DIR=$(mktemp -d)
    trap 'rm -rf "${TEMP_DIR}"' EXIT
    
    curl -L "${ACTIONLINT_URL}" -o "${TEMP_DIR}/actionlint.tar.gz"
    tar xzf "${TEMP_DIR}/actionlint.tar.gz" -C "${TEMP_DIR}"
    
    # Install to user bin directory
    install -m 755 "${TEMP_DIR}/actionlint" "${ACTIONLINT_BIN}"
    
    echo "✓ actionlint installed to ${ACTIONLINT_BIN}"
fi

# Run actionlint on workflow files
echo "Running actionlint on workflow files..."
"${ACTIONLINT_BIN}" .github/workflows/*.yml
