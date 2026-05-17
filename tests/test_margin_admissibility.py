"""Phase 3 / ADR-0026 — ranked-with-margin admissibility contract.

These tests pin the new admissibility shape:

  * ``rank_candidates_by_blade`` returns the admissible set sorted
    by ``cga_inner(versor, blade)`` descending, with strict ``>``
    tie-break (ascending vocab index for ties).
  * ``check_margin`` admits the top-ranked candidate iff
    ``top_score > 0`` AND ``top_score - second_score >= delta``.
  * Margin mode wired through ``generate()`` produces the correct
    endpoint on v2 mechanism-isolation cases and emits
    ``InnerLoopExhaustion`` when the margin is not met — never a
    silent boundary fallback.
  * Near-equal-score candidates resolve deterministically across
    repeated runs (replay invariance).
  * Threshold mode (ADR-0024) is unchanged by margin-mode plumbing.
"""

from __future__ import annotations

import numpy as np
import pytest

from chat.runtime import ChatRuntime
from field.state import FieldState
from generate.admissibility import (
    AdmissibilityRegion,
    RankedCandidate,
    RegionSource,
    check_margin,
    rank_candidates_by_blade,
)
from generate.exhaustion import InnerLoopExhaustion, RefusalReason
from generate.stream import generate

_BLADE_DIM = 32


def _zero_blade() -> np.ndarray:
    return np.zeros(_BLADE_DIM, dtype=np.float32)


def _region_with_blade(allowed: list[int], blade: np.ndarray, label: str = "test") -> AdmissibilityRegion:
    return AdmissibilityRegion(
        allowed_indices=np.asarray(allowed, dtype=np.int64),
        relation_blade=blade.astype(np.float32),
        source=RegionSource.RELATION,
        label=label,
    )


# ---------------------------------------------------------------------------
# rank_candidates_by_blade
# ---------------------------------------------------------------------------


class TestRankCandidates:
    def test_ranks_descending_by_score(self) -> None:
        blade = _zero_blade()
        blade[0] = 1.0  # non-zero blade with self-inner != 0 (depends on metric)
        # Build versors with known scores; we'll just construct them and
        # verify the *ordering*, not the exact score values.
        from algebra.cga import cga_inner

        bb = float(cga_inner(blade, blade))
        if abs(bb) < 1e-9:
            pytest.skip("blade self-inner is zero for chosen test blade")
        versors = {
            10: (0.5 / bb) * blade,
            20: (1.0 / bb) * blade,
            30: (0.2 / bb) * blade,
        }
        words = {10: "alpha", 20: "beta", 30: "gamma"}
        region = _region_with_blade([10, 20, 30], blade)
        ranked = rank_candidates_by_blade(
            region,
            candidate_indices=np.asarray([10, 20, 30], dtype=np.int64),
            versor_lookup=lambda i: versors[int(i)],
            word_lookup=lambda i: words[int(i)],
        )
        # Sorted desc by score → indices [20, 10, 30]
        assert [r.index for r in ranked] == [20, 10, 30]
        # Strict descending scores
        assert ranked[0].score > ranked[1].score > ranked[2].score

    def test_strict_tie_break_by_ascending_index(self) -> None:
        """When two candidates have the *same* score, ascending vocab
        index wins.  This pins the determinism contract."""
        blade = _zero_blade()
        blade[0] = 1.0
        from algebra.cga import cga_inner

        bb = float(cga_inner(blade, blade))
        if abs(bb) < 1e-9:
            pytest.skip("blade self-inner is zero for chosen test blade")
        # Two equal scores at indices 30 and 10 → 10 should win.
        versors = {
            10: (1.0 / bb) * blade,
            30: (1.0 / bb) * blade,
            20: (0.5 / bb) * blade,
        }
        words = {10: "alpha", 20: "beta", 30: "gamma"}
        region = _region_with_blade([10, 20, 30], blade)
        ranked = rank_candidates_by_blade(
            region,
            candidate_indices=np.asarray([10, 20, 30], dtype=np.int64),
            versor_lookup=lambda i: versors[int(i)],
            word_lookup=lambda i: words[int(i)],
        )
        # Both tied candidates are at the top; lower index comes first.
        assert ranked[0].index == 10
        assert ranked[1].index == 30
        # Determinism across repeats
        for _ in range(5):
            r = rank_candidates_by_blade(
                region,
                candidate_indices=np.asarray([10, 20, 30], dtype=np.int64),
                versor_lookup=lambda i: versors[int(i)],
                word_lookup=lambda i: words[int(i)],
            )
            assert tuple(c.index for c in r) == tuple(c.index for c in ranked)

    def test_empty_candidate_set_returns_empty(self) -> None:
        blade = _zero_blade()
        blade[0] = 1.0
        region = _region_with_blade([1], blade)
        assert (
            rank_candidates_by_blade(
                region,
                candidate_indices=np.asarray([], dtype=np.int64),
                versor_lookup=lambda i: np.zeros(_BLADE_DIM, dtype=np.float32),
                word_lookup=lambda i: "",
            )
            == ()
        )

    def test_zero_blade_returns_zero_scores_index_order(self) -> None:
        """An unconstrained-direction region returns all candidates at
        score 0, in vocab-index order.  The caller should not enter
        margin mode here; this test pins the safe fallback."""
        region = _region_with_blade([3, 1, 2], _zero_blade())
        # allowed_indices is canonicalised to sorted unique → [1,2,3].
        ranked = rank_candidates_by_blade(
            region,
            candidate_indices=region.allowed_indices,
            versor_lookup=lambda i: np.zeros(_BLADE_DIM, dtype=np.float32),
            word_lookup=lambda i: f"w{i}",
        )
        assert [r.index for r in ranked] == [1, 2, 3]
        assert all(r.score == 0.0 for r in ranked)


