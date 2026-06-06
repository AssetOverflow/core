"""CLI: print the determination-estimation calibration report.

    python -m evals.determination_estimation

Exit 0 iff the gate DISCRIMINATES (the symmetric class earns SERVE, the directed one
does not) — the falsification handle for Step E's calibration claim.
"""

from __future__ import annotations

import json

from evals.determination_estimation.runner import run


def main() -> int:
    report = run()
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["gate_discriminates"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
