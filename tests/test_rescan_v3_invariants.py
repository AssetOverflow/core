"""ADR-0136.S.3-post-rescan — invariant tests for refusal rescan v3."""

from __future__ import annotations

import json
from pathlib import Path

from evals.gsm8k_math.train_sample.v1.rescan_v3 import build_rescan

_HERE = Path(__file__).resolve().parent.parent
_RESCAN_V3 = _HERE / "evals/gsm8k_math/train_sample/v1/refusal_rescan_v3.json"
_TAXONOMY_V3 = _HERE / "evals/gsm8k_math/train_sample/v1/refusal_taxonomy_v3.json"


def test_wrong_is_zero() -> None:
    """GSM8K probe under v3 must hold wrong == 0."""
    rescan, _ = build_rescan()
    assert rescan["summary"]["wrong"] == 0


def test_admission_set_unchanged() -> None:
    """S.3 did not change the admission set: {0014, 0018, 0042}."""
    rescan, _ = build_rescan()
    admitted = {
        c["case_id"] for c in rescan["per_case"] if c["current_outcome"] == "admitted"
    }
    assert admitted == {
        "gsm8k-train-sample-v1-0014",
        "gsm8k-train-sample-v1-0018",
        "gsm8k-train-sample-v1-0042",
    }


def test_exactly_one_shift_v2_to_v3() -> None:
    """S.3 shifted exactly one case (gsm8k-0010)."""
    rescan, _ = build_rescan()
    assert rescan["summary"]["barrier_shifted_v2_to_v3"] == 1
    shifted = [c["case_id"] for c in rescan["per_case"] if c["barrier_shifted"]]
    assert shifted == ["gsm8k-train-sample-v1-0010"]


def test_gsm8k_0010_now_refuses_on_sentence_2() -> None:
    """gsm8k-0010 first-refusal moved from sentence 1 to sentence 2."""
    rescan, _ = build_rescan()
    case = next(
        c for c in rescan["per_case"]
        if c["case_id"] == "gsm8k-train-sample-v1-0010"
    )
    assert case["previous_first_refusal"].startswith("Yun had 20 paperclips")
    assert case["current_first_refusal"].startswith("Marion has 1/4")
    assert case["previous_primary_barrier"] == "compound_statement"
    assert case["current_primary_barrier"] == "fraction_operand"


def test_artifacts_deterministic() -> None:
    """Two runs of build_rescan() produce byte-equal artifacts."""
    r1, t1 = build_rescan()
    r2, t2 = build_rescan()
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
    assert json.dumps(t1, sort_keys=True) == json.dumps(t2, sort_keys=True)


def test_taxonomy_v3_has_50_entries() -> None:
    _, taxonomy = build_rescan()
    assert len(taxonomy["per_case"]) == 50


def test_disk_artifacts_match_freshly_computed() -> None:
    """If rescan v3 was committed, disk artifacts must match a fresh run."""
    if not _RESCAN_V3.exists() or not _TAXONOMY_V3.exists():
        return
    rescan, taxonomy = build_rescan()
    on_disk_rescan = json.loads(_RESCAN_V3.read_text(encoding="utf-8"))
    on_disk_taxonomy = json.loads(_TAXONOMY_V3.read_text(encoding="utf-8"))
    assert on_disk_rescan == rescan
    assert on_disk_taxonomy == taxonomy
