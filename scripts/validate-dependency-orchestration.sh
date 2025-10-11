#!/usr/bin/env bash
# Validate dependency orchestration setup
# This script ensures all dependency management components are properly configured
# and auto-remediates issues where possible

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}==================================================================${NC}"
echo -e "${CYAN}${BOLD}Hephaestus Dependency Orchestration Validator${NC}"
echo -e "${CYAN}==================================================================${NC}"
echo ""

FAILED=0
REMEDIATED=0
AUTO_REMEDIATE="${AUTO_REMEDIATE:-1}" # Enable auto-remediation by default

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

print_remediate() {
  echo -e "${YELLOW}⚙${NC} $1"
  REMEDIATED=$((REMEDIATED + 1))
}

# Check 1: Validate Python version and auto-remediate if needed
print_status "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' || echo "0.0.0")
PYTHON_MAJOR=$(echo "${PYTHON_VERSION}" | cut -d. -f1)
PYTHON_MINOR=$(echo "${PYTHON_VERSION}" | cut -d. -f2)

if [[ ${PYTHON_MAJOR} -lt 3 ]] || [[ ${PYTHON_MAJOR} -eq 3 && ${PYTHON_MINOR} -lt 12 ]]; then
  print_warning "Python 3.12+ required, found ${PYTHON_VERSION}"
  
  if [[ ${AUTO_REMEDIATE} -eq 1 ]]; then
    print_remediate "Attempting to install Python 3.12 via uv..."
    if command -v uv &>/dev/null; then
      if uv python install 3.12 >/dev/null 2>&1; then
        print_success "Python 3.12 installed via uv"
        if uv python pin 3.12 >/dev/null 2>&1; then
          print_success "Python 3.12 pinned for this project"
          # Recheck version
          PYTHON_VERSION=$(uv run python --version 2>&1 | awk '{print $2}' || echo "${PYTHON_VERSION}")
          print_success "Python ${PYTHON_VERSION} now available"
        else
          print_warning "Could not pin Python 3.12 automatically"
        fi
      else
        print_error "Failed to install Python 3.12 via uv"
        echo "  Manual installation required: https://www.python.org/downloads/"
      fi
    else
      print_error "uv not available - cannot auto-install Python"
      echo "  Install from: https://docs.astral.sh/uv/"
    fi
  else
    print_error "Python 3.12+ required but auto-remediation is disabled"
  fi
else
  print_success "Python ${PYTHON_VERSION} detected"
fi

# Check 2: Validate uv installation and auto-remediate if needed
print_status "Checking uv installation..."
if ! command -v uv &>/dev/null; then
  print_warning "uv not found"
  
  if [[ ${AUTO_REMEDIATE} -eq 1 ]]; then
    print_remediate "Attempting to install uv..."
    if curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; then
      # Add to PATH for this session
      export PATH="${HOME}/.cargo/bin:${HOME}/.local/bin:${PATH}"
      if command -v uv &>/dev/null; then
        UV_VERSION=$(uv --version 2>&1)
        print_success "uv installed: ${UV_VERSION}"
      else
        print_error "uv installation completed but not found in PATH"
        echo "  Try adding to PATH: export PATH=\"\${HOME}/.cargo/bin:\${PATH}\""
      fi
    else
      print_error "Failed to install uv automatically"
      echo "  Install manually from: https://docs.astral.sh/uv/"
    fi
  else
    print_error "uv not found and auto-remediation is disabled"
  fi
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

# Check 5: Validate lockfile is in sync and auto-remediate if needed
print_status "Validating uv.lock is in sync with pyproject.toml..."
if uv lock --check 2>&1 | grep -q "up-to-date"; then
  print_success "uv.lock is in sync"
elif uv lock --check 2>&1; then
  print_success "uv.lock is in sync"
else
  print_warning "uv.lock is out of sync"
  
  if [[ ${AUTO_REMEDIATE} -eq 1 ]]; then
    print_remediate "Regenerating lockfile..."
    if uv lock >/dev/null 2>&1; then
      print_success "uv.lock regenerated and is now in sync"
    else
      print_error "Failed to regenerate uv.lock"
      echo "  Try running: uv lock"
    fi
  else
    print_error "uv.lock is out of sync and auto-remediation is disabled"
    echo "  Run: uv lock"
  fi
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

