"""Phase 4 / ADR-0025 — rotor admissibility contract.

Pins the rotor-side admissibility shape:

  * ``check_rotor_admissibility`` is a no-op admit when the region
    carries no ``frame_versor`` (back-compat — every pre-Phase-4
    region admits trivially).
  * With a non-null ``frame_versor``, the rotor is admitted iff
    ``cga_inner(versor_apply(V, F), frame_versor) > 0``.
  * Wired through ``generate()``: in margin mode the rotor check
    runs on the top-ranked candidate after destination margin
    admits; rotor refusal raises ``InnerLoopExhaustion`` with
    ``reason=ROTOR_REJECTION`` (not ``INNER_LOOP_EXHAUSTION``) so
    the trace names the axis that ran out.
  * In threshold mode, rotor rejection retries the next candidate
    inside the per-attempt loop (same shape as destination rejection),
    and only escalates to refusal when the loop exhausts.  The
    exhaustion ``reason`` is ``ROTOR_REJECTION`` iff *any* rotor
    rejection occurred during the step.
  * The ``versor_condition < 1e-6`` invariant is preserved on
    admitted rotors — algebra closure asserts at apply time, not
    in this module.
"""

from __future__ import annotations

import numpy as np
import pytest

from algebra.backend import versor_apply, versor_condition
from algebra.cga import cga_inner
from algebra.rotor import word_transition_rotor
from chat.runtime import ChatRuntime
from field.state import FieldState
from generate.admissibility import AdmissibilityRegion, RegionSource
from generate.exhaustion import InnerLoopExhaustion, RefusalReason
from generate.rotor_admissibility import (
    RotorVerdict,
    check_rotor_admissibility,
)
from generate.stream import generate


_BLADE_DIM = 32


def _zero_blade() -> np.ndarray:
    return np.zeros(_BLADE_DIM, dtype=np.float32)


def _region(
    *,
    allowed: list[int],
    blade: np.ndarray,
    frame: np.ndarray | None = None,
    label: str = "rotor-test",
) -> AdmissibilityRegion:
    return AdmissibilityRegion(
        allowed_indices=np.asarray(allowed, dtype=np.int64),
        relation_blade=blade.astype(np.float32),
        frame_versor=frame,
        source=RegionSource.RELATION,
        label=label,
    )


def _v2_setup(rt: ChatRuntime, *, seed: str, admissible: list[str], blade_tok: str):
    """Construct the (state, indices, blade) tuple used by v2-style cases."""
    vocab = rt.session.vocab
    idx = vocab.index_of(seed)
    F = np.asarray(vocab.get_versor(seed), dtype=np.float32)
    state = FieldState(F=F.copy(), node=idx, step=0)
    indices = np.asarray([vocab.index_of(t) for t in admissible], dtype=np.int64)
    blade = np.asarray(vocab.get_versor(blade_tok), dtype=np.float32)
    return state, indices, blade


# ---------------------------------------------------------------------------
# check_rotor_admissibility — pure unit tests
# ---------------------------------------------------------------------------


class TestRotorVerdictNoFrameConstraint:
    """A region with ``frame_versor is None`` always admits."""

    def test_admits_when_frame_versor_is_none(self) -> None:
        blade = _zero_blade()
        blade[0] = 1.0
        region = _region(allowed=[0], blade=blade, frame=None)
        F = np.zeros(_BLADE_DIM, dtype=np.float32)
        F[1] = 1.0
        V = np.zeros(_BLADE_DIM, dtype=np.float32)
        V[2] = 1.0
        verdict = check_rotor_admissibility(region, field_current=F, rotor=V)
        assert verdict.admitted is True
        assert verdict.score == float("inf")
        assert "no frame constraint" in verdict.reason

    def test_admits_when_frame_versor_is_null_norm(self) -> None:
        """An all-zeros frame_versor is treated as no constraint
        (norm < _NULL_TOLERANCE), not as a hostile bound."""
        blade = _zero_blade()
        blade[0] = 1.0
        region = _region(allowed=[0], blade=blade, frame=_zero_blade())
        F = np.zeros(_BLADE_DIM, dtype=np.float32)
        F[1] = 1.0
        V = np.zeros(_BLADE_DIM, dtype=np.float32)
        V[2] = 1.0
        verdict = check_rotor_admissibility(region, field_current=F, rotor=V)
        assert verdict.admitted is True
        assert verdict.score == float("inf")


