"""CLI: validate the R3 rate gold, or grade the R3 reader against it.

    python -m evals.rate_oracle           # validate rate_gold.jsonl; exit 0 iff invalid == 0
    python -m evals.rate_oracle reader    # grade the reader; exit 0 iff setup_wrong == 0
                                          #   and reason_mismatch == 0
"""

from __future__ import annotations

import json
import sys

from evals.rate_oracle.runner import run, run_reader


def main() -> int:
    lane = sys.argv[1] if len(sys.argv) > 1 else ""
    if lane == "reader":
        report = run_reader()
        ok = report["setup_wrong"] == 0 and report["reason_mismatch"] == 0
    else:
        report = run()
        ok = report["invalid"] == 0
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
