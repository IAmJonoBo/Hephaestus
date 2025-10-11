#!/usr/bin/env python3
"""Wrapper for invoking the packaged Sigstore backfill implementation."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from hephaestus.backfill import (
    BackfillError,
    BackfillRunSummary,
    logger as backfill_logger,
    run_backfill,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for the backfill script."""

    parser = argparse.ArgumentParser(
        description="Backfill Sigstore bundles for historical releases",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform all steps except uploads (for testing)",
    )
    parser.add_argument(
        "--version",
        help="Backfill specific version only (default: all historical versions)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the standalone backfill helper."""

    args = parse_args(argv)

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        backfill_logger.error("GITHUB_TOKEN environment variable not set")
        backfill_logger.error("Set your token: export GITHUB_TOKEN=<your-token>")
        return 1

    try:
        summary: BackfillRunSummary = run_backfill(
            token=token,
            version=args.version,
            dry_run=args.dry_run,
        )
    except BackfillError as exc:
        backfill_logger.error("Backfill failed: %s", exc)
        return 1
    except Exception as exc:  # pragma: no cover - defensive
        backfill_logger.exception("Unexpected error during backfill: %s", exc)
        return 1

    if not summary.ok:
        failed_versions = ", ".join(entry["version"] for entry in summary.failures)
        if failed_versions:
            backfill_logger.error("Backfill failed for versions: %s", failed_versions)
        else:
            backfill_logger.error("Backfill encountered failures; see logs for details")
        return 1

    backfill_logger.info("Inventory updated at %s", summary.inventory_path)
    backfill_logger.info("All backfills completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
