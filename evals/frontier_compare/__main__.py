from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import format_human_report, run_all, run_suite, write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m evals.frontier_compare",
        description="Run CORE's Wave-1 frontier comparison benchmark suites.",
    )
    parser.add_argument(
        "--suite",
        choices=("determinism", "truth_lock", "axis_orthogonality", "all"),
        default="all",
        help="Benchmark suite to run. Defaults to all.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the stable machine-readable JSON report.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional path to write the JSON report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_all() if args.suite == "all" else run_suite(args.suite)

    if args.report is not None:
        write_report(report, args.report)

    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(format_human_report(report))
    return 0 if report.passed else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
