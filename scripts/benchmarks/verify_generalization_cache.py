#!/usr/bin/env python3
"""CLI script to verify local generalization benchmark cache directories."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

# Resolve repository root and add to sys.path to support imports
script_path = Path(__file__).resolve()
repo_root = script_path.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from evals.generalization.cache_verifier import verify_local_generalization_cache  # noqa: E402



def main() -> None:
    # Explicit rejection check for download/fetch flags before argparse
    forbidden = {"--download", "--fetch", "--pull"}
    for arg in sys.argv[1:]:
        if arg in forbidden:
            print(
                f"Error: Flag {arg} is not supported. Fetching or downloading dataset content is forbidden by policy.",
                file=sys.stderr,
            )
            sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Verify local generalization benchmark cache."
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only validate manifests metadata without requiring cache presence.",
    )
    parser.add_argument(
        "--require-present",
        action="store_true",
        help="Require all local cache directories to exist.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print report in deterministic JSON format.",
    )

    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent.parent
    manifests_dir = repo_root / "evals" / "generalization" / "manifests"

    try:
        report = verify_local_generalization_cache(
            repo_root=repo_root,
            manifests_dir=manifests_dir,
            require_present=args.require_present,
        )
    except Exception as exc:
        print(f"Verification Failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        report_dict = asdict(report)
        print(json.dumps(report_dict, indent=2, sort_keys=True))
    else:
        print(
            f"Generalization Cache Verification Report (Policy: {report.policy_version})"
        )
        print("=" * 80)
        for record in report.records:
            status = "RUNNABLE" if record.runnable else "NOT RUNNABLE"
            print(f"Dataset: {record.dataset}")
            print(f"  Manifest: {record.manifest_path}")
            print(f"  Cache Path: {record.local_cache}")
            print(f"  Exists: {record.exists}")
            print(f"  License Ready: {record.license_ready}")
            print(f"  Checksum Ready: {record.checksum_ready}")
            print(f"  Status: {status}")
            if record.reason_codes:
                print(f"  Reasons: {', '.join(record.reason_codes)}")
            print("-" * 80)
        print(f"All datasets runnable: {report.all_runnable}")

    # If --require-present is set, exit non-zero if any dataset is not runnable
    if args.require_present and not report.all_runnable:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
