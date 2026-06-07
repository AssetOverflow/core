"""CLI: print the setup-oracle report.

    python -m evals.setup_oracle          # the 15-case relational-metric setup gold
    python -m evals.setup_oracle r1       # the independent R1 gold (PR-5b)

Exit 0 iff ``setup_wrong == 0`` — the gate the milestone rests on (a wrong reading must
never pass, and serving must not move while setup_wrong > 0). For ``r1`` the reader is
expected to REFUSE the unsupported shapes (setup_refused), never misread them.
"""

from __future__ import annotations

import json
import sys

from evals.setup_oracle.runner import run, run_r1


def main() -> int:
    lane = sys.argv[1] if len(sys.argv) > 1 else ""
    report = run_r1() if lane == "r1" else run()
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["setup_wrong"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
