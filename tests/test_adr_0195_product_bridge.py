"""ADR-0195 — serving-safe product promotion bridge.

The pooled derivation reader already solves GSM8K train-sample 0003 and 0021,
but it also commits known wrong products.  The bridge promotes only complete
pure-product readings with an aggregate product target and refuses the known
hazard surfaces.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.gsm8k_math.train_sample.v1.runner import (
    _CASES_PATH,
    _load_cases,
    build_report,
)
from generate.derivation.product_bridge import resolve_promotable_product
from generate.math_candidate_graph import parse_and_solve


def _case(case_suffix: str) -> dict:
    target = f"gsm8k-train-sample-v1-{case_suffix}"
    for line in Path(_CASES_PATH).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["case_id"] == target:
            return row
    raise AssertionError(f"missing train-sample case {target}")


@pytest.mark.parametrize("case_suffix, expected", [("0003", 864.0), ("0021", 450.0)])
def test_promotable_product_cases_resolve(case_suffix: str, expected: float) -> None:
    row = _case(case_suffix)
    resolution = resolve_promotable_product(row["question"])
    assert resolution is not None
    assert resolution.answer == expected

    result = parse_and_solve(row["question"])
    assert result.refusal_reason is None
    assert result.answer == expected


@pytest.mark.parametrize(
    "case_suffix",
    [
        "0011",  # profit target: divide/surplus, not product
        "0016",  # per-mile rate target
        "0018",  # rate scaling; served by the candidate graph, not this bridge
        "0019",  # insurance/coverage adjustment
        "0025",  # same-amount-as group total needs scalar + 1
        "0028",  # comma-number/percent/equation target
        "0032",  # percent-less time composition
        "0047",  # remaining-after-consumption target
    ],
)
def test_known_pooled_wrong_commits_are_not_promotable(case_suffix: str) -> None:
    row = _case(case_suffix)
    assert resolve_promotable_product(row["question"]) is None


def test_train_sample_lifts_two_products_without_wrong() -> None:
    report = build_report(_load_cases(_CASES_PATH))
    # ADR-0207 §5 step 2: serving lifted 6/44/0 -> 7/43/0 (cv-0005/0037 goal-residual).
    assert report["counts"] == {"correct": 7, "wrong": 0, "refused": 43}
    by_case = {row["case_id"]: row for row in report["per_case"]}
    assert by_case["gsm8k-train-sample-v1-0003"]["verdict"] == "correct"
    assert by_case["gsm8k-train-sample-v1-0021"]["verdict"] == "correct"
    assert by_case["gsm8k-train-sample-v1-0037"]["verdict"] == "correct"
    assert by_case["gsm8k-train-sample-v1-0050"]["verdict"] == "refused"
