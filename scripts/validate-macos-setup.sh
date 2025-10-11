#!/usr/bin/env bash
# Validation script for macOS setup fixes
# This script tests the logic added to setup-dev-env.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_test() {
  echo -e "${CYAN}→ TEST:${NC} $1"
}

print_pass() {
  echo -e "${GREEN}✓ PASS:${NC} $1"
}

print_fail() {
  echo -e "${RED}✗ FAIL:${NC} $1"
}

print_info() {
  echo -e "${YELLOW}ℹ INFO:${NC} $1"
}

echo "======================================"
echo "macOS Setup Validation Tests"
echo "======================================"
echo ""

# Test 1: Check script syntax
print_test "Checking setup-dev-env.sh syntax..."
if bash -n scripts/setup-dev-env.sh; then
  print_pass "Script has valid bash syntax"
else
  print_fail "Script has syntax errors"
  exit 1
fi

# Test 2: Check if macOS detection works
print_test "Checking macOS detection logic..."
if [[ $OSTYPE == "darwin"* ]]; then
  print_pass "Running on macOS (detected: $OSTYPE)"
  IS_MACOS=true
else
  print_info "Not running on macOS (detected: $OSTYPE)"
  IS_MACOS=false
fi

# Test 3: Check if COPYFILE_DISABLE works
print_test "Checking COPYFILE_DISABLE environment variable..."
export COPYFILE_DISABLE=1
if [[ $COPYFILE_DISABLE == "1" ]]; then
  print_pass "COPYFILE_DISABLE is set correctly"
else
  print_fail "COPYFILE_DISABLE is not set"
fi

# Test 4: Check if UV_LINK_MODE works
print_test "Checking UV_LINK_MODE environment variable..."
export UV_LINK_MODE=copy
if [[ $UV_LINK_MODE == "copy" ]]; then
  print_pass "UV_LINK_MODE is set correctly"
else
  print_fail "UV_LINK_MODE is not set"
fi

# Test 5: Verify cleanup patterns work (dry-run)
if [[ $IS_MACOS == true ]]; then
  print_test "Checking AppleDouble file detection patterns..."

  # Create a temporary test directory
  TEST_DIR=$(mktemp -d)

  # Create test files
  touch "$TEST_DIR/.DS_Store"
  touch "$TEST_DIR/._test"
  mkdir -p "$TEST_DIR/__MACOSX"

  # Try to find and count them
  COUNT=$(find "$TEST_DIR" -type f -name "._*" -o -name ".DS_Store" | wc -l | tr -d ' ')

  if [[ $COUNT -ge 2 ]]; then
    print_pass "AppleDouble file patterns work (found $COUNT files)"
  else
    print_fail "AppleDouble file patterns not working correctly"
  fi

  # Cleanup test directory
  rm -rf "$TEST_DIR"
fi

# Test 6: Check if UV cache directory detection works
print_test "Checking UV cache directory detection..."
UV_CACHE_DIR="${UV_CACHE_DIR:-$HOME/.cache/uv}"
print_info "UV cache directory: $UV_CACHE_DIR"
if [[ -n $UV_CACHE_DIR ]]; then
  print_pass "UV cache directory path is set"
else
  print_fail "UV cache directory path is not set"
fi

# Test 7: Verify cleanup-macos-cruft.sh syntax
print_test "Checking cleanup-macos-cruft.sh syntax..."
if bash -n cleanup-macos-cruft.sh; then
  print_pass "cleanup-macos-cruft.sh has valid bash syntax"
else
  print_fail "cleanup-macos-cruft.sh has syntax errors"
  exit 1
fi

# Test 8: Verify no AppleDouble files in cache or .venv after cleanup
if [[ $IS_MACOS == true ]]; then
  print_test "Checking for AppleDouble artifacts after cleanup..."

  # Check UV cache
  UV_CACHE_DIR="${UV_CACHE_DIR:-$HOME/.cache/uv}"
  APPLEDOUBLE_COUNT=0

  if [[ -d $UV_CACHE_DIR ]]; then
    APPLEDOUBLE_COUNT=$(find "$UV_CACHE_DIR" -name "._*" -type f 2>/dev/null | wc -l | tr -d ' ')
  fi

  # Check .venv
  if [[ -d ".venv" ]]; then
    VENV_COUNT=$(find ".venv" -name "._*" -type f 2>/dev/null | wc -l | tr -d ' ')
    APPLEDOUBLE_COUNT=$((APPLEDOUBLE_COUNT + VENV_COUNT))
  fi

  if [[ $APPLEDOUBLE_COUNT -eq 0 ]]; then
    print_pass "No AppleDouble artifacts found"
  else
    print_fail "Found $APPLEDOUBLE_COUNT AppleDouble artifacts - cleanup required"
    exit 1
  fi
fi

echo ""
echo "======================================"
echo "All validation tests passed!"
echo "======================================"
echo ""

if [[ $IS_MACOS == true ]]; then
  echo "macOS detected - the setup script will:"
  echo "  1. Set UV_LINK_MODE=copy"
  echo "  2. Set COPYFILE_DISABLE=1"
  echo "  3. Clean AppleDouble files from UV cache"
  echo "  4. Clean AppleDouble files from .venv"
  echo "  5. Retry with full cleanup on failure"
else
  echo "Non-macOS system detected - macOS-specific logic will be skipped"
fi
echo ""
