"""CLI: print the edge-budget cost report.

    python -m evals.edge_budget [n_turns]
"""

from __future__ import annotations

import json
import sys

from evals.edge_budget.runner import run


def main() -> int:
    n_turns = int(sys.argv[1]) if len(sys.argv) > 1 else None
    report = run() if n_turns is None else run(n_turns)
    print(json.dumps(report, indent=2))
    return 0 if report["edge_budget_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
