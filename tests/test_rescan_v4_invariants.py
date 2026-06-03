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


def test_admission_set_grew_monotonically_over_v3() -> None:
    """The reader admits the v3 set plus three new *correct* solves.

    v3 admitted {0014, 0018, 0042}. Later capability waves added three correct
    admissions (0003, 0021, 0024) — the +3 that moved the serving metric from
    3 to 6. No v3 admission was lost (monotonic), and wrong stays 0
    (test_wrong_is_zero), so every gain is a sound solve.
    """
    rescan, _ = build_rescan()
    admitted = {
        c["case_id"] for c in rescan["per_case"] if c["current_outcome"] == "admitted"
    }
    v3_admitted = {
        "gsm8k-train-sample-v1-0014",
        "gsm8k-train-sample-v1-0018",
        "gsm8k-train-sample-v1-0042",
    }
    # No regression: every case v3 solved is still solved.
    assert v3_admitted <= admitted
    assert admitted == v3_admitted | {
        "gsm8k-train-sample-v1-0003",
        "gsm8k-train-sample-v1-0021",
        "gsm8k-train-sample-v1-0024",
    }


def test_barrier_shifts_from_v3_baseline() -> None:
    """The live reader has diverged from the v3 baseline on ten cases.

    S.4 shifted two (0038, 0046). Later capability waves (0163-D.2, 0174, 0178,
    0191, 0192) advanced the reader past five more v3-era barriers (0019, 0023,
    0025, 0027, 0047) — still refusing, one sentence deeper — and turned three
    refusals into correct admissions (0003, 0021, 0024). All ten are
    soundness-preserving (wrong stays 0); the five still-refusing shifts each
    carry an override in _V4_BARRIER_OVERRIDES.
    """
    rescan, _ = build_rescan()
    # 10 = 7 first-refusal/barrier shifts + 3 refused->admitted transitions
    # (0003, 0021, 0024), which also count as shifts (outcome changed).
    assert rescan["summary"]["barrier_shifted_v3_to_v4"] == 10
    shifted = sorted(
        c["case_id"] for c in rescan["per_case"] if c["barrier_shifted"]
    )
    assert shifted == [
        "gsm8k-train-sample-v1-0003",
        "gsm8k-train-sample-v1-0019",
        "gsm8k-train-sample-v1-0021",
        "gsm8k-train-sample-v1-0023",
        "gsm8k-train-sample-v1-0024",
        "gsm8k-train-sample-v1-0025",
        "gsm8k-train-sample-v1-0027",
        "gsm8k-train-sample-v1-0038",
        "gsm8k-train-sample-v1-0046",
        "gsm8k-train-sample-v1-0047",
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
