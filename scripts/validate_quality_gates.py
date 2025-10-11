#!/usr/bin/env python3
"""Comprehensive quality gate validation script.

This script runs all quality checks defined in the Hephaestus project
to ensure frontier quality standards are met.

Usage:
    python scripts/validate_quality_gates.py

Exit codes:
    0: All quality gates passed
    1: One or more quality gates failed
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Literal


@dataclass
class QualityGate:
    """Represents a quality gate check."""

    name: str
    command: list[str]
    required: bool = True
    description: str = ""
    category: Literal["testing", "linting", "typing", "security", "build", "custom"] = "custom"


# Define all quality gates
QUALITY_GATES = [
    QualityGate(
        name="Pytest with Coverage",
        command=["pytest"],
        required=True,
        description="Run test suite with coverage ≥85%",
        category="testing",
    ),
    QualityGate(
        name="Ruff Check",
        command=["ruff", "check", "."],
        required=True,
        description="Lint code with Ruff",
        category="linting",
    ),
    QualityGate(
        name="Ruff Isort Check",
        command=["ruff", "check", "--select", "I", "."],
        required=True,
        description="Ensure imports stay sorted via Ruff isort rules",
        category="linting",
    ),
    QualityGate(
        name="Ruff Format Check",
        command=["ruff", "format", "--check", "."],
        required=True,
        description="Check code formatting with Ruff",
        category="linting",
    ),
    QualityGate(
        name="YAML Lint",
        command=[
            "yamllint",
            "-c",
            ".yamllint",
            ".github/",
            ".pre-commit-config.yaml",
            "hephaestus-toolkit/",
        ],
        required=True,
        description="Lint YAML files with yamllint",
        category="linting",
    ),
    QualityGate(
        name="Mypy Type Check",
        command=["mypy", "src", "tests"],
        required=True,
        description="Static type checking with Mypy",
        category="typing",
    ),
    QualityGate(
        name="Nested Decorator Check",
        command=["python3", "scripts/lint_nested_decorators.py", "src/hephaestus"],
        required=True,
        description="Ensure no nested Typer command decorators",
        category="custom",
    ),
    QualityGate(
        name="Workflow Lint (actionlint)",
        command=["bash", "scripts/run_actionlint.sh"],
        required=True,
        description="Validate GitHub Actions workflows",
        category="linting",
    ),
    QualityGate(
        name="Build Artifacts",
        command=["python3", "-m", "build"],
        required=True,
        description="Build distribution artifacts",
        category="build",
    ),
    QualityGate(
        name="pip-audit",
        command=["pip-audit", "--strict", "--ignore-vuln", "GHSA-4xh5-x5gv-qwph"],
        required=False,  # Known to fail in containers without SSL trust chain
        description="Security audit of dependencies",
        category="security",
    ),
]


def run_quality_gate(gate: QualityGate, verbose: bool = True) -> bool:
    """Run a single quality gate check."""
    if verbose:
        print(f"\n{'=' * 80}")
        print(f"Running: {gate.name}")
        print(f"Description: {gate.description}")
        print(f"Category: {gate.category}")
        print(f"Command: {' '.join(gate.command)}")
        print(f"{'=' * 80}\n")

    try:
        result = subprocess.run(
            gate.command,
            capture_output=True,  # Always capture to check for errors
            text=True,
            check=False,
        )

        # Print output if verbose
        if verbose:
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="", file=sys.stderr)

        if result.returncode == 0:
            print(f"✅ {gate.name} PASSED")
            return True
        else:
            # Check if this is a missing Python module error
            is_python_module = "-m" in gate.command
            stderr_has_no_module = result.stderr and "No module named" in result.stderr
            stdout_has_no_module = result.stdout and "No module named" in result.stdout

            if is_python_module and (stderr_has_no_module or stdout_has_no_module):
                module_name = gate.command[gate.command.index("-m") + 1]
                print(f"⚙️  {gate.name} - Installing missing module: {module_name}")

                try:
                    install_result = subprocess.run(
                        ["pip", "install", module_name],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    if install_result.returncode == 0:
                        print(f"✅ {module_name} installed successfully, retrying...")
                        # Retry the command
                        retry_result = subprocess.run(
                            gate.command,
                            capture_output=True,
                            text=True,
                            check=False,
                        )

                        # Print output if verbose
                        if verbose:
                            if retry_result.stdout:
                                print(retry_result.stdout, end="")
                            if retry_result.stderr:
                                print(retry_result.stderr, end="", file=sys.stderr)

                        if retry_result.returncode == 0:
                            print(f"✅ {gate.name} PASSED")
                            return True
                        else:
                            print(f"❌ {gate.name} FAILED after installing {module_name}")
                            if not verbose:
                                if retry_result.stdout:
                                    print(retry_result.stdout)
                                if retry_result.stderr:
                                    print(retry_result.stderr, file=sys.stderr)
                            return False
                    else:
                        print(f"⚠️  Failed to install {module_name}")
                        if install_result.stderr:
                            print(install_result.stderr, file=sys.stderr)
                        print(f"❌ {gate.name} FAILED")
                        return False
                except Exception as install_error:
                    print(f"⚠️  Error installing {module_name}: {install_error}")
                    print(f"❌ {gate.name} FAILED")
                    return False
            else:
                print(f"❌ {gate.name} FAILED")
                if not verbose:
                    if result.stdout:
                        print(result.stdout)
                    if result.stderr:
                        print(result.stderr, file=sys.stderr)
                return False

    except FileNotFoundError as e:
        print(f"⚠️  {gate.name} SKIPPED (command not found: {e})")
        return not gate.required
    except Exception as e:
        print(f"❌ {gate.name} ERROR: {e}")
        return False


def main() -> int:
    """Main entry point for quality gate validation."""
    print("🔍 Hephaestus Frontier Quality Gate Validation")
    print("=" * 80)

    results: dict[str, bool] = {}
    required_failed = []
    optional_failed = []

    for gate in QUALITY_GATES:
        passed = run_quality_gate(gate, verbose=True)
        results[gate.name] = passed

        if not passed:
            if gate.required:
                required_failed.append(gate.name)
            else:
                optional_failed.append(gate.name)

    # Print summary
    print("\n" + "=" * 80)
    print("📊 Quality Gate Summary")
    print("=" * 80)

    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)

    print(f"\nTotal: {passed_count}/{total_count} passed")

    if required_failed:
        print("\n❌ Required gates FAILED:")
        for gate_name in required_failed:
            print(f"  - {gate_name}")

    if optional_failed:
        print("\n⚠️  Optional gates failed (non-blocking):")
        for gate_name in optional_failed:
            print(f"  - {gate_name}")

    if not required_failed:
        print("\n✅ All required quality gates PASSED!")
        print("\nFrontier quality standards met.")
        return 0
    else:
        print("\n❌ Some required quality gates FAILED")
        print("\nPlease fix the failing checks before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
