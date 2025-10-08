#!/usr/bin/env bash
# Version Bumping Script for Hephaestus
#
# Usage:
#   ./scripts/bump_version.sh <new_version>
#   ./scripts/bump_version.sh 0.3.0
#
# This script:
# - Updates version in pyproject.toml
# - Updates version in __init__.py (if present)
# - Validates version format
# - Provides next steps guidance

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() {
  echo -e "${RED}Error: $1${NC}" >&2
}

print_success() {
  echo -e "${GREEN}$1${NC}"
}

print_info() {
  echo -e "${YELLOW}$1${NC}"
}

# Check arguments
if [ $# -ne 1 ]; then
  print_error "Invalid number of arguments"
  echo "Usage: $0 <version>"
  echo "Example: $0 0.3.0"
  exit 1
fi

NEW_VERSION="$1"

# Validate version format (semantic versioning: X.Y.Z)
if ! [[ $NEW_VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  print_error "Invalid version format. Must be X.Y.Z (e.g., 0.3.0)"
  exit 1
fi

# Get repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Check if we're in the correct directory
if [ ! -f "pyproject.toml" ]; then
  print_error "pyproject.toml not found. Are you in the repository root?"
  exit 1
fi

# Get current version
CURRENT_VERSION=$(grep -E '^version = ' pyproject.toml | sed -E 's/version = "(.*)"/\1/')

if [ -z "$CURRENT_VERSION" ]; then
  print_error "Could not extract current version from pyproject.toml"
  exit 1
fi

print_info "Current version: $CURRENT_VERSION"
print_info "New version: $NEW_VERSION"

# Check if version is actually changing
if [ "$CURRENT_VERSION" = "$NEW_VERSION" ]; then
  print_error "New version is the same as current version"
  exit 1
fi

# Determine release type
IFS='.' read -r CURR_MAJOR CURR_MINOR CURR_PATCH <<<"$CURRENT_VERSION"
IFS='.' read -r NEW_MAJOR NEW_MINOR NEW_PATCH <<<"$NEW_VERSION"

RELEASE_TYPE=""
if [ "$NEW_MAJOR" -gt "$CURR_MAJOR" ]; then
  RELEASE_TYPE="MAJOR"
elif [ "$NEW_MAJOR" -lt "$CURR_MAJOR" ]; then
  print_error "Cannot downgrade major version"
  exit 1
elif [ "$NEW_MINOR" -gt "$CURR_MINOR" ]; then
  RELEASE_TYPE="MINOR"
elif [ "$NEW_MINOR" -lt "$CURR_MINOR" ]; then
  print_error "Cannot downgrade minor version (unless major version increased)"
  exit 1
elif [ "$NEW_PATCH" -gt "$CURR_PATCH" ]; then
  RELEASE_TYPE="PATCH"
else
  print_error "Cannot downgrade patch version"
  exit 1
fi

print_info "Release type: $RELEASE_TYPE"

# Confirm with user
echo ""
echo "This will:"
echo "  1. Update version in pyproject.toml: $CURRENT_VERSION → $NEW_VERSION"
echo "  2. Update version in src/hephaestus/__init__.py (if present)"
echo ""
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  print_info "Aborted"
  exit 0
fi

# Update pyproject.toml
print_info "Updating pyproject.toml..."
if [[ $OSTYPE == "darwin"* ]]; then
  # macOS requires an extension for -i
  sed -i.bak "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
  rm pyproject.toml.bak
else
  # Linux
  sed -i "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
fi

# Update __init__.py if it has __version__
INIT_FILE="src/hephaestus/__init__.py"
if [ -f "$INIT_FILE" ] && grep -q "__version__" "$INIT_FILE"; then
  print_info "Updating $INIT_FILE..."
  if [[ $OSTYPE == "darwin"* ]]; then
    sed -i.bak "s/__version__ = \".*\"/__version__ = \"$NEW_VERSION\"/" "$INIT_FILE"
    rm "${INIT_FILE}.bak"
  else
    sed -i "s/__version__ = \".*\"/__version__ = \"$NEW_VERSION\"/" "$INIT_FILE"
  fi
fi

print_success "✓ Version bumped to $NEW_VERSION"

# Generate CHANGELOG template
echo ""
print_info "CHANGELOG template for version $NEW_VERSION:"
echo ""
echo "## [$NEW_VERSION] - $(date +%Y-%m-%d)"
echo ""
echo "### Added"
echo "- New feature 1"
echo "- New feature 2"
echo ""
if [ "$RELEASE_TYPE" = "MAJOR" ]; then
  echo "### Changed (BREAKING)"
  echo "- Breaking change 1"
  echo "- Breaking change 2"
  echo ""
fi
echo "### Fixed"
echo "- Bug fix 1"
echo ""
echo "### Security"
echo "- Security improvement 1"
echo ""

# Provide next steps
echo ""
print_info "Next steps:"
echo ""
echo "1. Update CHANGELOG.md with the template above"
echo "   vim CHANGELOG.md"
echo ""
echo "2. Update README.md 'What's New' section (if $RELEASE_TYPE release)"
if [ "$RELEASE_TYPE" = "MAJOR" ]; then
  echo "   ⚠️  Document migration guide for breaking changes!"
fi
echo ""
echo "3. Review and commit changes:"
echo "   git status"
echo "   git diff pyproject.toml"
if [ -f "$INIT_FILE" ] && grep -q "__version__" "$INIT_FILE"; then
  echo "   git diff $INIT_FILE"
fi
echo "   git add pyproject.toml $INIT_FILE CHANGELOG.md README.md"
echo "   git commit -m 'chore: Prepare release v$NEW_VERSION'"
echo ""
echo "4. Run quality checks:"
echo "   hephaestus guard-rails"
echo "   hephaestus guard-rails --drift"
echo ""
echo "5. Push changes:"
if [ "$RELEASE_TYPE" = "PATCH" ]; then
  echo "   git push origin main"
else
  echo "   git checkout -b release/v$NEW_VERSION"
  echo "   git push origin release/v$NEW_VERSION"
  echo "   # Then open PR for review"
fi
echo ""
print_info "See docs/how-to/release-process.md for full release guide"