# ---------------------------------------------------------------------------
# check_margin
# ---------------------------------------------------------------------------


class TestCheckMargin:
    def _ranked(self, *triples: tuple[int, str, float]) -> tuple[RankedCandidate, ...]:
        return tuple(RankedCandidate(index=i, word=w, score=s) for i, w, s in triples)

    def test_admits_when_margin_meets_delta(self) -> None:
        ranked = self._ranked((1, "a", 1.5), (2, "b", 0.8))
        region = _region_with_blade([1, 2], np.array([1.0] + [0.0] * (_BLADE_DIM - 1), dtype=np.float32))
        verdict = check_margin(region, ranked, delta=0.5)
        assert verdict.admitted is True
        assert verdict.top is not None and verdict.top.index == 1
        assert pytest.approx(verdict.margin, abs=1e-9) == 0.7

    def test_refuses_when_margin_below_delta(self) -> None:
        ranked = self._ranked((1, "a", 1.0), (2, "b", 0.8))
        region = _region_with_blade([1, 2], np.array([1.0] + [0.0] * (_BLADE_DIM - 1), dtype=np.float32))
        verdict = check_margin(region, ranked, delta=0.5)
        assert verdict.admitted is False
        assert "margin" in verdict.reason
        assert pytest.approx(verdict.margin, abs=1e-9) == pytest.approx(0.2)

    def test_refuses_when_top_score_not_positive(self) -> None:
        """Even a clean margin doesn't save a non-positive top score:
        the admissible set has no blade-aligned candidate at all."""
        ranked = self._ranked((1, "a", -0.5), (2, "b", -2.0))
        region = _region_with_blade([1, 2], np.array([1.0] + [0.0] * (_BLADE_DIM - 1), dtype=np.float32))
        verdict = check_margin(region, ranked, delta=0.5)
        assert verdict.admitted is False
        assert "not positive" in verdict.reason

    def test_single_candidate_trivially_admitted_when_positive(self) -> None:
        ranked = self._ranked((1, "a", 0.5))
        region = _region_with_blade([1], np.array([1.0] + [0.0] * (_BLADE_DIM - 1), dtype=np.float32))
        verdict = check_margin(region, ranked, delta=999.0)
        assert verdict.admitted is True
        assert verdict.margin == float("inf")
        assert "single admissible" in verdict.reason

    def test_empty_ranking_refuses(self) -> None:
        region = _region_with_blade([1], np.array([1.0] + [0.0] * (_BLADE_DIM - 1), dtype=np.float32))
        verdict = check_margin(region, (), delta=0.4)
        assert verdict.admitted is False
        assert verdict.top is None


# ---------------------------------------------------------------------------
# generate() in margin mode — integration via v2-like setup
# ---------------------------------------------------------------------------


