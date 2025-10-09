"""Example gRPC client for Hephaestus Quality Service."""

from __future__ import annotations

import asyncio

import grpc

from hephaestus.api.grpc.protos import hephaestus_pb2, hephaestus_pb2_grpc


async def run_guard_rails_example() -> None:
    """Example: Run guard-rails quality pipeline."""
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = hephaestus_pb2_grpc.QualityServiceStub(channel)

        # Create request
        request = hephaestus_pb2.GuardRailsRequest(
            no_format=False,
            workspace=".",
            drift_check=True,
        )

        # Call service
        print("Running guard-rails...")
        response = await stub.RunGuardRails(request)

        # Display results
        print(f"\nSuccess: {response.success}")
        print(f"Duration: {response.duration:.2f}s")
        print(f"Task ID: {response.task_id}")
        print("\nQuality Gates:")
        for gate in response.gates:
            status = "✓" if gate.passed else "✗"
            print(f"  {status} {gate.name} ({gate.duration:.2f}s)")
            if gate.message:
                print(f"    {gate.message}")


async def run_guard_rails_streaming_example() -> None:
    """Example: Run guard-rails with streaming progress."""
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = hephaestus_pb2_grpc.QualityServiceStub(channel)

        # Create request
        request = hephaestus_pb2.GuardRailsRequest(
            no_format=False,
            workspace=".",
            drift_check=True,
        )

        # Call streaming service
        print("Running guard-rails with streaming progress...\n")
        async for progress in stub.RunGuardRailsStream(request):
            if progress.completed:
                print(f"\n✓ {progress.message}")
                break
            else:
                print(f"[{progress.progress}%] {progress.stage}: {progress.message}")


async def check_drift_example() -> None:
    """Example: Check for tool version drift."""
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = hephaestus_pb2_grpc.QualityServiceStub(channel)

        # Create request
        request = hephaestus_pb2.DriftRequest(workspace=".")

        # Call service
        print("Checking for drift...")
        response = await stub.CheckDrift(request)

        # Display results
        print(f"\nHas Drift: {response.has_drift}")
        if response.has_drift:
            print("\nDrifted Tools:")
            for drift in response.drifts:
                print(
                    f"  - {drift.tool}: {drift.installed_version} "
                    f"(expected {drift.expected_version})"
                )
            print("\nRemediation Commands:")
            for cmd in response.remediation_commands:
                print(f"  $ {cmd}")


async def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("Quality Service Examples")
    print("=" * 60)

    print("\n1. Run Guard-Rails (Blocking)")
    print("-" * 60)
    await run_guard_rails_example()

    print("\n\n2. Run Guard-Rails (Streaming)")
    print("-" * 60)
    await run_guard_rails_streaming_example()

    print("\n\n3. Check Drift")
    print("-" * 60)
    await check_drift_example()


if __name__ == "__main__":
    asyncio.run(main())
