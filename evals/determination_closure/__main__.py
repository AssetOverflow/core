"""CLI: print the determination-closure falsification report.

    python -m evals.determination_closure [depth]
"""

from __future__ import annotations

import json
import sys

from evals.determination_closure.runner import run


def main() -> int:
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    report = run(depth)
    print(json.dumps(report, indent=2))
    return 0 if report["falsification_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
