#!/usr/bin/env python3
"""Compile Protocol Buffer definitions for gRPC services."""

import subprocess
import sys
from pathlib import Path


def compile_protos() -> int:
    """Compile proto files to Python code.

    Returns:
        Exit code (0 for success)
    """
    proto_dir = Path(__file__).parent.parent / "src" / "hephaestus" / "api" / "grpc" / "protos"
    output_dir = proto_dir

    proto_files = list(proto_dir.glob("*.proto"))
    if not proto_files:
        print("No .proto files found", file=sys.stderr)
        return 1

    print(f"Compiling {len(proto_files)} proto file(s)...")

    for proto_file in proto_files:
        print(f"  - {proto_file.name}")

        # Compile proto file
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "grpc_tools.protoc",
                f"--proto_path={proto_dir}",
                f"--python_out={output_dir}",
                f"--grpc_python_out={output_dir}",
                f"--pyi_out={output_dir}",
                str(proto_file),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Error compiling {proto_file.name}:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            return result.returncode

    print("✓ Proto compilation successful")
    return 0


if __name__ == "__main__":
    sys.exit(compile_protos())
