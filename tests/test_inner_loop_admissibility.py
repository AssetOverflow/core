"""ADR-0024 — inner-loop per-rotor admissibility tests.

These tests exercise ``generate()`` with a stub vocab so we can
deterministically control selection order and the CGA inner-product
score of each candidate against the region's relation blade.  They
prove four properties stated in the ADR:

  1. Default ``inner_loop_admissibility=False`` preserves ADR-0023
     boundary-only behavior (no ``rejected_attempts`` recorded).
  2. With the flag on, a candidate whose verdict is *not* admitted is
     skipped and the next admitted candidate is selected; the
     rejected one shows up in the step's ``rejected_attempts``.
  3. Exhaustion (every admissible candidate rejected) raises
     ``ValueError`` with the region label embedded — the same shape
     ADR-0022 §2 commits to for empty admissible sets.
  4. Empty ``rejected_attempts`` is *not* folded into
     ``AdmissibilityTraceStep.canonical()``, so the trace hash stays
     byte-identical with ADR-0023 turns.
"""

from __future__ import annotations

import numpy as np
import pytest

from field.state import FieldState
from generate.admissibility import (
    AdmissibilityRegion,
    AdmissibilityTraceStep,
    AdmissibilityVerdict,
    RegionSource,
)
from generate.result import GenerationResult
from generate.stream import generate


def _basis_versor(weight_index: int) -> np.ndarray:
    """A 32-component versor with a single non-zero component.

    ``cga_inner`` is a dot-product over the 32-dim CGA basis (with the
    metric applied in algebra.cga), so two basis-aligned versors yield
    a positive score iff they share their non-zero component's grade
    sign under the metric.  We pick component 1 (e1, spatial, metric
    ``+1``) so the scores are predictable.
    """
    v = np.zeros(32, dtype=np.float32)
    v[1] = 1.0  # e1 — metric +1
    v[1] *= float(weight_index)
    return v


class _ControllableVocab:
    """Stub vocab whose ``nearest`` returns candidates in a fixed
    preference order so the test controls which one the walk sees
    first.

    Each word has a basis-aligned versor whose CGA inner product with
    the test region's blade we can predict deterministically.
    """

    def __init__(self, *, words: list[str], preference: list[int],
                 versor_signs: list[float]) -> None:
        assert len(words) == len(versor_signs)
        self._words = words
        self._preference = preference
        # Build per-word versors.  versor_signs[i] picks the sign on
        # the e1 component; positive ⇒ admitted vs a +e1 region blade,
        # negative ⇒ rejected.
        self._versors: list[np.ndarray] = []
        for sign in versor_signs:
            v = np.zeros(32, dtype=np.float32)
            v[1] = float(sign)
            self._versors.append(v)

    def __len__(self) -> int:
        return len(self._words)

    def nearest(self, F, exclude_idx: int = -1, exclude_indices=None,
                candidate_indices=None):
        blocked = set(exclude_indices or ())
        if candidate_indices is not None:
            allowed = {int(i) for i in candidate_indices}
        else:
            allowed = set(range(len(self._words)))
        for idx in self._preference:
            if idx == exclude_idx or idx in blocked or idx not in allowed:
                continue
            return self._words[idx], idx
        raise ValueError("No candidate word available after exclusions.")

    def get_versor_at(self, idx: int) -> np.ndarray:
        return self._versors[idx]

    def index_of(self, word: str) -> int:
        try:
            return self._words.index(word)
        except ValueError:  # pragma: no cover
            raise KeyError(word)


class _IdentityPersona:
    def apply(self, F: np.ndarray) -> np.ndarray:
        return F


def _initial_state(vocab: _ControllableVocab) -> FieldState:
    """Field state seeded with a +e1 versor so the rotor application
    is well-defined; we only care about selection in these tests."""
    F = np.zeros(32, dtype=np.float32)
    F[1] = 1.0
    return FieldState(
        F=F,
        node=0,
        step=0,
    )


def _positive_blade_region(allowed: tuple[int, ...]) -> AdmissibilityRegion:
    """Region whose blade scores positively for +e1 versors and
    negatively for -e1 versors, with the given admissible token set."""
    blade = np.zeros(32, dtype=np.float32)
    blade[1] = 1.0
    return AdmissibilityRegion(
        allowed_indices=np.asarray(allowed, dtype=np.int64),
        relation_blade=blade,
        source=RegionSource.RELATION,
        label="adr0024-test",
    )


class TestDefaultOffPreservesBehavior:
    def test_no_rejected_attempts_when_flag_off(self) -> None:
        # The "preferred" word has a -e1 versor (verdict rejected).
        # With inner-loop OFF, the walk still emits it; the trace
        # records the rejected verdict but no rejected_attempts.
        vocab = _ControllableVocab(
            words=["seed", "alpha", "beta"],
            preference=[1, 2],
            versor_signs=[+1.0, -1.0, +1.0],
        )
        result = generate(
            _initial_state(vocab),
            vocab,
            _IdentityPersona(),
            max_tokens=1,
            region=_positive_blade_region((1, 2)),
            inner_loop_admissibility=False,
        )
        assert result.tokens == ("alpha",)
        assert len(result.admissibility_trace) == 1
        step = result.admissibility_trace[0]
        assert step.rejected_attempts == ()
        # Boundary-only path: verdict still computed and recorded.
        assert step.verdict.admitted is False