def _v2_state_and_region(rt: ChatRuntime, *, seed: str, admissible: list[str], blade_tok: str, label: str):
    vocab = rt.session.vocab
    idx = vocab.index_of(seed)
    F = np.asarray(vocab.get_versor(seed), dtype=np.float32)
    state = FieldState(F=F.copy(), node=idx, step=0)
    indices = np.asarray([vocab.index_of(t) for t in admissible], dtype=np.int64)
    blade = np.asarray(vocab.get_versor(blade_tok), dtype=np.float32)
    region = AdmissibilityRegion(
        allowed_indices=indices,
        relation_blade=blade,
        source=RegionSource.RELATION,
        label=label,
    )
    return state, region


class TestGenerateMarginMode:
    """End-to-end: margin mode on v2-style mechanism-isolation cases."""

    def test_v2_001_question_admitted_via_margin(self) -> None:
        rt = ChatRuntime()
        state, region = _v2_state_and_region(
            rt, seed="symbol", admissible=["answer", "question"],
            blade_tok="question", label="v2-001",
        )
        result = generate(
            state, rt.session.vocab, rt.session.persona,
            max_tokens=1, region=region,
            inner_loop_admissibility=True,
            admissibility_mode="margin",
            admissibility_margin=0.4,
        )
        assert result.tokens == ("question",)
        step = result.admissibility_trace[0]
        assert step.verdict.admitted is True
        assert "margin" in step.verdict.reason
        # rejected_attempts now carries the *full* ranking
        assert len(step.rejected_attempts) >= 2
        words = [w for (_i, w, _s) in step.rejected_attempts]
        assert "question" in words and "answer" in words

    def test_v2_001_refuses_when_delta_too_high(self) -> None:
        """The v2-001 margin is ≈0.597.  Setting delta=0.9 must trigger
        honest refusal — no silent boundary fallback."""
        rt = ChatRuntime()
        state, region = _v2_state_and_region(
            rt, seed="symbol", admissible=["answer", "question"],
            blade_tok="question", label="v2-001",
        )
        with pytest.raises(InnerLoopExhaustion) as exc_info:
            generate(
                state, rt.session.vocab, rt.session.persona,
                max_tokens=1, region=region,
                inner_loop_admissibility=True,
                admissibility_mode="margin",
                admissibility_margin=0.9,
            )
        exc = exc_info.value
        assert exc.reason is RefusalReason.INNER_LOOP_EXHAUSTION
        assert exc.region_label == "v2-001"
        # Refusal carries the ranking as evidence
        words = [w for (_i, w, _s) in exc.rejected_attempts]
        assert "question" in words and "answer" in words

    def test_threshold_mode_unchanged_by_margin_plumbing(self) -> None:
        """Threshold mode (the ADR-0024 default) must produce the same
        result whether admissibility_mode is "threshold" or unset."""
        rt = ChatRuntime()
        state, region = _v2_state_and_region(
            rt, seed="symbol", admissible=["answer", "question"],
            blade_tok="question", label="v2-001",
        )
        r1 = generate(
            state, rt.session.vocab, rt.session.persona,
            max_tokens=1, region=region,
            inner_loop_admissibility=True,
            admissibility_threshold=1.122,
        )
        r2 = generate(
            state, rt.session.vocab, rt.session.persona,
            max_tokens=1, region=region,
            inner_loop_admissibility=True,
            admissibility_threshold=1.122,
            admissibility_mode="threshold",
        )
        assert r1.tokens == r2.tokens
        assert r1.tokens == ("question",)


class TestMarginModeDeterminism:
    """5 reruns of the same margin-mode case produce identical traces."""

    def test_margin_mode_replay_stable_across_5_runs(self) -> None:
        rt = ChatRuntime()
        state, region = _v2_state_and_region(
            rt, seed="symbol", admissible=["answer", "question"],
            blade_tok="question", label="v2-001",
        )
        first = generate(
            state, rt.session.vocab, rt.session.persona,
            max_tokens=1, region=region,
            inner_loop_admissibility=True,
            admissibility_mode="margin",
            admissibility_margin=0.4,
        )
        first_canonical = first.admissibility_trace[0].canonical()
        for _ in range(4):
            r = generate(
                state, rt.session.vocab, rt.session.persona,
                max_tokens=1, region=region,
                inner_loop_admissibility=True,
                admissibility_mode="margin",
                admissibility_margin=0.4,
            )
            assert r.tokens == first.tokens
            assert r.admissibility_trace[0].canonical() == first_canonical
