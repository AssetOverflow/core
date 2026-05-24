"""ADR-0136.S.3-post-rescan — invariant tests for refusal rescan v3.

v3 is a SNAPSHOT in time. These tests assert against the frozen on-disk
artifacts only — they do NOT re-run build_rescan(), because the live
parser drifts away from the v3 baseline as new phases (S.4, S.5, …)
land. The next snapshot (v4+) is asserted by its own invariant file.
"""

from __future__ import annotations

import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
_RESCAN_V3 = _HERE / "evals/gsm8k_math/train_sample/v1/refusal_rescan_v3.json"
_TAXONOMY_V3 = _HERE / "evals/gsm8k_math/train_sample/v1/refusal_taxonomy_v3.json"


def _load_rescan() -> dict:
    return json.loads(_RESCAN_V3.read_text(encoding="utf-8"))


def _load_taxonomy() -> dict:
    return json.loads(_TAXONOMY_V3.read_text(encoding="utf-8"))


def test_v3_snapshot_wrong_is_zero() -> None:
    assert _load_rescan()["summary"]["wrong"] == 0


def test_v3_snapshot_admission_set() -> None:
    rescan = _load_rescan()
    admitted = {
        c["case_id"] for c in rescan["per_case"] if c["current_outcome"] == "admitted"
    }
    assert admitted == {
        "gsm8k-train-sample-v1-0014",
        "gsm8k-train-sample-v1-0018",
        "gsm8k-train-sample-v1-0042",
    }


def test_v3_snapshot_exactly_one_shift_v2_to_v3() -> None:
    rescan = _load_rescan()
    assert rescan["summary"]["barrier_shifted_v2_to_v3"] == 1
    shifted = [c["case_id"] for c in rescan["per_case"] if c["barrier_shifted"]]
    assert shifted == ["gsm8k-train-sample-v1-0010"]


def test_v3_snapshot_gsm8k_0010_shifted_to_fraction_operand() -> None:
    rescan = _load_rescan()
    case = next(
        c for c in rescan["per_case"]
        if c["case_id"] == "gsm8k-train-sample-v1-0010"
    )
    assert case["previous_first_refusal"].startswith("Yun had 20 paperclips")
    assert case["current_first_refusal"].startswith("Marion has 1/4")
    assert case["previous_primary_barrier"] == "compound_statement"
    assert case["current_primary_barrier"] == "fraction_operand"


def test_v3_snapshot_taxonomy_has_50_entries() -> None:
    assert len(_load_taxonomy()["per_case"]) == 50


def test_v3_snapshot_adr_tag() -> None:
    """Identifies which ADR produced this snapshot."""
    assert _load_rescan()["adr"] == "0136.S.3-post-rescan"
    assert _load_taxonomy()["adr"] == "0136.S.3-post-rescan"
