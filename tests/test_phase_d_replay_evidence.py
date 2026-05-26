"""ADR-0163 Phase D — replay-evidence gate under wired registry.

Pins:
- synthesize a registry of three accepted recognizers (the live
  Phase C pending proposals' spec content)
- run the admissibility replay gate against the patched candidate-graph
- assert wrong_count_delta == 0 (the load-bearing wrong=0 invariant)
- assert each accepted recognizer's match function admits ≥ 1
  GSM8K train_sample sentence — the wiring is consequential, not
  inert
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import generate.math_candidate_graph as cg
import teaching.replay as replay_mod
from generate.recognizer_match import match as _matcher
from generate.recognizer_registry import RatifiedRecognizer
from tests._phase_d_fixture import build_synthetic_registry


_REPO_ROOT = Path(__file__).resolve().parent.parent
_GSM8K_CASES = _REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "cases.jsonl"


@pytest.fixture(autouse=True)
def _clean_replay_cache() -> Any:
    replay_mod._BASELINE_CACHE.clear()
    yield
    replay_mod._BASELINE_CACHE.clear()


@pytest.fixture(scope="module")
def synthetic_registry() -> tuple[RatifiedRecognizer, ...]:
    return build_synthetic_registry()


def test_replay_gate_wrong_count_delta_zero_under_synthetic_registry(
    monkeypatch: pytest.MonkeyPatch,
    synthetic_registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """The load-bearing Phase D invariant test.

    Patch the candidate-graph's registry loader to return the
    synthetic registry, then run the full admissibility replay gate.
    The wrong_count_delta must be zero — Phase D's wiring is
    refused→(refused-or-correct), never refused→wrong.
    """
    monkeypatch.setattr(
        cg, "_load_ratified_registry_or_empty", lambda: synthetic_registry,
    )
    # The replay gate runs both baseline and candidate against the
    # same patched candidate-graph, so both lanes see the synthetic
    # registry.  This still proves wrong=0 holds under the wiring;
    # the operator's live-log run will compare against the unwired
    # baseline after ratification.
    spec_placeholder = {"shape_category": "rate_with_currency"}  # the gate ignores its content in Phase D
    evidence = replay_mod.run_admissibility_replay_gate(spec_placeholder)
    assert evidence.replay_equivalent is True, (
        f"replay gate rejected under synthetic registry: "
        f"regressed_metrics={evidence.regressed_metrics}"
    )
    assert evidence.wrong_count_delta == 0
    assert evidence.gsm8k_train_sample["wrong"] == 0
    for axis_id, counts in evidence.capability_axes.items():
        assert counts["wrong"] == 0, (
            f"{axis_id} regressed wrong=0 under synthetic registry: {counts}"
        )


def test_each_recognizer_admits_at_least_one_train_sample_sentence(
    synthetic_registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """Phase D's wiring is consequential, not inert.

    For each ratified recognizer, the matcher must admit at least
    one statement in the GSM8K train_sample.  Proves the wiring path
    will actually shift refusal causes once Phase E's parser-side
    consumption lands.
    """
    cases = [
        json.loads(line)
        for line in _GSM8K_CASES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    statements: list[str] = []
    for case in cases:
        text = case["question"]
        for s in text.replace("?", ".").split("."):
            s = s.strip()
            if s:
                statements.append(s)

    per_recognizer_hits: dict[str, int] = {
        r.shape_category.value: 0 for r in synthetic_registry
    }
    for statement in statements:
        m = _matcher(statement, synthetic_registry)
        if m is not None:
            per_recognizer_hits[m.category.value] += 1

    for category, count in per_recognizer_hits.items():
        assert count >= 1, (
            f"recognizer for {category!r} admitted zero train_sample "
            "sentences — wiring is inert for this category"
        )
