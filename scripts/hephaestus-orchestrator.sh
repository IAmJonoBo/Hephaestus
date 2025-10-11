#!/usr/bin/env bash
# Hephaestus Unified Orchestrator
# Intelligent, context-aware automation for environment setup, validation, and dependency management
# This script unifies all validation and setup operations into a single, intelligent workflow

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration flags (inherit from environment or use defaults)
AUTO_REMEDIATE="${AUTO_REMEDIATE:-1}"
DRY_RUN="${DRY_RUN:-0}"
INTERACTIVE="${INTERACTIVE:-0}"
PERSIST_CONFIG="${PERSIST_CONFIG:-0}"
LOG_REMEDIATION="${LOG_REMEDIATION:-1}"
SKIP_TESTS="${SKIP_TESTS:-0}"
FAST_MODE="${FAST_MODE:-0}" # Skip optional checks for speed

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Log setup
LOG_DIR="${HOME}/.hephaestus/logs"
LOG_FILE="${LOG_DIR}/orchestrator-$(date +%Y%m%d-%H%M%S).log"
STATE_FILE="${HOME}/.hephaestus/state.json"

# Context tracking
declare -A CONTEXT
CONTEXT[python_version]=""
CONTEXT[uv_installed]=""
CONTEXT[venv_exists]=""
CONTEXT[dependencies_synced]=""
CONTEXT[lockfile_synced]=""
CONTEXT[last_validation]=""

# Performance tracking
START_TIME=$(date +%s)

# Initialize logging
init_logging() {
  if [[ ${LOG_REMEDIATION} -eq 1 ]]; then
    mkdir -p "${LOG_DIR}"
    mkdir -p "$(dirname "${STATE_FILE}")"

    # Log rotation: keep only last 20 logs
    local log_count=$(ls -1 "${LOG_DIR}"/orchestrator-*.log 2>/dev/null | wc -l)
    if [[ ${log_count} -gt 20 ]]; then
      ls -t "${LOG_DIR}"/orchestrator-*.log | tail -n +21 | xargs rm -f
      log_message "LOG_ROTATION: Removed old logs, kept 20 most recent"
    fi

    touch "${LOG_FILE}" # Ensure file exists
    echo "==================================================================" >>"${LOG_FILE}"
    echo "Hephaestus Unified Orchestrator" >>"${LOG_FILE}"
    echo "Started: $(date)" >>"${LOG_FILE}"
    echo "Mode: AUTO_REMEDIATE=${AUTO_REMEDIATE} DRY_RUN=${DRY_RUN} INTERACTIVE=${INTERACTIVE}" >>"${LOG_FILE}"
    echo "Hostname: $(hostname)" >>"${LOG_FILE}"
    echo "User: $(whoami)" >>"${LOG_FILE}"
    echo "PWD: $(pwd)" >>"${LOG_FILE}"
    echo "==================================================================" >>"${LOG_FILE}"
  fi
}

# Logging function
log_message() {
  if [[ ${LOG_REMEDIATION} -eq 1 ]] && [[ -f ${LOG_FILE} ]]; then
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $1" >>"${LOG_FILE}"
  fi
}

# Print functions
print_header() {
  echo ""
  echo -e "${CYAN}==================================================================${NC}"
  echo -e "${CYAN}${BOLD}$1${NC}"
  echo -e "${CYAN}==================================================================${NC}"
  echo ""
  log_message "HEADER: $1"
}

print_section() {
  echo ""
  echo -e "${BLUE}▶ $1${NC}"
  log_message "SECTION: $1"
}

print_status() {
  echo -e "${CYAN}  →${NC} $1"
  log_message "STATUS: $1"
}

print_success() {
  echo -e "${GREEN}  ✓${NC} $1"
  log_message "SUCCESS: $1"
}

print_error() {
  echo -e "${RED}  ✗${NC} $1"
  log_message "ERROR: $1"
}

print_warning() {
  echo -e "${YELLOW}  ⚠${NC} $1"
  log_message "WARNING: $1"
}

print_info() {
  echo -e "${MAGENTA}  ℹ${NC} $1"
  log_message "INFO: $1"
}

print_skip() {
  echo -e "${YELLOW}  ⊘${NC} $1"
  log_message "SKIP: $1"
}

