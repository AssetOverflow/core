from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.contemplation.runner import (
    contemplate_frontier_reports,
    write_contemplation_run,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m core.contemplation",
        description="Run ADR-0080 read-only contemplation over explicit evidence files.",
    )
    parser.add_argument(
        "reports",
        nargs="+",
        type=Path,
        help="frontier_compare JSON report path(s) to contemplate.",
    )
    parser.add_argument(
        "--pack-id",
        action="append",
        default=(),
        help="Optional pack id to include in the substrate snapshot. May repeat.",
    )
    parser.add_argument(
        "--note",
        action="append",
        default=(),
        help="Optional operator note included in the substrate snapshot. May repeat.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional output path for the contemplation run JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run = contemplate_frontier_reports(
        args.reports,
        pack_ids=tuple(args.pack_id or ()),
        notes=tuple(args.note or ()),
    )
    if args.report is not None:
        write_contemplation_run(run, args.report)
    print(json.dumps(run.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