class TestRotorVerdictWithFrame:
    """With a real frame versor, admission is gated by score > 0."""

    def test_admits_when_score_positive(self) -> None:
        rt = ChatRuntime()
        state, _idx, blade = _v2_setup(
            rt, seed="symbol", admissible=["question", "answer"], blade_tok="question"
        )
        # frame_versor = seed direction → the seed-to-seed rotor is
        # identity-ish and the post-rotor field stays aligned with the
        # frame.  We use the seed-to-question rotor and check the
        # frame=seed case.
        frame = state.F.copy()  # frame is seed direction
        V = word_transition_rotor(
            state.F, np.asarray(rt.session.vocab.get_versor("question"), dtype=np.float32)
        )
        region = _region(allowed=[0], blade=blade, frame=frame)
        verdict = check_rotor_admissibility(region, field_current=state.F, rotor=V)
        # Whether this is admitted depends on actual algebra — we
        # assert the shape, not a specific score.
        assert isinstance(verdict, RotorVerdict)
        assert verdict.region_label.startswith("rotor-test")

    def test_refuses_when_score_non_positive(self) -> None:
        """Construct a frame deliberately misaligned with the post-
        rotor field.  An orthogonal-ish frame versor (zeros except one
        coordinate) will not be score-positive against the propagated
        field unless by coincidence."""
        rt = ChatRuntime()
        state, _idx, blade = _v2_setup(
            rt, seed="symbol", admissible=["question", "answer"], blade_tok="question"
        )
        frame = np.zeros(_BLADE_DIM, dtype=np.float32)
        frame[15] = 1.0  # coordinate chosen to mismatch field alignment
        V = word_transition_rotor(
            state.F, np.asarray(rt.session.vocab.get_versor("question"), dtype=np.float32)
        )
        region = _region(allowed=[0], blade=blade, frame=frame)
        verdict = check_rotor_admissibility(region, field_current=state.F, rotor=V)
        # We can't guarantee non-positivity for arbitrary frame
        # choices without running the algebra ourselves first.
        # Verify by recomputing: if score is non-positive, refuse;
        # if positive, admit.  Either way the verdict shape is sound.
        F_next = versor_apply(V, state.F)
        expected_score = float(cga_inner(np.asarray(F_next, dtype=np.float32), frame))
        if expected_score <= 0.0:
            assert verdict.admitted is False
            assert "not positive" in verdict.reason
            assert pytest.approx(verdict.score, abs=1e-5) == expected_score
        else:
            assert verdict.admitted is True


# ---------------------------------------------------------------------------
# generate() wiring — integration via v2-like setup
# ---------------------------------------------------------------------------


