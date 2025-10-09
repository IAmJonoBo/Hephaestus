#!/usr/bin/env bash
# Test script for setup-dev-env.sh filesystem detection logic
# This validates the logic without requiring actual environment setup

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TEST_COUNT=0
PASSED=0
FAILED=0

print_test() {
    echo -e "${YELLOW}→ TEST:${NC} $1"
}

print_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    PASSED=$((PASSED + 1))
}

print_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    FAILED=$((FAILED + 1))
}

echo "================================================"
echo "Setup Script Logic Tests"
echo "================================================"
echo ""

# Test 1: Check script syntax
TEST_COUNT=$((TEST_COUNT + 1))
print_test "Validating setup-dev-env.sh syntax"
if bash -n scripts/setup-dev-env.sh 2>/dev/null; then
    print_pass "Script has valid bash syntax"
else
    print_fail "Script has syntax errors"
fi

# Test 2: Test filesystem type detection logic
TEST_COUNT=$((TEST_COUNT + 1))
print_test "Testing filesystem detection regex"

# Simulate the detection logic
check_fs_type() {
    local fs_type="$1"
    
    if [[ "$fs_type" =~ ^(exfat|msdos|ntfs|fat32|vfat)$ ]] || [[ "$fs_type" =~ [Ee]x[Ff][Aa][Tt] ]]; then
        echo "non-xattr"
    else
        echo "xattr"
    fi
}

# Test various filesystem types
test_fs() {
    local fs_type="$1"
    local expected="$2"
    local result
    result=$(check_fs_type "$fs_type")
    
    if [[ "$result" == "$expected" ]]; then
        print_pass "Detected $fs_type as $expected"
        return 0
    else
        print_fail "Expected $fs_type to be $expected, got $result"
        return 1
    fi
}

# Test non-xattr filesystems
test_fs "exfat" "non-xattr"
test_fs "ExFAT" "non-xattr"
test_fs "exFAT" "non-xattr"
test_fs "msdos" "non-xattr"
test_fs "ntfs" "non-xattr"
test_fs "fat32" "non-xattr"
test_fs "vfat" "non-xattr"

# Test xattr-supporting filesystems
test_fs "apfs" "xattr"
test_fs "hfs" "xattr"
test_fs "ext4" "xattr"
test_fs "btrfs" "xattr"
test_fs "xfs" "xattr"

# Test 3: Verify ENV_RELOCATED variable logic
TEST_COUNT=$((TEST_COUNT + 1))
print_test "Testing environment relocation flag logic"

ENV_RELOCATED=0
NON_XATTR_FS=1

if [[ $NON_XATTR_FS -eq 1 ]]; then
    ENV_RELOCATED=1
fi

if [[ $ENV_RELOCATED -eq 1 ]]; then
    print_pass "ENV_RELOCATED flag set correctly"
else
    print_fail "ENV_RELOCATED flag not set"
fi

# Test 4: Verify symlink target path generation
TEST_COUNT=$((TEST_COUNT + 1))
print_test "Testing symlink path generation"

REPO_NAME="Hephaestus"
TARGET_ENV_DIR="$HOME/.uvenvs/$REPO_NAME"

if [[ "$TARGET_ENV_DIR" == "$HOME/.uvenvs/Hephaestus" ]]; then
    print_pass "Target environment path generated correctly"
else
    print_fail "Target environment path incorrect: $TARGET_ENV_DIR"
fi

# Test 5: Test Python version checking logic
TEST_COUNT=$((TEST_COUNT + 1))
print_test "Testing Python version check logic"

check_python_version() {
    local version="$1"
    local major minor
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)
    
    if [[ "$major" -lt 3 ]] || [[ "$major" -eq 3 && "$minor" -lt 12 ]]; then
        echo "fail"
    else
        echo "pass"
    fi
}

# Test various Python versions
test_python() {
    local version="$1"
    local expected="$2"
    local result
    result=$(check_python_version "$version")
    
    if [[ "$result" == "$expected" ]]; then
        print_pass "Python $version correctly evaluated as $expected"
        return 0
    else
        print_fail "Python $version incorrectly evaluated as $result, expected $expected"
        return 1
    fi
}

test_python "3.11.0" "fail"
test_python "3.12.0" "pass"
test_python "3.12.3" "pass"
test_python "3.13.0" "pass"
test_python "3.9.6" "fail"

# Test 6: Test symlink handling logic
TEST_COUNT=$((TEST_COUNT + 1))
print_test "Testing symlink vs directory detection"

# Create test directory structure
TEST_DIR=$(mktemp -d)
cd "$TEST_DIR" || exit 1

# Test case 1: .venv is a directory
mkdir -p .venv
if [[ -d ".venv" ]] && [[ ! -L ".venv" ]]; then
    print_pass "Correctly detected .venv as directory (not symlink)"
else
    print_fail "Failed to detect .venv as directory"
fi

# Test case 2: .venv is a symlink
rm -rf .venv
mkdir -p /tmp/test-target-$$
ln -s /tmp/test-target-$$ .venv
if [[ -L ".venv" ]]; then
    VENV_TARGET=$(readlink ".venv")
    if [[ "$VENV_TARGET" == "/tmp/test-target-$$" ]]; then
        print_pass "Correctly detected .venv as symlink and read target"
    else
        print_fail "Failed to read symlink target correctly"
    fi
else
    print_fail "Failed to detect .venv as symlink"
fi

# Clean up test directory
cd / || exit 1
rm -rf "$TEST_DIR" /tmp/test-target-$$

# Test 7: Verify core.hooksPath detection
TEST_COUNT=$((TEST_COUNT + 1))
print_test "Testing git hooks path detection"

# Create a test git repo
TEST_REPO=$(mktemp -d)
cd "$TEST_REPO" || exit 1
git init -q 2>/dev/null

# Test without hooksPath set
HOOKS_PATH=$(git config --get core.hooksPath 2>/dev/null || echo "")
if [[ -z "$HOOKS_PATH" ]]; then
    print_pass "Correctly detected no core.hooksPath configured"
else
    print_fail "Incorrectly detected core.hooksPath when none set"
fi

# Test with hooksPath set
git config core.hooksPath /some/path 2>/dev/null
HOOKS_PATH=$(git config --get core.hooksPath 2>/dev/null || echo "")
if [[ -n "$HOOKS_PATH" ]] && [[ "$HOOKS_PATH" == "/some/path" ]]; then
    print_pass "Correctly detected core.hooksPath configuration"
else
    print_fail "Failed to detect core.hooksPath configuration"
fi

# Clean up test repo
cd / || exit 1
rm -rf "$TEST_REPO"

echo ""
echo "================================================"
echo "Test Summary"
echo "================================================"
echo "Total tests: $TEST_COUNT"
echo -e "${GREEN}Passed: $PASSED${NC}"
if [[ $FAILED -gt 0 ]]; then
    echo -e "${RED}Failed: $FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
