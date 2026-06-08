"""CLI: validate the combined-rate gold ruler, or grade the CMB solver against it.

    python -m evals.combined_rate_oracle           # validate combined_rate_gold.jsonl; exit 0 iff invalid == 0
    python -m evals.combined_rate_oracle solver    # grade the solver (CMB-b); exit 0 iff no wrong

The reader grading lane (``reader`` arg) lands with the reader (CMB-c).
"""

from __future__ import annotations

import json
import sys

from evals.combined_rate_oracle.runner import run, run_solver


def main() -> int:
    lane = sys.argv[1] if len(sys.argv) > 1 else ""
    if lane == "solver":
        report = run_solver()
        ok = report["solved_wrong"] == 0 and report["refuse_wrong"] == 0
    else:
        report = run()
        ok = report["invalid"] == 0
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
