"""CLI: print the setup-oracle report.

    python -m evals.setup_oracle              # the 15-case relational-metric setup gold
    python -m evals.setup_oracle r1           # the independent R1 setup gold (PR-5b)
    python -m evals.setup_oracle r1-answers   # off-serving R1 answer lane (PR-6b)

Exit 0 iff the lane's wrong-critical counters are zero. For setup lanes that means
``setup_wrong == 0``. For ``r1-answers`` that means ``setup_wrong == wrong ==
gold_error == 0``; unsupported R1 fixtures may still refuse honestly.
"""

from __future__ import annotations

import json
import sys

from evals.setup_oracle.runner import run, run_r1, run_r1_answers


def main() -> int:
    lane = sys.argv[1] if len(sys.argv) > 1 else ""
    if lane == "r1":
        report = run_r1()
        ok = report["setup_wrong"] == 0
    elif lane in ("r1-answers", "r1_answers"):
        report = run_r1_answers()
        ok = report["setup_wrong"] == 0 and report["wrong"] == 0 and report["gold_error"] == 0
    else:
        report = run()
        ok = report["setup_wrong"] == 0
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
