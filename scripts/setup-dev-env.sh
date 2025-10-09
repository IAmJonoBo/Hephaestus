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
    echo ""
    echo "Recommended fixes:"
    if command -v uv &> /dev/null; then
        echo "  1. Install Python 3.12 with uv: uv python install 3.12"
        echo "  2. Use it for this project: uv python pin 3.12"
    else
        echo "  1. Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "  2. Install Python 3.12: uv python install 3.12"
        echo "  3. Use it for this project: uv python pin 3.12"
    fi
    echo "  Or install Python 3.12+ from https://www.python.org/downloads/"
    echo ""
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

# Step 2.5: Detect filesystem type and configure UV environment location
REPO_NAME=$(basename "$(pwd)")
ENV_RELOCATED=0

if [[ "$OSTYPE" == "darwin"* ]]; then
    print_status "Detecting filesystem type..."
    
    # Check if we're on a filesystem that doesn't support extended attributes
    # (exFAT, NTFS, FAT32, etc.)
    FS_TYPE=""
    if command -v stat >/dev/null 2>&1; then
        # macOS stat format
        FS_TYPE=$(stat -f %T . 2>/dev/null || echo "")
    fi
    
    # Alternative: use df and grep
    if [[ -z "$FS_TYPE" ]]; then
        FS_TYPE=$(df -T . 2>/dev/null | tail -1 | awk '{print $2}' || echo "")
    fi
    
    print_success "Filesystem detected: ${FS_TYPE:-unknown}"
    
    # Check if filesystem is non-xattr (exFAT, NTFS, FAT32, etc.)
    NON_XATTR_FS=0
    if [[ "$FS_TYPE" =~ ^(exfat|msdos|ntfs|fat32|vfat)$ ]] || [[ "$FS_TYPE" =~ [Ee]x[Ff][Aa][Tt] ]]; then
        NON_XATTR_FS=1
        print_warning "Non-xattr filesystem detected ($FS_TYPE)"
        print_warning "Extended attributes not supported - relocating virtual environment"
    fi
    
    # Relocate environment to internal disk if on non-xattr filesystem
    if [[ $NON_XATTR_FS -eq 1 ]]; then
        TARGET_ENV_DIR="$HOME/.uvenvs/$REPO_NAME"
        
        print_status "Configuring UV_PROJECT_ENVIRONMENT=$TARGET_ENV_DIR"
        export UV_PROJECT_ENVIRONMENT="$TARGET_ENV_DIR"
        ENV_RELOCATED=1
        
        # Create the parent directory if needed
        mkdir -p "$HOME/.uvenvs"
        
        print_success "Virtual environment will be created on internal disk"
    fi
fi

# Step 2.6: Configure UV for macOS compatibility
if [[ "$OSTYPE" == "darwin"* ]]; then
    print_status "Configuring UV for macOS..."
    
    # Prevent reflink issues on cross-filesystem operations
    export UV_LINK_MODE=copy
    
    # Prevent macOS from creating AppleDouble files during copy operations
    export COPYFILE_DISABLE=1
    
    print_success "macOS compatibility settings applied"
    
    # Strip extended attributes from UV cache to prevent AppleDouble file creation
    print_status "Stripping extended attributes from UV cache..."
    
    UV_CACHE_DIR="${UV_CACHE_DIR:-$HOME/.cache/uv}"
    if [[ -d "$UV_CACHE_DIR" ]] && command -v xattr >/dev/null 2>&1; then
        xattr -rc "$UV_CACHE_DIR" 2>/dev/null || true
        print_success "Extended attributes stripped from UV cache"
    fi
    
    # Clean AppleDouble files from UV cache to prevent installation failures
    if [[ -d "$UV_CACHE_DIR" ]]; then
        find "$UV_CACHE_DIR" -type f -name "._*" -delete 2>/dev/null || true
        find "$UV_CACHE_DIR" -type f -name ".DS_Store" -delete 2>/dev/null || true
        find "$UV_CACHE_DIR" -type d -name "__MACOSX" -exec rm -rf {} + 2>/dev/null || true
        print_success "UV cache cleaned"
    else
        print_success "UV cache directory not found (will be created on first sync)"
    fi
    
    # Handle existing .venv (either directory or symlink)
    if [[ -L ".venv" ]]; then
        # It's a symlink - resolve and clean the target
        VENV_TARGET=$(readlink ".venv")
        if [[ -d "$VENV_TARGET" ]]; then
            print_status "Cleaning macOS metadata from virtual environment..."
            if command -v xattr >/dev/null 2>&1; then
                xattr -rc "$VENV_TARGET" 2>/dev/null || true
            fi
            find "$VENV_TARGET" -type f -name "._*" -delete 2>/dev/null || true
            find "$VENV_TARGET" -type f -name ".DS_Store" -delete 2>/dev/null || true
            find "$VENV_TARGET" -type d -name "__MACOSX" -exec rm -rf {} + 2>/dev/null || true
            print_success "Virtual environment cleaned"
        fi
    elif [[ -d ".venv" ]]; then
        # It's a directory - clean it
        print_status "Cleaning macOS metadata from .venv..."
        if command -v xattr >/dev/null 2>&1; then
            xattr -rc .venv 2>/dev/null || true
        fi
        find .venv -type f -name "._*" -delete 2>/dev/null || true
        find .venv -type f -name ".DS_Store" -delete 2>/dev/null || true
        find .venv -type d -name "__MACOSX" -exec rm -rf {} + 2>/dev/null || true
        print_success ".venv cleaned"
    fi
fi

