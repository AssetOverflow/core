"""ADR-0136.S.4-post-rescan — invariant tests for refusal rescan v4.

v4 is the CURRENT snapshot (post-S.4).  Unlike v3 (which is now frozen and
asserted against disk), v4 tests re-run build_rescan() to confirm the live
parser still produces the v4 ledger — until S.5 lands and shifts more.
"""

from __future__ import annotations

import json
from pathlib import Path

from evals.gsm8k_math.train_sample.v1.rescan_v4 import build_rescan

_HERE = Path(__file__).resolve().parent.parent
_RESCAN_V4 = _HERE / "evals/gsm8k_math/train_sample/v1/refusal_rescan_v4.json"
_TAXONOMY_V4 = _HERE / "evals/gsm8k_math/train_sample/v1/refusal_taxonomy_v4.json"


def test_wrong_is_zero() -> None:
    rescan, _ = build_rescan()
    assert rescan["summary"]["wrong"] == 0


def test_admission_set_unchanged() -> None:
    """S.4 did not change the admission set: {0014, 0018, 0042}."""
    rescan, _ = build_rescan()
    admitted = {
        c["case_id"] for c in rescan["per_case"] if c["current_outcome"] == "admitted"
    }
    assert admitted == {
        "gsm8k-train-sample-v1-0014",
        "gsm8k-train-sample-v1-0018",
        "gsm8k-train-sample-v1-0042",
    }


def test_exactly_two_shifts_v3_to_v4() -> None:
    """S.4 shifted exactly two cases (gsm8k-0038, gsm8k-0046)."""
    rescan, _ = build_rescan()
    assert rescan["summary"]["barrier_shifted_v3_to_v4"] == 2
    shifted = sorted(
        c["case_id"] for c in rescan["per_case"] if c["barrier_shifted"]
    )
    assert shifted == [
        "gsm8k-train-sample-v1-0038",
        "gsm8k-train-sample-v1-0046",
    ]


def test_gsm8k_0038_now_refuses_on_sentence_2() -> None:
    rescan, _ = build_rescan()
    case = next(
        c for c in rescan["per_case"]
        if c["case_id"] == "gsm8k-train-sample-v1-0038"
    )
    assert case["previous_first_refusal"].startswith("In a building")
    assert case["current_first_refusal"].startswith("There are three times")
    assert case["previous_primary_barrier"] == "novel_initial_form"
    assert case["current_primary_barrier"] == "compound_comparative"


def test_gsm8k_0046_now_refuses_on_sentence_2() -> None:
    rescan, _ = build_rescan()
    case = next(
        c for c in rescan["per_case"]
        if c["case_id"] == "gsm8k-train-sample-v1-0046"
    )
    assert case["previous_first_refusal"].startswith("A school has 100 students")
    assert case["current_first_refusal"].startswith("Half of the students")
    assert case["previous_primary_barrier"] == "novel_initial_form"
    assert case["current_primary_barrier"] == "fraction_operand"


def test_artifacts_deterministic() -> None:
    r1, t1 = build_rescan()
    r2, t2 = build_rescan()
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
    assert json.dumps(t1, sort_keys=True) == json.dumps(t2, sort_keys=True)


def test_taxonomy_v4_has_50_entries() -> None:
    _, taxonomy = build_rescan()
    assert len(taxonomy["per_case"]) == 50


def test_disk_artifacts_match_freshly_computed() -> None:
    if not _RESCAN_V4.exists() or not _TAXONOMY_V4.exists():
        return
    rescan, taxonomy = build_rescan()
    on_disk_rescan = json.loads(_RESCAN_V4.read_text(encoding="utf-8"))
    on_disk_taxonomy = json.loads(_TAXONOMY_V4.read_text(encoding="utf-8"))
    assert on_disk_rescan == rescan
    assert on_disk_taxonomy == taxonomy