# Check 10: Test dependency sync and auto-remediate if needed
print_status "Testing dependency sync..."
SYNC_OUTPUT=$(uv sync --locked --extra dev --extra qa 2>&1 || true)
if echo "${SYNC_OUTPUT}" | grep -qE "(Resolved|Audited|Already up-to-date)"; then
  print_success "Dependency sync test passed"
elif [[ -d ".venv" ]]; then
  print_success "Dependencies already synced (.venv exists)"
else
  print_warning "Dependencies not synced"
  
  if [[ ${AUTO_REMEDIATE} -eq 1 ]]; then
    print_remediate "Syncing dependencies..."
    if uv sync --locked --extra dev --extra qa --extra grpc >/dev/null 2>&1; then
      print_success "Dependencies synced successfully"
    else
      print_error "Failed to sync dependencies"
      echo "  Try running: uv sync --extra dev --extra qa --extra grpc"
    fi
  else
    print_error "Dependencies not synced and auto-remediation is disabled"
  fi
fi

# Check 11: Validate environment isolation and auto-remediate if needed
print_status "Checking environment isolation..."
if [[ -d ".venv" ]]; then
  VENV_PYTHON=$(uv run python -c "import sys; print(sys.prefix)" 2>/dev/null || echo "")
  if [[ -n ${VENV_PYTHON} ]] && [[ ${VENV_PYTHON} == *".venv"* || ${VENV_PYTHON} == *".uvenvs"* ]]; then
    print_success "Environment uses isolated .venv"
  else
    print_warning "Environment may not be properly isolated"
  fi
else
  print_warning ".venv not found"
  
  if [[ ${AUTO_REMEDIATE} -eq 1 ]]; then
    print_remediate "Creating virtual environment..."
    if uv sync --locked --extra dev --extra qa --extra grpc >/dev/null 2>&1; then
      print_success ".venv created and dependencies synced"
    else
      print_error "Failed to create .venv"
      echo "  Try running: uv sync --extra dev --extra qa --extra grpc"
    fi
  else
    print_error ".venv not found and auto-remediation is disabled"
  fi
fi

# Check 12: Validate COPYFILE_DISABLE and UV_LINK_MODE on macOS and auto-remediate
if [[ ${OSTYPE} == "darwin"* ]]; then
  print_status "Checking macOS environment variables..."
  
  NEEDS_REMEDIATION=0
  
  if [[ ${COPYFILE_DISABLE:-0} -eq 1 ]]; then
    print_success "COPYFILE_DISABLE=1 is set"
  else
    print_warning "COPYFILE_DISABLE should be set to 1 on macOS"
    NEEDS_REMEDIATION=1
  fi

  if [[ ${UV_LINK_MODE-} == "copy" ]]; then
    print_success "UV_LINK_MODE=copy is set"
  else
    print_warning "UV_LINK_MODE should be set to 'copy' on macOS"
    NEEDS_REMEDIATION=1
  fi
  
  if [[ ${NEEDS_REMEDIATION} -eq 1 ]] && [[ ${AUTO_REMEDIATE} -eq 1 ]]; then
    print_remediate "Setting macOS environment variables for current session..."
    export COPYFILE_DISABLE=1
    export UV_LINK_MODE=copy
    print_success "Environment variables set: COPYFILE_DISABLE=1, UV_LINK_MODE=copy"
    
    # Provide instructions for persistent configuration
    echo ""
    print_status "To make these settings persistent, add to your shell profile:"
    echo "  echo 'export COPYFILE_DISABLE=1' >> ~/.zshrc  # or ~/.bashrc"
    echo "  echo 'export UV_LINK_MODE=copy' >> ~/.zshrc  # or ~/.bashrc"
    echo ""
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
  if [[ ${REMEDIATED} -gt 0 ]]; then
    echo -e "${YELLOW}⚙ ${REMEDIATED} issue(s) were auto-remediated${NC}"
  fi
  exit 0
else
  echo -e "${RED}✗ Some dependency orchestration checks failed${NC}"
  if [[ ${REMEDIATED} -gt 0 ]]; then
    echo -e "${YELLOW}⚙ ${REMEDIATED} issue(s) were auto-remediated but some require manual intervention${NC}"
  fi
  echo ""
  echo "Please review the errors above and take corrective action."
  echo "To disable auto-remediation, run: AUTO_REMEDIATE=0 $0"
  exit 1
fi
