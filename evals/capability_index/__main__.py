"""On-demand: run the capability index over the composed lanes and print it.

Run:  PYTHONPATH=. .venv/bin/python -m evals.capability_index

Exits non-zero if the assert-mode invariant is violated (any domain committed a
wrong answer). The printed ``deterministic_digest`` is the freeze handle — the
baseline the autonomous-improvement loop must climb.
"""

from __future__ import annotations

import json
import sys

from evals.capability_index.adapters import collect_domain_results
from evals.capability_index.index import aggregate, index_to_dict


def main() -> int:
    collection = collect_domain_results()
    index = aggregate(list(collection.results))
    report = index_to_dict(index)
    report["not_covered"] = [
        {"adapter": name, "error": err} for name, err in collection.not_covered
    ]
    print(json.dumps(report, indent=2))
    return 0 if index.assert_mode_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