# Step 3: Sync dependencies
print_status "Syncing dependencies with uv..."
if uv sync --locked --extra dev --extra qa; then
    print_success "Dependencies synced successfully"
    
    # Create/update .venv symlink if environment was relocated
    if [[ $ENV_RELOCATED -eq 1 ]] && [[ -n "${UV_PROJECT_ENVIRONMENT:-}" ]]; then
        print_status "Creating .venv symlink to relocated environment..."
        
        # Remove existing .venv if it's a directory (not a symlink)
        if [[ -d ".venv" ]] && [[ ! -L ".venv" ]]; then
            print_warning "Removing local .venv directory (environment relocated)"
            rm -rf .venv
        fi
        
        # Create or update symlink
        if [[ -L ".venv" ]]; then
            # Update existing symlink
            ln -sfn "$UV_PROJECT_ENVIRONMENT" .venv
        else
            # Create new symlink
            ln -s "$UV_PROJECT_ENVIRONMENT" .venv
        fi
        
        print_success "Symlink created: .venv -> $UV_PROJECT_ENVIRONMENT"
        print_warning "Note: .venv is now a symlink to an APFS-backed location"
    fi
else
    print_error "Failed to sync dependencies"
    
    # If on macOS and failed, suggest additional cleanup
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_warning "macOS detected - trying additional cleanup..."
        
        # Strip xattrs from cache
        UV_CACHE_DIR="${UV_CACHE_DIR:-$HOME/.cache/uv}"
        if [[ -d "$UV_CACHE_DIR" ]] && command -v xattr >/dev/null 2>&1; then
            print_status "Stripping extended attributes from UV cache..."
            xattr -rc "$UV_CACHE_DIR" 2>/dev/null || true
        fi
        
        # More aggressive cleanup of UV cache
        if [[ -d "$UV_CACHE_DIR" ]]; then
            print_status "Clearing entire UV cache..."
            rm -rf "$UV_CACHE_DIR"
            print_success "UV cache cleared"
        fi
        
        # Clear .venv completely (handle both symlink and directory)
        if [[ -L ".venv" ]]; then
            VENV_TARGET=$(readlink ".venv")
            print_status "Removing relocated environment..."
            rm -f .venv
            if [[ -d "$VENV_TARGET" ]]; then
                rm -rf "$VENV_TARGET"
            fi
            print_success "Environment removed"
        elif [[ -d ".venv" ]]; then
            print_status "Removing .venv..."
            rm -rf .venv
            print_success ".venv removed"
        fi
        
        print_warning "Retrying with fresh cache..."
        if uv sync --locked --extra dev --extra qa; then
            print_success "Dependencies synced successfully (after cache clear)"
            
            # Create symlink if environment was relocated
            if [[ $ENV_RELOCATED -eq 1 ]] && [[ -n "${UV_PROJECT_ENVIRONMENT:-}" ]]; then
                print_status "Creating .venv symlink..."
                ln -s "$UV_PROJECT_ENVIRONMENT" .venv
                print_success "Symlink created: .venv -> $UV_PROJECT_ENVIRONMENT"
            fi
        else
            print_warning "Trying without lock file..."
            if uv sync --extra dev --extra qa; then
                print_success "Dependencies synced (without lock)"
                print_warning "Consider updating uv.lock with: uv lock"
            else
                print_error "Failed to sync dependencies"
                echo ""
                echo "If you're still experiencing issues on macOS, try:"
                echo "  1. Manually clear UV cache: rm -rf ~/.cache/uv"
                echo "  2. Run cleanup-macos-cruft.sh script"
                echo "  3. Ensure UV_LINK_MODE=copy is set: export UV_LINK_MODE=copy"
                echo "  4. Try: uv sync --extra dev --extra qa --reinstall"
                echo ""
                exit 1
            fi
        fi
    else
        print_warning "Trying without lock file..."
        if uv sync --extra dev --extra qa; then
            print_success "Dependencies synced (without lock)"
            print_warning "Consider updating uv.lock with: uv lock"
        else
            print_error "Failed to sync dependencies"
            exit 1
        fi
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
    
    # Check if core.hooksPath is configured
    HOOKS_PATH=$(git config --get core.hooksPath 2>/dev/null || echo "")
    if [[ -n "$HOOKS_PATH" ]]; then
        print_warning "core.hooksPath is set to: $HOOKS_PATH"
        print_warning "Pre-commit hooks managed centrally - skipping local installation"
        print_warning "To enable local hooks, run: git config --unset core.hooksPath"
    else
        if uv run pre-commit install; then
            print_success "Pre-commit hooks installed"
        else
            print_warning "Failed to install pre-commit hooks (non-critical)"
        fi
    fi
else
    print_warning "pre-commit not available (optional)"
fi

echo ""
echo -e "${CYAN}==================================================================${NC}"
echo -e "${GREEN}Development environment setup complete!${NC}"
echo -e "${CYAN}==================================================================${NC}"
echo ""

# Show environment location info
if [[ $ENV_RELOCATED -eq 1 ]]; then
    echo -e "${YELLOW}Note:${NC} Virtual environment relocated to APFS-backed location"
    echo "  Location: $UV_PROJECT_ENVIRONMENT"
    echo "  Reason: Repository on non-xattr filesystem ($FS_TYPE)"
    echo "  .venv is a symlink to the relocated environment"
    echo ""
fi

echo "Next steps:"
echo "  • Run quality checks: uv run hephaestus guard-rails"
echo "  • Run tests: uv run pytest"
echo "  • Format code: uv run ruff format ."
echo "  • Check linting: uv run ruff check ."
echo "  • Type check: uv run mypy src tests"
echo ""
echo "For more information, see docs/how-to/quality-gates.md"
echo ""
