"""ADR-0163 Phase C — admissibility replay-gate tests.

Pins:
- the helper runs the cognition + capability-axis + GSM8K train_sample lanes
- baseline cache hit: a second call against the same corpus digest does NOT
  re-run the baselines
- cache invalidation: changing the corpus digest re-runs baselines
- WRONG-COUNT INVARIANT: a candidate run that lifts the GSM8K train_sample
  wrong count is rejected with the typed regressed_metrics entry
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from teaching.exemplar_ingest import load_exemplar_corpus
from teaching.recognizer_synthesis import synthesize_recognizer
import teaching.replay as replay_mod
from teaching.replay import (
    AdmissibilityReplayEvidence,
    run_admissibility_replay_gate,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent
_EXEMPLAR = (
    _REPO_ROOT / "teaching" / "admissibility_exemplars" / "rate_with_currency_v1.jsonl"
)


@pytest.fixture(autouse=True)
def _clean_baseline_cache() -> Any:
    """Each test starts with a clean baseline cache."""
    replay_mod._BASELINE_CACHE.clear()
    yield
    replay_mod._BASELINE_CACHE.clear()


def _stub_capability_axes() -> dict[str, dict[str, int]]:
    return {
        "G1_verb_classes": {"correct": 20, "wrong": 0, "refused": 0},
        "G2_comparatives": {"correct": 29, "wrong": 0, "refused": 0},
        "G3_numerics": {"correct": 20, "wrong": 0, "refused": 6},
        "G4_multi_clause": {"correct": 32, "wrong": 0, "refused": 0},
        "G5_aggregate": {"correct": 20, "wrong": 0, "refused": 0},
        "S1_rate_events": {"correct": 20, "wrong": 0, "refused": 0},
    }


def _stub_gsm8k() -> dict[str, int]:
    return {"correct": 3, "wrong": 0, "refused": 47}


def _stub_cognition() -> dict[str, float]:
    return {
        "intent_accuracy": 1.0,
        "surface_groundedness": 1.0,
        "term_capture_rate": 1.0,
        "versor_closure_rate": 1.0,
    }


def _spec() -> Any:
    return synthesize_recognizer(load_exemplar_corpus(_EXEMPLAR))


# ---------------------------------------------------------------------------
# Happy path: every lane wrong=0 → replay_equivalent=True
# ---------------------------------------------------------------------------


def test_gate_passes_when_no_lane_regresses() -> None:
    ev = run_admissibility_replay_gate(
        _spec(),
        _capability_axes_runner=_stub_capability_axes,
        _gsm8k_runner=_stub_gsm8k,
        _cognition_runner=_stub_cognition,
    )
    assert isinstance(ev, AdmissibilityReplayEvidence)
    assert ev.replay_equivalent is True
    assert ev.regressed_metrics == ()
    assert ev.wrong_count_delta == 0
    assert ev.capability_axes["G1_verb_classes"]["wrong"] == 0
    assert ev.gsm8k_train_sample == {"correct": 3, "wrong": 0, "refused": 47}


# ---------------------------------------------------------------------------
# Cache hit + invalidation
# ---------------------------------------------------------------------------


def test_baseline_cache_hit_on_second_call(tmp_path: Path) -> None:
    """Second call with the same active corpus digest reuses baselines."""
    active = tmp_path / "active_corpus.jsonl"
    active.write_text("{}\n", encoding="utf-8")

    cap_calls: list[int] = []
    gsm_calls: list[int] = []

    def _cap() -> dict[str, dict[str, int]]:
        cap_calls.append(1)
        return _stub_capability_axes()

    def _gsm() -> dict[str, int]:
        gsm_calls.append(1)
        return _stub_gsm8k()

    run_admissibility_replay_gate(
        _spec(),
        active_corpus_path=active,
        _capability_axes_runner=_cap,
        _gsm8k_runner=_gsm,
        _cognition_runner=_stub_cognition,
    )
    first_cap = len(cap_calls)
    first_gsm = len(gsm_calls)
    # Each first call runs the baseline AND the candidate -> 2 runs each.
    assert first_cap >= 2 and first_gsm >= 2

    run_admissibility_replay_gate(
        _spec(),
        active_corpus_path=active,
        _capability_axes_runner=_cap,
        _gsm8k_runner=_gsm,
        _cognition_runner=_stub_cognition,
    )
    # On the second call only the CANDIDATE run fires; baseline is cached.
    assert len(cap_calls) == first_cap + 1
    assert len(gsm_calls) == first_gsm + 1


def test_baseline_cache_invalidates_on_corpus_change(tmp_path: Path) -> None:
    active_a = tmp_path / "corpus_a.jsonl"
    active_a.write_text("a\n", encoding="utf-8")
    active_b = tmp_path / "corpus_b.jsonl"
    active_b.write_text("b\n", encoding="utf-8")

    cap_calls: list[int] = []
    gsm_calls: list[int] = []

    def _cap() -> dict[str, dict[str, int]]:
        cap_calls.append(1)
        return _stub_capability_axes()

    def _gsm() -> dict[str, int]:
        gsm_calls.append(1)
        return _stub_gsm8k()

    run_admissibility_replay_gate(
        _spec(),
        active_corpus_path=active_a,
        _capability_axes_runner=_cap,
        _gsm8k_runner=_gsm,
        _cognition_runner=_stub_cognition,
    )
    a_cap, a_gsm = len(cap_calls), len(gsm_calls)
    # Different corpus digest -> baseline re-runs.
    run_admissibility_replay_gate(
        _spec(),
        active_corpus_path=active_b,
        _capability_axes_runner=_cap,
        _gsm8k_runner=_gsm,
        _cognition_runner=_stub_cognition,
    )
    # The second call runs baseline + candidate again because the cache
    # was invalidated by the digest change.
    assert len(cap_calls) >= a_cap + 2
    assert len(gsm_calls) >= a_gsm + 2


# ---------------------------------------------------------------------------
# WRONG-COUNT INVARIANT (the load-bearing test for ADR-0163 §Constraint #1)
# ---------------------------------------------------------------------------


def test_wrong_count_invariant_auto_rejects_gsm8k_regression() -> None:
    """If the candidate lifts the GSM8K wrong count by ≥ 1, the gate
    rejects with the typed regressed_metrics entry — Phase D / E's
    wiring never reaches the operator review."""

    baseline_gsm = {"correct": 3, "wrong": 0, "refused": 47}
    candidate_gsm = {"correct": 3, "wrong": 1, "refused": 46}

    # Pre-populate the baseline cache so the runner returns the
    # candidate's elevated counts.  This mirrors a Phase D wiring that
    # mis-admits one previously-refused case as a wrong answer.
    call_count = {"n": 0}

    def _alternating_gsm() -> dict[str, int]:
        # First call: baseline.  Second call (live candidate): elevated.
        call_count["n"] += 1
        return baseline_gsm if call_count["n"] == 1 else candidate_gsm

    ev = run_admissibility_replay_gate(
        _spec(),
        _capability_axes_runner=_stub_capability_axes,
        _gsm8k_runner=_alternating_gsm,
        _cognition_runner=_stub_cognition,
    )
    assert ev.replay_equivalent is False
    assert "gsm8k_train_sample_wrong_count" in ev.regressed_metrics
    assert ev.wrong_count_delta == 1


def test_capability_axis_wrong_count_also_rejects() -> None:
    """Any capability axis whose candidate wrong>0 is a regression.

    G1..G5+S1 are wrong=0 today; a candidate that flips any to >0
    must be rejected.
    """
    elevated = _stub_capability_axes()
    elevated["G3_numerics"] = {"correct": 19, "wrong": 1, "refused": 6}

    call_count = {"n": 0}

    def _alt_caps() -> dict[str, dict[str, int]]:
        call_count["n"] += 1
        return _stub_capability_axes() if call_count["n"] == 1 else elevated

    ev = run_admissibility_replay_gate(
        _spec(),
        _capability_axes_runner=_alt_caps,
        _gsm8k_runner=_stub_gsm8k,
        _cognition_runner=_stub_cognition,
    )
    assert ev.replay_equivalent is False
    assert any(
        m.startswith("capability_axis_wrong:") for m in ev.regressed_metrics
    )


def test_cognition_lane_regression_also_rejects() -> None:
    """The cognition-lane regression detection from the older
    run_replay_equivalence path is preserved verbatim."""

    baseline = {
        "intent_accuracy": 1.0,
        "surface_groundedness": 1.0,
        "term_capture_rate": 1.0,
        "versor_closure_rate": 1.0,
    }
    candidate = {**baseline, "intent_accuracy": 0.9}

    call_count = {"n": 0}

    def _alt_cog() -> dict[str, float]:
        call_count["n"] += 1
        return baseline if call_count["n"] == 1 else candidate

    ev = run_admissibility_replay_gate(
        _spec(),
        _capability_axes_runner=_stub_capability_axes,
        _gsm8k_runner=_stub_gsm8k,
        _cognition_runner=_alt_cog,
    )
    assert ev.replay_equivalent is False
    assert "intent_accuracy" in ev.regressed_metrics