class TestInnerLoopRejectionDrivesReselection:
    def test_rejected_candidate_skipped(self) -> None:
        # Preferred order is [alpha (rejected), beta (admitted)].
        # Inner loop should skip alpha and emit beta.
        vocab = _ControllableVocab(
            words=["seed", "alpha", "beta"],
            preference=[1, 2],
            versor_signs=[+1.0, -1.0, +1.0],
        )
        result = generate(
            _initial_state(vocab),
            vocab,
            _IdentityPersona(),
            max_tokens=1,
            region=_positive_blade_region((1, 2)),
            inner_loop_admissibility=True,
        )
        assert result.tokens == ("beta",)
        step = result.admissibility_trace[0]
        assert step.selected_index == 2
        assert step.selected_word == "beta"
        assert step.verdict.admitted is True
        # The rejected alpha should be in rejected_attempts with its
        # negative score recorded.
        assert len(step.rejected_attempts) == 1
        idx, word, score = step.rejected_attempts[0]
        assert (idx, word) == (1, "alpha")
        assert score < 0.0


class TestExhaustionRaisesHonestRefusal:
    def test_all_rejected_raises_value_error(self) -> None:
        # Both admissible candidates have -e1 versors so the region
        # rejects them both; inner loop must raise ValueError.
        vocab = _ControllableVocab(
            words=["seed", "alpha", "beta"],
            preference=[1, 2],
            versor_signs=[+1.0, -1.0, -1.0],
        )
        with pytest.raises(ValueError, match="adr0024-test"):
            generate(
                _initial_state(vocab),
                vocab,
                _IdentityPersona(),
                max_tokens=1,
                region=_positive_blade_region((1, 2)),
                inner_loop_admissibility=True,
            )


class TestCanonicalOmitsEmptyRejectedAttempts:
    def test_empty_rejected_attempts_not_in_canonical(self) -> None:
        # Construct a step with default (empty) rejected_attempts and
        # verify the canonical form does not include the new key —
        # this is what keeps ADR-0023 turn hashes byte-identical.
        step = AdmissibilityTraceStep(
            step_index=0,
            region_label="r",
            region_source="relation",
            candidates_before=(1, 2),
            candidates_after=(1, 2),
            selected_index=1,
            selected_word="x",
            verdict=AdmissibilityVerdict(
                admitted=True, score=0.0, region_label="r", reason="ok"
            ),
        )
        canonical = step.canonical()
        assert "rejected_attempts" not in canonical

    def test_non_empty_rejected_attempts_in_canonical(self) -> None:
        step = AdmissibilityTraceStep(
            step_index=0,
            region_label="r",
            region_source="relation",
            candidates_before=(1, 2),
            candidates_after=(1, 2),
            selected_index=2,
            selected_word="y",
            verdict=AdmissibilityVerdict(
                admitted=True, score=0.5, region_label="r", reason="ok"
            ),
            rejected_attempts=((1, "x", -0.25),),
        )
        canonical = step.canonical()
        assert canonical["rejected_attempts"] == [[1, "x", -0.25]]


class TestInnerLoopDeterminism:
    """Phase 1 acceptance criterion (ADR-0024 follow-up).

    The inner-loop re-selection introduces a new ordering-sensitive
    path: candidates excluded by rejection feed back into the next
    ``vocab.nearest`` call.  Determinism here relies on:

      * ``vocab.nearest`` using a strict ``>`` tie-break over a
        sequenced iteration (load-bearing comment in
        ``vocab/manifold.py``);
      * ``step_exclude`` being used only for set membership, never
        iterated;
      * ``rejected_attempts`` being appended in loop order.

    These tests pin determinism *by repetition* — same inputs, same
    output across N runs, with non-empty rejection sequences in scope.
    """

    def _run(self) -> GenerationResult:
        vocab = _ControllableVocab(
            words=["seed", "alpha", "beta", "gamma"],
            preference=[1, 2, 3],
            versor_signs=[+1.0, -1.0, -1.0, +1.0],
        )
        return generate(
            _initial_state(vocab),
            vocab,
            _IdentityPersona(),
            max_tokens=1,
            region=_positive_blade_region((1, 2, 3)),
            inner_loop_admissibility=True,
        )

    def test_repeated_runs_produce_identical_rejected_attempts(self) -> None:
        results = [self._run() for _ in range(5)]
        baseline = results[0].admissibility_trace[0].rejected_attempts
        # Two rejections precede the admitted selection.
        assert len(baseline) == 2
        for result in results[1:]:
            step = result.admissibility_trace[0]
            assert step.rejected_attempts == baseline
            assert step.selected_word == "gamma"

    def test_repeated_runs_produce_identical_trace_hash(self) -> None:
        from core.cognition.trace import hash_admissibility_trace

        hashes = {
            hash_admissibility_trace(self._run().admissibility_trace)
            for _ in range(5)
        }
        assert len(hashes) == 1
        only_hash = next(iter(hashes))
        assert only_hash != ""  # non-empty trace ⇒ non-empty hash

    def test_inner_loop_off_preserves_legacy_trace_hash(self) -> None:
        """No rejections ⇒ canonical omits the new key ⇒ hash is byte-
        identical to what an ADR-0023 turn would have produced."""
        from core.cognition.trace import hash_admissibility_trace

        vocab_off = _ControllableVocab(
            words=["seed", "alpha", "beta"],
            preference=[1, 2],
            versor_signs=[+1.0, +1.0, +1.0],
        )
        result_off = generate(
            _initial_state(vocab_off),
            vocab_off,
            _IdentityPersona(),
            max_tokens=1,
            region=_positive_blade_region((1, 2)),
            inner_loop_admissibility=False,
        )
        result_on = generate(
            _initial_state(vocab_off),
            vocab_off,
            _IdentityPersona(),
            max_tokens=1,
            region=_positive_blade_region((1, 2)),
            inner_loop_admissibility=True,
        )
        # No rejections in either run ⇒ traces hash identically.
        h_off = hash_admissibility_trace(result_off.admissibility_trace)
        h_on = hash_admissibility_trace(result_on.admissibility_trace)
        assert h_off == h_on


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
