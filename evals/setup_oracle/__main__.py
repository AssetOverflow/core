"""CLI: print the setup-oracle report.

    python -m evals.setup_oracle

Exit 0 iff ``setup_wrong == 0`` — the gate the milestone rests on (a wrong reading must
never pass, and serving must not move while setup_wrong > 0).
"""

from __future__ import annotations

import json

from evals.setup_oracle.runner import run


def main() -> int:
    report = run()
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["setup_wrong"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