class TestGenerateRotorAdmissibility:
    """End-to-end: rotor admissibility wired through generate()."""

    def test_no_frame_versor_preserves_phase3_behavior(self) -> None:
        """When the region carries no frame_versor, margin mode
        produces the same token as before Phase 4 (Phase 3 invariant
        preserved).  No rotor refusal possible."""
        rt = ChatRuntime()
        state, indices, blade = _v2_setup(
            rt, seed="symbol", admissible=["answer", "question"], blade_tok="question"
        )
        region = AdmissibilityRegion(
            allowed_indices=indices, relation_blade=blade,
            frame_versor=None, source=RegionSource.RELATION, label="v2-001-no-frame",
        )
        r = generate(
            state, rt.session.vocab, rt.session.persona,
            max_tokens=1, region=region,
            inner_loop_admissibility=True,
            admissibility_mode="margin",
            admissibility_margin=0.4,
        )
        assert r.tokens == ("question",)

    def test_frame_aligned_with_seed_admits(self) -> None:
        """frame_versor = seed direction — the seed→question rotor
        keeps the field aligned with frame; admit."""
        rt = ChatRuntime()
        state, indices, blade = _v2_setup(
            rt, seed="symbol", admissible=["answer", "question"], blade_tok="question"
        )
        region = AdmissibilityRegion(
            allowed_indices=indices, relation_blade=blade,
            frame_versor=state.F.copy(),
            source=RegionSource.RELATION, label="v2-001-frame-seed",
        )
        r = generate(
            state, rt.session.vocab, rt.session.persona,
            max_tokens=1, region=region,
            inner_loop_admissibility=True,
            admissibility_mode="margin",
            admissibility_margin=0.4,
        )
        assert r.tokens == ("question",)

    def test_frame_orthogonal_refuses_with_rotor_rejection(self) -> None:
        """A frame versor misaligned with the propagated field must
        produce honest refusal under ``ROTOR_REJECTION``, not
        ``INNER_LOOP_EXHAUSTION`` — the trace names the axis."""
        rt = ChatRuntime()
        state, indices, blade = _v2_setup(
            rt, seed="symbol", admissible=["answer", "question"], blade_tok="question"
        )
        frame = np.zeros(_BLADE_DIM, dtype=np.float32)
        frame[15] = 1.0  # chosen to mismatch the algebra of this pack
        region = AdmissibilityRegion(
            allowed_indices=indices, relation_blade=blade, frame_versor=frame,
            source=RegionSource.RELATION, label="v2-001-frame-ortho",
        )
        with pytest.raises(InnerLoopExhaustion) as exc_info:
            generate(
                state, rt.session.vocab, rt.session.persona,
                max_tokens=1, region=region,
                inner_loop_admissibility=True,
                admissibility_mode="margin",
                admissibility_margin=0.4,
            )
        exc = exc_info.value
        assert exc.reason is RefusalReason.ROTOR_REJECTION
        assert exc.region_label == "v2-001-frame-ortho"
        # Evidence: the ranking AND the rejected rotor are present
        assert len(exc.rejected_attempts) >= 1
        words = [w for (_i, w, _s) in exc.rejected_attempts]
        # The destination 'question' was chosen by margin then
        # rotor-rejected; it must appear in the trace.
        assert "question" in words

    def test_versor_condition_preserved_on_admitted_rotor(self) -> None:
        """Sanity: when rotor admits, the actual propagation closes
        within ``versor_condition < 1e-6``.  This is algebra closure,
        not rotor-admissibility business — the test pins that they
        co-exist cleanly."""
        rt = ChatRuntime()
        state, indices, blade = _v2_setup(
            rt, seed="symbol", admissible=["answer", "question"], blade_tok="question"
        )
        region = AdmissibilityRegion(
            allowed_indices=indices, relation_blade=blade,
            frame_versor=state.F.copy(),
            source=RegionSource.RELATION, label="v2-001-frame-seed",
        )
        r = generate(
            state, rt.session.vocab, rt.session.persona,
            max_tokens=1, region=region,
            inner_loop_admissibility=True,
            admissibility_mode="margin",
            admissibility_margin=0.4,
        )
        # final_state's F satisfies versor_condition
        cond = float(versor_condition(np.asarray(r.final_state.F, dtype=np.float64)))
        assert cond < 1e-6, f"versor_condition violated: {cond}"

    def test_threshold_mode_rotor_rejection_routes_reason(self) -> None:
        """Threshold mode: when every candidate's rotor is rejected,
        the InnerLoopExhaustion reason is ROTOR_REJECTION, not
        INNER_LOOP_EXHAUSTION — the axis is named."""
        rt = ChatRuntime()
        state, indices, blade = _v2_setup(
            rt, seed="symbol", admissible=["answer", "question"], blade_tok="question"
        )
        frame = np.zeros(_BLADE_DIM, dtype=np.float32)
        frame[15] = 1.0
        region = AdmissibilityRegion(
            allowed_indices=indices, relation_blade=blade, frame_versor=frame,
            source=RegionSource.RELATION, label="v2-001-thr-frame-ortho",
        )
        with pytest.raises(InnerLoopExhaustion) as exc_info:
            generate(
                state, rt.session.vocab, rt.session.persona,
                max_tokens=1, region=region,
                inner_loop_admissibility=True,
                admissibility_threshold=0.0,  # destination passes easily
            )
        assert exc_info.value.reason is RefusalReason.ROTOR_REJECTION


class TestRotorAdmissibilityDeterminism:
    """5 reruns of the same rotor-admissibility scenario produce
    identical traces (replay invariance)."""

    def test_admitted_rotor_replay_stable(self) -> None:
        rt = ChatRuntime()
        state, indices, blade = _v2_setup(
            rt, seed="symbol", admissible=["answer", "question"], blade_tok="question"
        )
        region = AdmissibilityRegion(
            allowed_indices=indices, relation_blade=blade,
            frame_versor=state.F.copy(),
            source=RegionSource.RELATION, label="v2-001-frame-seed",
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

    def test_rotor_refusal_replay_stable(self) -> None:
        rt = ChatRuntime()
        state, indices, blade = _v2_setup(
            rt, seed="symbol", admissible=["answer", "question"], blade_tok="question"
        )
        frame = np.zeros(_BLADE_DIM, dtype=np.float32)
        frame[15] = 1.0
        region = AdmissibilityRegion(
            allowed_indices=indices, relation_blade=blade, frame_versor=frame,
            source=RegionSource.RELATION, label="v2-001-frame-ortho",
        )
        first_attempts: tuple[tuple[int, str, float], ...] | None = None
        for _ in range(5):
            with pytest.raises(InnerLoopExhaustion) as exc_info:
                generate(
                    state, rt.session.vocab, rt.session.persona,
                    max_tokens=1, region=region,
                    inner_loop_admissibility=True,
                    admissibility_mode="margin",
                    admissibility_margin=0.4,
                )
            if first_attempts is None:
                first_attempts = exc_info.value.rejected_attempts
            else:
                assert exc_info.value.rejected_attempts == first_attempts
                assert exc_info.value.reason is RefusalReason.ROTOR_REJECTION
