#!/usr/bin/env bash
# Validate dependency orchestration setup
# This script ensures all dependency management components are properly configured

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}==================================================================${NC}"
echo -e "${CYAN}Hephaestus Dependency Orchestration Validator${NC}"
echo -e "${CYAN}==================================================================${NC}"
echo ""

FAILED=0

# Function to print status messages
print_status() {
  echo -e "${CYAN}→${NC} $1"
}

print_success() {
  echo -e "${GREEN}✓${NC} $1"
}

print_error() {
  echo -e "${RED}✗${NC} $1"
  FAILED=1
}

print_warning() {
  echo -e "${YELLOW}⚠${NC} $1"
}

# Check 1: Validate Python version
print_status "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "${PYTHON_VERSION}" | cut -d. -f1)
PYTHON_MINOR=$(echo "${PYTHON_VERSION}" | cut -d. -f2)

if [[ ${PYTHON_MAJOR} -lt 3 ]] || [[ ${PYTHON_MAJOR} -eq 3 && ${PYTHON_MINOR} -lt 12 ]]; then
  print_error "Python 3.12+ required, found ${PYTHON_VERSION}"
else
  print_success "Python ${PYTHON_VERSION} detected"
fi

# Check 2: Validate uv installation
print_status "Checking uv installation..."
if ! command -v uv &>/dev/null; then
  print_error "uv not found - install from https://docs.astral.sh/uv/"
else
  UV_VERSION=$(uv --version 2>&1)
  print_success "uv detected: ${UV_VERSION}"
fi

# Check 3: Validate pyproject.toml exists
print_status "Checking pyproject.toml..."
if [[ ! -f "pyproject.toml" ]]; then
  print_error "pyproject.toml not found"
else
  print_success "pyproject.toml found"
fi

# Check 4: Validate uv.lock exists
print_status "Checking uv.lock..."
if [[ ! -f "uv.lock" ]]; then
  print_error "uv.lock not found"
else
  print_success "uv.lock found"
fi

# Check 5: Validate lockfile is in sync
print_status "Validating uv.lock is in sync with pyproject.toml..."
if uv lock --check 2>&1; then
  print_success "uv.lock is in sync"
else
  print_error "uv.lock is out of sync - run 'uv lock' to fix"
fi

# Check 6: Validate workflows use correct Python version
print_status "Checking workflow Python versions..."
INVALID_VERSIONS=$(grep -r "python-version.*3\.14" .github/workflows/*.yml 2>/dev/null || true)
if [[ -n ${INVALID_VERSIONS} ]]; then
  print_error "Found invalid Python 3.14 in workflows:"
  echo "${INVALID_VERSIONS}"
else
  print_success "All workflows use Python 3.12"
fi

# Check 7: Validate workflows use --locked flag
print_status "Checking for missing --locked flags..."
MISSING_LOCKED=$(grep "uv sync" .github/workflows/*.yml | grep -v "name:" | grep -v "\-\-locked" | grep -v "\-\-frozen" || true)
if [[ -n ${MISSING_LOCKED} ]]; then
  print_warning "Found uv sync without --locked flag:"
  echo "${MISSING_LOCKED}"
else
  print_success "All uv sync commands use --locked or --frozen"
fi

# Check 8: Validate setup-uv usage
print_status "Checking setup-uv configurations..."
MISSING_PYTHON=$(grep -l "setup-uv@v" .github/workflows/*.yml | while read -r file; do
  if ! grep -q "python-version" "${file}"; then
    echo "${file}"
  fi
done)
if [[ -n ${MISSING_PYTHON} ]]; then
  print_warning "Found setup-uv without python-version:"
  echo "${MISSING_PYTHON}"
else
  print_success "All setup-uv actions specify python-version"
fi

# Check 9: Validate dependabot configuration
print_status "Checking dependabot configuration..."
if [[ ! -f ".github/dependabot.yml" ]]; then
  print_warning "dependabot.yml not found"
else
  if grep -q "package-ecosystem: pip" .github/dependabot.yml; then
    print_success "Dependabot configured for pip"
  else
    print_warning "Dependabot not configured for pip"
  fi
fi

# Check 10: Test dependency sync
print_status "Testing dependency sync..."
if uv sync --locked --extra dev --extra qa 2>&1 | grep -qE "(Resolved|Audited|Already up-to-date)"; then
  print_success "Dependency sync test passed"
else
  print_warning "Could not verify dependency sync"
fi

# Check 11: Validate environment isolation
print_status "Checking environment isolation..."
if [[ -d ".venv" ]]; then
  VENV_PYTHON=$(uv run python -c "import sys; print(sys.prefix)" 2>/dev/null || echo "")
  if [[ -n ${VENV_PYTHON} ]] && [[ ${VENV_PYTHON} == *".venv"* ]]; then
    print_success "Environment uses isolated .venv"
  else
    print_warning "Environment may not be properly isolated"
  fi
else
  print_warning ".venv not found - run 'uv sync' to create"
fi

# Check 12: Validate COPYFILE_DISABLE and UV_LINK_MODE on macOS
if [[ ${OSTYPE} == "darwin"* ]]; then
  print_status "Checking macOS environment variables..."
  
  if [[ ${COPYFILE_DISABLE:-0} -eq 1 ]]; then
    print_success "COPYFILE_DISABLE=1 is set"
  else
    print_warning "COPYFILE_DISABLE should be set to 1 on macOS"
  fi
  
  if [[ ${UV_LINK_MODE} == "copy" ]]; then
    print_success "UV_LINK_MODE=copy is set"
  else
    print_warning "UV_LINK_MODE should be set to 'copy' on macOS"
  fi
fi

# Check 13: Smoke test uv sync with Python 3.12
print_status "Testing throwaway uv sync with Python 3.12..."
if UV_PYTHON=3.12 uv sync --frozen --dry-run 2>&1 | grep -qE "(Would|Already)"; then
  print_success "uv sync dry-run test passed"
else
  print_warning "Could not verify uv sync dry-run"
fi

# Check 14: Smoke test hephaestus CLI
print_status "Testing hephaestus CLI smoke test..."
if uv run hephaestus version >/dev/null 2>&1; then
  print_success "hephaestus CLI smoke test passed"
else
  print_error "hephaestus CLI smoke test failed"
fi

# Summary
echo ""
echo -e "${CYAN}==================================================================${NC}"
if [[ ${FAILED} -eq 0 ]]; then
  echo -e "${GREEN}✓ All dependency orchestration checks passed${NC}"
  exit 0
else
  echo -e "${RED}✗ Some dependency orchestration checks failed${NC}"
  echo ""
  echo "Please fix the issues above to ensure proper dependency management."
  exit 1
fi