# Load previous state
load_state() {
  if [[ -f ${STATE_FILE} ]]; then
    while IFS='=' read -r key value; do
      CONTEXT["$key"]="$value"
    done <"${STATE_FILE}"
    print_info "Loaded previous state from $(date -r "${STATE_FILE}" +%Y-%m-%d\ %H:%M:%S 2>/dev/null || echo 'cache')"
  fi
}

# Save current state
save_state() {
  {
    for key in "${!CONTEXT[@]}"; do
      echo "${key}=${CONTEXT[$key]}"
    done
  } >"${STATE_FILE}"
  log_message "STATE_SAVED: $(date)"
}

# Check if we need to run a validation (context-aware skip)
should_run_check() {
  local check_name="$1"
  local cache_key="$2"
  local cache_duration="${3:-3600}" # Default 1 hour

  # Always run if not in fast mode
  if [[ ${FAST_MODE} -eq 0 ]]; then
    return 0
  fi

  # Check if we have cached state
  local last_check="${CONTEXT[$cache_key]:-0}"
  local current_time=$(date +%s)
  local age=$((current_time - last_check))

  if [[ ${age} -lt ${cache_duration} ]]; then
    print_skip "${check_name} (validated ${age}s ago, cache valid for ${cache_duration}s)"
    log_message "CACHE_HIT: ${check_name} age=${age}s"
    return 1
  fi

  return 0
}

# Update cache timestamp
update_cache() {
  local cache_key="$1"
  CONTEXT["$cache_key"]=$(date +%s)
}

# File locking for concurrent execution safety
# Check disk space before operations
check_disk_space() {
  local min_space_gb=1

  if command -v df &>/dev/null; then
    local available_space=$(df -BG . 2>/dev/null | tail -1 | awk '{print $4}' | sed 's/G//' 2>/dev/null || echo "999")
    if [[ ${available_space} =~ ^[0-9]+$ ]] && [[ ${available_space} -lt ${min_space_gb} ]]; then
      print_error "Insufficient disk space: ${available_space}GB available (need at least ${min_space_gb}GB)"
      log_message "ERROR: Insufficient disk space - ${available_space}GB"
      return 1
    fi
  fi
  return 0
}

# Check for stale locks and clean them
clean_stale_locks() {
  local lockfile="${HOME}/.hephaestus/orchestrator.lock"

  if [[ -f ${lockfile} ]]; then
    local lock_pid=$(cat "${lockfile}" 2>/dev/null || echo "")
    if [[ -n ${lock_pid} ]] && ! kill -0 "${lock_pid}" 2>/dev/null; then
      print_warning "Removing stale lock from PID ${lock_pid}"
      rm -f "${lockfile}"
      log_message "STALE_LOCK_REMOVED: PID=${lock_pid}"
    fi
  fi
}

# File locking for concurrent execution safety
acquire_lock() {
  local lockfile="${HOME}/.hephaestus/orchestrator.lock"
  local max_wait=30
  local waited=0

  # Clean stale locks first
  clean_stale_locks

  while [[ -f ${lockfile} ]] && [[ ${waited} -lt ${max_wait} ]]; do
    local lock_pid=$(cat "${lockfile}" 2>/dev/null || echo "")
    if [[ -n ${lock_pid} ]] && ! kill -0 "${lock_pid}" 2>/dev/null; then
      # Stale lock, remove it
      rm -f "${lockfile}"
      break
    fi
    print_warning "Another orchestrator instance is running (PID ${lock_pid}), waiting..."
    sleep 2
    waited=$((waited + 2))
  done

  if [[ -f ${lockfile} ]]; then
    print_error "Could not acquire lock after ${max_wait}s"
    return 1
  fi

  echo "$$" >"${lockfile}"
  log_message "LOCK_ACQUIRED: PID=$$"

  # Ensure lock is removed on exit
  trap "rm -f '${lockfile}'" EXIT INT TERM

  return 0
}

# Release lock
release_lock() {
  local lockfile="${HOME}/.hephaestus/orchestrator.lock"
  rm -f "${lockfile}"
  log_message "LOCK_RELEASED"
}

