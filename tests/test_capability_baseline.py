"""Capability-index baseline freeze.

The committed baseline is the monotonic handle for the autonomous-improvement
loop. A digest change is intentional only when the baseline is deliberately
re-frozen after an accepted improvement.
"""

from __future__ import annotations

import json
from pathlib import Path

from evals.capability_index.adapters import collect_domain_results
from evals.capability_index.index import (
    DomainResult,
    aggregate,
    deterministic_digest,
    index_to_dict,
)


_BASELINE = (
    Path(__file__).resolve().parent.parent
    / "evals"
    / "capability_index"
    / "baseline.json"
)


def _live_report() -> dict:
    collection = collect_domain_results()
    index = aggregate(list(collection.results))
    report = index_to_dict(index)
    report["not_covered"] = [
        {"adapter": name, "error": err} for name, err in collection.not_covered
    ]
    return report


def test_capability_index_matches_frozen_baseline_digest() -> None:
    baseline = json.loads(_BASELINE.read_text(encoding="utf-8"))
    live = _live_report()

    assert live["wrong_total"] == 0
    assert live["assert_mode_valid"] is True
    assert live["not_covered"] == []
    assert live["deterministic_digest"] == baseline["deterministic_digest"]


def test_capability_baseline_digest_is_the_index_digest() -> None:
    baseline = json.loads(_BASELINE.read_text(encoding="utf-8"))
    rebuilt = aggregate([
        # Rebuild only from the frozen domain counts; rounded presentation
        # fields are intentionally ignored by deterministic_digest.
        DomainResult(
            domain=d["domain"],
            correct=int(d["correct"]),
            wrong=int(d["wrong"]),
            refused=int(d["refused"]),
        )
        for d in baseline["domains"]
    ])

    assert baseline["wrong_total"] == 0
    assert baseline["deterministic_digest"] == deterministic_digest(rebuilt)
