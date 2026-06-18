#!/usr/bin/env python3
"""GSM8K bounded experience flywheel — deterministic practice memory builder.

Reads sealed scout evidence and emits compact experience artifacts.  Never
mutates serving, report.json, packs, teaching corpus, or sealed practice lanes
unless an explicit --out path is provided by the operator.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evals.gsm8k_math.train_sample.v1.experience import (
    build_experience_report,
    load_compacted_from_report,
    write_experience_json,
    write_experience_jsonl,
)
from evals.gsm8k_math.train_sample.v1.runner import _CASES_PATH, _load_cases
from evals.gsm8k_math.train_sample.v1.scout import build_scout_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build bounded GSM8K experience flywheel artifact from scout"
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=_CASES_PATH,
        help="Path to cases.jsonl (default: train_sample)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Score only the first N cases (sorted by case_id)",
    )
    parser.add_argument(
        "--prior",
        type=Path,
        default=None,
        help="Optional prior experience report JSON for cross-run compaction",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional JSON output path (never writes repo artifacts by default)",
    )
    parser.add_argument(
        "--jsonl-out",
        type=Path,
        default=None,
        help="Optional JSONL output path for compacted case records",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Include pre-compaction raw records in JSON output",
    )
    args = parser.parse_args(argv)

    if not args.cases.exists():
        print(f"ERROR: cases file not found: {args.cases}", file=sys.stderr)
        return 1

    cases = _load_cases(args.cases)
    if args.limit is not None:
        cases = sorted(cases, key=lambda c: c["case_id"])[: args.limit]

    scout_summary = build_scout_summary(
        cases,
        cases_source=str(args.cases),
        include_rows=True,
    )

    prior_compacted = None
    if args.prior is not None:
        if not args.prior.exists():
            print(f"ERROR: prior report not found: {args.prior}", file=sys.stderr)
            return 1
        prior_payload = json.loads(args.prior.read_text(encoding="utf-8"))
        prior_compacted = load_compacted_from_report(prior_payload)

    report = build_experience_report(
        scout_summary,
        cases=cases,
        prior_compacted=prior_compacted,
        include_raw_records=args.include_raw,
    )
    print(json.dumps(report, indent=2, sort_keys=True))

    if args.out is not None:
        write_experience_json(report, args.out)
    if args.jsonl_out is not None:
        write_experience_jsonl(report, args.jsonl_out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())