# Phase 1: Environment Validation
phase_environment() {
  print_section "Phase 1: Environment Validation"

  if should_run_check "Python version" "last_python_check" 3600; then
    print_status "Checking Python version..."
    # Run only the Python check from validate-dependency-orchestration.sh
    export AUTO_REMEDIATE DRY_RUN INTERACTIVE PERSIST_CONFIG LOG_REMEDIATION

    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' || echo "0.0.0")
    PYTHON_MAJOR=$(echo "${PYTHON_VERSION}" | cut -d. -f1)
    PYTHON_MINOR=$(echo "${PYTHON_VERSION}" | cut -d. -f2)

    if [[ ${PYTHON_MAJOR} -ge 3 ]] && [[ ${PYTHON_MINOR} -ge 12 ]]; then
      print_success "Python ${PYTHON_VERSION} detected"
      CONTEXT[python_version]="${PYTHON_VERSION}"
      update_cache "last_python_check"
    else
      print_warning "Python 3.12+ required, found ${PYTHON_VERSION}"
      # Let the full orchestration handle this
    fi
  fi

  if should_run_check "UV installation" "last_uv_check" 3600; then
    print_status "Checking uv installation..."
    if command -v uv &>/dev/null; then
      UV_VERSION=$(uv --version 2>&1)
      print_success "uv detected: ${UV_VERSION}"
      CONTEXT[uv_installed]="yes"
      update_cache "last_uv_check"
    else
      print_warning "uv not found"
      CONTEXT[uv_installed]="no"
    fi
  fi
}

# Phase 2: Dependency Orchestration
phase_dependencies() {
  print_section "Phase 2: Dependency Orchestration"

  # Check if dependencies need syncing
  local needs_sync=0

  if should_run_check "Lockfile sync" "last_lockfile_check" 300; then
    print_status "Checking lockfile sync status..."
    if [[ -f "uv.lock" ]] && [[ -f "pyproject.toml" ]]; then
      if uv lock --check 2>&1 | grep -q "up-to-date"; then
        print_success "Lockfile is in sync"
        CONTEXT[lockfile_synced]="yes"
        update_cache "last_lockfile_check"
      else
        print_warning "Lockfile out of sync"
        needs_sync=1
        CONTEXT[lockfile_synced]="no"
      fi
    fi
  fi

  if should_run_check "Virtual environment" "last_venv_check" 600; then
    print_status "Checking virtual environment..."
    if [[ -d ".venv" ]]; then
      print_success "Virtual environment exists"
      CONTEXT[venv_exists]="yes"
      update_cache "last_venv_check"
    else
      print_warning "Virtual environment not found"
      needs_sync=1
      CONTEXT[venv_exists]="no"
    fi
  fi

  if [[ ${needs_sync} -eq 1 ]] || should_run_check "Dependency sync" "last_dep_sync" 1800; then
    print_status "Running full dependency orchestration..."
    export AUTO_REMEDIATE DRY_RUN INTERACTIVE PERSIST_CONFIG LOG_REMEDIATION PRE_FLIGHT_CHECK=0

    if bash "${SCRIPT_DIR}/validate-dependency-orchestration.sh" >>"${LOG_FILE}" 2>&1; then
      print_success "Dependency orchestration complete"
      CONTEXT[dependencies_synced]="yes"
      update_cache "last_dep_sync"
    else
      print_error "Dependency orchestration failed"
      return 1
    fi
  else
    print_skip "Dependency sync (recently validated)"
  fi
}

# Phase 3: Code Quality Gates
phase_quality() {
  print_section "Phase 3: Code Quality Validation"

  if [[ ${SKIP_TESTS} -eq 1 ]]; then
    print_skip "Quality checks (SKIP_TESTS=1)"
    return 0
  fi

  if should_run_check "Quality gates" "last_quality_check" 600; then
    print_status "Running quality gates..."

    # Run linting checks only (fast)
    if [[ ${FAST_MODE} -eq 1 ]]; then
      print_status "Fast mode: Running ruff check only..."
      if command -v ruff &>/dev/null || uv run ruff --version &>/dev/null 2>&1; then
        if uv run ruff check . >>"${LOG_FILE}" 2>&1; then
          print_success "Ruff linting passed"
          update_cache "last_quality_check"
        else
          print_warning "Ruff linting found issues"
        fi
      fi
    else
      # Full quality gates (slower)
      print_status "Running full quality gates..."
      export AUTO_REMEDIATE DRY_RUN INTERACTIVE

      # Run actionlint
      if bash "${SCRIPT_DIR}/run_actionlint.sh" >>"${LOG_FILE}" 2>&1; then
        print_success "Workflow validation passed"
      else
        print_warning "Workflow validation found issues"
      fi

      update_cache "last_quality_check"
    fi
  else
    print_skip "Quality checks (recently validated)"
  fi
}

