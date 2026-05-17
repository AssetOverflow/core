"""ADR-0023 — admissibility trace + trace-hash determinism tests.

Pure-unit checks on the trace surface introduced by ADR-0023.  No
runtime, no pipeline; just the typed dataclasses and the hashing
helpers in ``core.cognition.trace``.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.cognition.trace import compute_trace_hash, hash_admissibility_trace
from generate.admissibility import (
    AdmissibilityRegion,
    AdmissibilityTraceStep,
    AdmissibilityVerdict,
    check_transition,
    region_from_relation_chain,
)


def _step(
    *,
    step_index: int = 0,
    region_label: str = "region",
    region_source: str = "relation",
    candidates_before: tuple[int, ...] = (1, 2, 3),
    candidates_after: tuple[int, ...] = (2, 3),
    selected_index: int = 2,
    selected_word: str = "beta",
    admitted: bool = True,
    reason: str = "ok",
) -> AdmissibilityTraceStep:
    return AdmissibilityTraceStep(
        step_index=step_index,
        region_label=region_label,
        region_source=region_source,
        candidates_before=candidates_before,
        candidates_after=candidates_after,
        selected_index=selected_index,
        selected_word=selected_word,
        verdict=AdmissibilityVerdict(
            admitted=admitted,
            score=0.42,
            region_label=region_label,
            reason=reason,
        ),
    )


class TestHashAdmissibilityTrace:
    def test_empty_trace_returns_empty_string(self) -> None:
        assert hash_admissibility_trace(()) == ""

    def test_same_trace_same_hash(self) -> None:
        trace = (_step(step_index=0), _step(step_index=1, selected_word="gamma"))
        assert hash_admissibility_trace(trace) == hash_admissibility_trace(trace)

    def test_mutation_changes_hash(self) -> None:
        original = (_step(step_index=0),)
        mutated = (_step(step_index=0, selected_word="zeta"),)
        assert hash_admissibility_trace(original) != hash_admissibility_trace(mutated)

    def test_reason_change_changes_hash(self) -> None:
        original = (_step(reason="ok"),)
        mutated = (_step(reason="below threshold"),)
        assert hash_admissibility_trace(original) != hash_admissibility_trace(mutated)


class TestComputeTraceHashBackwardCompat:
    """Pre-ADR-0023 calls (without the new kwargs) must produce the
    *exact* hash they would have produced before ADR-0023, so existing
    recorded turn hashes do not silently drift."""

    def _baseline_kwargs(self) -> dict[str, object]:
        return {
            "input_text": "hello",
            "filtered_tokens": ("hello",),
            "surface": "hi",
            "walk_surface": "hi",
            "articulation_surface": "hi",
            "dialogue_role": "assert",
            "versor_condition": 1e-9,
            "vault_hits": 0,
        }

    def test_default_kwargs_byte_preserved(self) -> None:
        baseline = compute_trace_hash(**self._baseline_kwargs())
        with_defaults = compute_trace_hash(
            **self._baseline_kwargs(),
            admissibility_trace_hash="",
            ratification_outcome="",
            region_was_unconstrained=True,
        )
        assert baseline == with_defaults

    def test_non_default_trace_hash_changes_hash(self) -> None:
        baseline = compute_trace_hash(**self._baseline_kwargs())
        with_trace = compute_trace_hash(
            **self._baseline_kwargs(),
            admissibility_trace_hash="deadbeef",
        )
        assert baseline != with_trace

    def test_non_default_ratification_outcome_changes_hash(self) -> None:
        baseline = compute_trace_hash(**self._baseline_kwargs())
        ratified = compute_trace_hash(
            **self._baseline_kwargs(),
            ratification_outcome="ratified",
        )
        assert baseline != ratified

    def test_region_was_constrained_changes_hash(self) -> None:
        baseline = compute_trace_hash(**self._baseline_kwargs())
        constrained = compute_trace_hash(
            **self._baseline_kwargs(),
            region_was_unconstrained=False,
        )
        assert baseline != constrained


class TestRegionFromRelationChainTrace:
    """End-to-end: a region built from real versors yields verdicts that
    round-trip through ``AdmissibilityTraceStep`` and hash deterministically.
    """

    def _versor(self, seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed)
        return rng.standard_normal(32).astype(np.float32)

    def test_verdict_round_trips_through_step(self) -> None:
        anchors = [self._versor(i) for i in range(3)]
        region = region_from_relation_chain(anchors, label="chain")
        verdict = check_transition(
            region, candidate_index=7, candidate_versor=anchors[0]
        )
        step = AdmissibilityTraceStep(
            step_index=0,
            region_label=region.label,
            region_source=region.source.value,
            candidates_before=(7, 8),
            candidates_after=(7,),
            selected_index=7,
            selected_word="alpha",
            verdict=verdict,
        )
        canonical = step.canonical()
        assert canonical["region_label"] == "chain"
        assert canonical["verdict_admitted"] == verdict.admitted

    def test_unconstrained_region_admits_any(self) -> None:
        region = AdmissibilityRegion(label="unconstrained")
        verdict = check_transition(
            region, candidate_index=0, candidate_versor=np.zeros(32, dtype=np.float32)
        )
        assert verdict.admitted is True


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
