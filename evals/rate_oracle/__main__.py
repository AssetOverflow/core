"""CLI: validate the R3 rate gold.

    python -m evals.rate_oracle   # validate rate_gold.jsonl; exit 0 iff invalid == 0
"""

from __future__ import annotations

import json

from evals.rate_oracle.runner import run


def main() -> int:
    report = run()
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["invalid"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