# Phase 4: Platform-Specific Checks
phase_platform() {
  print_section "Phase 4: Platform-Specific Validation"

  if [[ ${OSTYPE} == "darwin"* ]]; then
    if should_run_check "macOS setup" "last_macos_check" 3600; then
      print_status "Running macOS-specific checks..."

      if bash "${SCRIPT_DIR}/validate-macos-setup.sh" >>"${LOG_FILE}" 2>&1; then
        print_success "macOS validation passed"
        update_cache "last_macos_check"
      else
        print_warning "macOS validation found issues"
      fi
    else
      print_skip "macOS checks (recently validated)"
    fi
  else
    print_skip "macOS checks (not on macOS)"
  fi
}

# Phase 5: Summary and Cleanup
phase_summary() {
  print_section "Summary"

  local end_time=$(date +%s)
  local duration=$((end_time - START_TIME))

  print_info "Total execution time: ${duration}s"
  print_info "State saved to: ${STATE_FILE}"

  if [[ ${LOG_REMEDIATION} -eq 1 ]]; then
    print_info "Log file: ${LOG_FILE}"
  fi

  # Save state for next run
  save_state

  log_message "ORCHESTRATION_COMPLETE: duration=${duration}s"
}

# Main orchestration flow
main() {
  print_header "Hephaestus Unified Orchestrator"

  # Show mode information
  if [[ ${DRY_RUN} -eq 1 ]]; then
    print_warning "Running in DRY-RUN mode - no changes will be made"
  fi
  if [[ ${INTERACTIVE} -eq 1 ]]; then
    print_info "Running in INTERACTIVE mode"
  fi
  if [[ ${FAST_MODE} -eq 1 ]]; then
    print_info "Running in FAST mode - using cached validations"
  fi

  # Initialize
  init_logging

  # Check disk space
  if ! check_disk_space; then
    print_error "Cannot proceed - insufficient disk space"
    exit 1
  fi

  # Acquire lock for concurrent execution safety
  if ! acquire_lock; then
    exit 1
  fi

  # Load previous state
  load_state

  # Run orchestration phases
  phase_environment || {
    print_error "Environment phase failed"
    exit 1
  }
  phase_dependencies || {
    print_error "Dependency phase failed"
    exit 1
  }
  phase_quality
  phase_platform
  phase_summary

  # Release lock
  release_lock

  print_header "✓ Orchestration Complete"

  echo ""
  echo -e "${GREEN}All systems operational!${NC}"
  echo ""
  echo "Next steps:"
  echo "  • Run tests: uv run pytest"
  echo "  • Start development: uv run hephaestus --help"
  echo "  • View logs: cat ${LOG_FILE}"
  echo ""
}

# Handle script arguments
case "${1-}" in
--help | -h)
  echo "Hephaestus Unified Orchestrator"
  echo ""
  echo "Usage: $0 [options]"
  echo ""
  echo "Options:"
  echo "  --help, -h          Show this help message"
  echo "  --fast              Skip recently validated checks (use cache)"
  echo "  --skip-tests        Skip quality gate checks"
  echo "  --dry-run           Show what would be done"
  echo "  --interactive       Prompt before changes"
  echo ""
  echo "Environment Variables:"
  echo "  AUTO_REMEDIATE=1    Enable auto-remediation (default)"
  echo "  DRY_RUN=1           Dry-run mode"
  echo "  INTERACTIVE=1       Interactive mode"
  echo "  PERSIST_CONFIG=1    Persist settings to shell profile"
  echo "  FAST_MODE=1         Use cached validations"
  echo "  SKIP_TESTS=1        Skip quality checks"
  echo ""
  exit 0
  ;;
--fast)
  FAST_MODE=1
  shift
  ;;
--skip-tests)
  SKIP_TESTS=1
  shift
  ;;
--dry-run)
  DRY_RUN=1
  shift
  ;;
--interactive)
  INTERACTIVE=1
  shift
  ;;
esac

# Run main orchestration
main
