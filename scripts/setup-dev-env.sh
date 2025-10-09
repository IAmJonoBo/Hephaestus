#!/usr/bin/env bash
# Development environment setup script for Hephaestus
# This script ensures a consistent and bulletproof development environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}==================================================================${NC}"
echo -e "${CYAN}Hephaestus Development Environment Setup${NC}"
echo -e "${CYAN}==================================================================${NC}"
echo ""

# Function to print status messages
print_status() {
    echo -e "${CYAN}→${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if we're in the repository root
if [[ ! -f "pyproject.toml" ]]; then
    print_error "Must be run from the repository root"
    exit 1
fi

print_success "Repository root detected"

# Step 1: Check Python version
print_status "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 12 ]]; then
    print_error "Python 3.12+ required, found $PYTHON_VERSION"
    exit 1
fi

print_success "Python $PYTHON_VERSION detected"

# Step 2: Check for uv installation
print_status "Checking for uv package manager..."
if ! command -v uv &> /dev/null; then
    print_warning "uv not found, attempting to install..."
    
    # Try to install uv
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        print_success "uv installed successfully"
        # Add to PATH for this session
        export PATH="$HOME/.cargo/bin:$PATH"
    else
        print_error "Failed to install uv automatically"
        print_warning "Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
else
    UV_VERSION=$(uv --version 2>&1)
    print_success "uv detected: $UV_VERSION"
fi

# Step 3: Sync dependencies
print_status "Syncing dependencies with uv..."
if uv sync --locked --extra dev --extra qa; then
    print_success "Dependencies synced successfully"
else
    print_error "Failed to sync dependencies"
    print_warning "Trying without lock file..."
    if uv sync --extra dev --extra qa; then
        print_success "Dependencies synced (without lock)"
        print_warning "Consider updating uv.lock with: uv lock"
    else
        print_error "Failed to sync dependencies"
        exit 1
    fi
fi

# Step 4: Validate environment
print_status "Validating development environment..."

VALIDATION_FAILED=0

# Check core dependencies
for module in "typer" "rich" "pydantic" "pytest" "ruff" "mypy"; do
    if uv run python -c "import $module; print(f'$module OK')" &> /dev/null; then
        print_success "$module available"
    else
        print_error "$module not available"
        VALIDATION_FAILED=1
    fi
done

# Check CLI tools
if uv run python -m ruff --version &> /dev/null; then
    print_success "ruff CLI available"
else
    print_error "ruff CLI not available"
    VALIDATION_FAILED=1
fi

if uv run mypy --version &> /dev/null; then
    print_success "mypy CLI available"
else
    print_error "mypy CLI not available"
    VALIDATION_FAILED=1
fi

if [[ $VALIDATION_FAILED -eq 1 ]]; then
    print_error "Environment validation failed"
    exit 1
fi

print_success "Environment validation complete"

# Step 5: Run a quick test
print_status "Running quick validation test..."
if uv run pytest tests/ -q --tb=no --maxfail=1 &> /dev/null; then
    print_success "Quick test passed"
else
    print_warning "Some tests failed (this may be expected)"
fi

# Step 6: Install pre-commit hooks (optional)
if command -v pre-commit &> /dev/null || uv run pre-commit --version &> /dev/null; then
    print_status "Setting up pre-commit hooks..."
    if uv run pre-commit install; then
        print_success "Pre-commit hooks installed"
    else
        print_warning "Failed to install pre-commit hooks (non-critical)"
    fi
else
    print_warning "pre-commit not available (optional)"
fi

echo ""
echo -e "${CYAN}==================================================================${NC}"
echo -e "${GREEN}Development environment setup complete!${NC}"
echo -e "${CYAN}==================================================================${NC}"
echo ""
echo "Next steps:"
echo "  • Run quality checks: uv run hephaestus guard-rails"
echo "  • Run tests: uv run pytest"
echo "  • Format code: uv run ruff format ."
echo "  • Check linting: uv run ruff check ."
echo "  • Type check: uv run mypy src tests"
echo ""
echo "For more information, see docs/how-to/quality-gates.md"
echo ""
