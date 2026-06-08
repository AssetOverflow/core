"""CLI: validate the combined-rate gold ruler (CMB-a).

    python -m evals.combined_rate_oracle    # validate combined_rate_gold.jsonl; exit 0 iff invalid == 0

The reader grading lane (``reader`` arg) lands with the reader (CMB-c).
"""

from __future__ import annotations

import json

from evals.combined_rate_oracle.runner import run


def main() -> int:
    report = run()
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["invalid"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
