#!/usr/bin/env python3
"""Deterministic GSM8K train-sample sealed attempt scout (ADR-0175 S1).

Dual-scores train_sample cases with serving vs sealed resolve_pooled scorers.
Measurement-only — never writes report.json unless caller passes --out.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evals.gsm8k_math.train_sample.v1.runner import _CASES_PATH, _load_cases
from evals.gsm8k_math.train_sample.v1.scout import (
    build_scout_summary,
    render_markdown,
    write_jsonl,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GSM8K sealed attempt scout")
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
        "--out",
        type=Path,
        default=None,
        help="Optional JSONL output path (never writes repo artifacts by default)",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Skip markdown summary block",
    )
    parser.add_argument(
        "--no-rows",
        action="store_true",
        help="Omit per-case rows from JSON output",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="Emit only top N lift recommendations",
    )
    args = parser.parse_args(argv)

    if not args.cases.exists():
        print(f"ERROR: cases file not found: {args.cases}", file=sys.stderr)
        return 1

    cases = _load_cases(args.cases)
    if args.limit is not None:
        cases = sorted(cases, key=lambda c: c["case_id"])[: args.limit]

    summary = build_scout_summary(
        cases,
        cases_source=str(args.cases),
        include_rows=not args.no_rows,
        top_recommendations=args.top,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not args.json_only:
        print("\n---\n")
        print(render_markdown(summary))

    if args.out is not None:
        rows = summary.get("rows", [])
        write_jsonl(rows, args.out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())