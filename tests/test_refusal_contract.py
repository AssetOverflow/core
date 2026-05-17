"""ADR-0024 Phase 2 — refusal contract.

Pins the typed-refusal contract introduced in Phase 2:

  1. ``generate.stream`` raises ``InnerLoopExhaustion`` (not bare
     ``ValueError``) at both inner-loop exhaustion sites.
  2. ``InnerLoopExhaustion`` is a ``ValueError`` subclass, so every
     pre-Phase-2 ``except ValueError`` handler still catches it.
  3. Each raise carries evidence: ``reason``, ``region_label``,
     ``step_index``, and (for in-walk site) ``rejected_attempts``.
  4. Pre-walk site uses ``step_index == -1`` and empty
     ``rejected_attempts``; in-walk site uses ``step_index >= 0`` and
     non-empty ``rejected_attempts``.
  5. ``compute_trace_hash`` accepts ``refusal_reason`` and:
       a. byte-identical hash when ``refusal_reason == ""`` (default),
          relative to the same call without the kwarg → preserves
          pre-Phase-2 hashes for non-refused turns;
       b. different hash when ``refusal_reason`` is set to a non-empty
          value, so refusal is load-bearing in replay equality once
          materialised.
  6. ``CognitiveTurnResult`` exposes ``refusal_reason`` defaulting to
     "" so call sites can be ignorant of refusal materialisation
     during the Phase 2 → Phase ? transition window.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.cognition.result import CognitiveTurnResult
from core.cognition.trace import compute_trace_hash
from field.state import FieldState
from generate.admissibility import AdmissibilityRegion, RegionSource
from generate.exhaustion import InnerLoopExhaustion, RefusalReason
from generate.stream import generate


# --------------------------------------------------------------------
# Stub vocab / persona — mirrors test_inner_loop_admissibility.py
# --------------------------------------------------------------------


class _ControllableVocab:
    def __init__(self, *, words, preference, versor_signs):
        self._words = words
        self._preference = preference
        self._versors = []
        for sign in versor_signs:
            v = np.zeros(32, dtype=np.float32)
            v[1] = float(sign)
            self._versors.append(v)

    def __len__(self):
        return len(self._words)

    def nearest(self, F, exclude_idx=-1, exclude_indices=None, candidate_indices=None):
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

    def get_versor_at(self, idx):
        return self._versors[idx]

    def index_of(self, word):
        try:
            return self._words.index(word)
        except ValueError:
            raise KeyError(word)


class _IdentityPersona:
    def apply(self, F):
        return F


def _initial_state():
    F = np.zeros(32, dtype=np.float32)
    F[1] = 1.0
    return FieldState(F=F, node=0, step=0)


def _positive_blade_region(allowed, label="adr0024-phase2-test"):
    blade = np.zeros(32, dtype=np.float32)
    blade[1] = 1.0
    return AdmissibilityRegion(
        allowed_indices=np.asarray(allowed, dtype=np.int64),
        relation_blade=blade,
        source=RegionSource.RELATION,
        label=label,
    )


def _empty_region(label="adr0024-phase2-empty"):
    """Region whose allowed-index intersection with the candidate set
    is empty before any step runs — exercises the pre-walk raise site."""
    blade = np.zeros(32, dtype=np.float32)
    blade[1] = 1.0
    return AdmissibilityRegion(
        allowed_indices=np.asarray([], dtype=np.int64),
        relation_blade=blade,
        source=RegionSource.RELATION,
        label=label,
    )


# --------------------------------------------------------------------
# Property 1 + 2 + 3 + 4: exception type, subclassing, evidence
# --------------------------------------------------------------------


class TestExceptionIsValueErrorSubclass:
    """Pre-Phase-2 handlers caught ValueError; Phase 2 must remain
    backwards-compatible."""

    def test_inner_loop_exhaustion_is_value_error(self) -> None:
        exc = InnerLoopExhaustion(
            reason=RefusalReason.INNER_LOOP_EXHAUSTION,
            region_label="r",
            step_index=-1,
        )
        assert isinstance(exc, ValueError)

    def test_in_walk_exhaustion_caught_as_value_error(self) -> None:
        # Both admissible candidates rejected — exercises the in-walk
        # raise site at the loop's ``else`` branch.
        vocab = _ControllableVocab(
            words=["seed", "alpha", "beta"],
            preference=[1, 2],
            versor_signs=[+1.0, -1.0, -1.0],
        )
        with pytest.raises(ValueError):
            generate(
                _initial_state(),
                vocab,
                _IdentityPersona(),
                max_tokens=1,
                region=_positive_blade_region((1, 2)),
                inner_loop_admissibility=True,
            )

    def test_pre_walk_exhaustion_caught_as_value_error(self) -> None:
        vocab = _ControllableVocab(
            words=["seed", "alpha", "beta"],
            preference=[1, 2],
            versor_signs=[+1.0, +1.0, +1.0],
        )
        with pytest.raises(ValueError):
            generate(
                _initial_state(),
                vocab,
                _IdentityPersona(),
                max_tokens=1,
                region=_empty_region(),
                inner_loop_admissibility=True,
            )


class TestInWalkExhaustionCarriesEvidence:
    def test_typed_exception_with_full_evidence(self) -> None:
        vocab = _ControllableVocab(
            words=["seed", "alpha", "beta"],
            preference=[1, 2],
            versor_signs=[+1.0, -1.0, -1.0],
        )
        with pytest.raises(InnerLoopExhaustion) as excinfo:
            generate(
                _initial_state(),
                vocab,
                _IdentityPersona(),
                max_tokens=1,
                region=_positive_blade_region((1, 2), label="in-walk-label"),
                inner_loop_admissibility=True,
            )
        exc = excinfo.value
        assert exc.reason is RefusalReason.INNER_LOOP_EXHAUSTION
        assert exc.region_label == "in-walk-label"
        # In-walk site fires at step_index >= 0.
        assert exc.step_index >= 0
        # Both admissible candidates rejected ⇒ rejected_attempts
        # records each in attempt order.
        assert len(exc.rejected_attempts) >= 1
        for idx, word, score in exc.rejected_attempts:
            assert isinstance(idx, int)
            assert isinstance(word, str)
            assert isinstance(score, float)
        # Message preserves the Phase 1 contract — region label is
        # embedded so existing ``match=region.label`` callers still pass.
        assert "in-walk-label" in str(exc)


class TestPreWalkExhaustionCarriesEvidence:
    def test_typed_exception_with_pre_walk_sentinel(self) -> None:
        vocab = _ControllableVocab(
            words=["seed", "alpha", "beta"],
            preference=[1, 2],
            versor_signs=[+1.0, +1.0, +1.0],
        )
        with pytest.raises(InnerLoopExhaustion) as excinfo:
            generate(
                _initial_state(),
                vocab,
                _IdentityPersona(),
                max_tokens=1,
                region=_empty_region(label="pre-walk-label"),
                inner_loop_admissibility=True,
            )
        exc = excinfo.value
        assert exc.reason is RefusalReason.INNER_LOOP_EXHAUSTION
        assert exc.region_label == "pre-walk-label"
        # Pre-walk site is marked with the -1 sentinel.
        assert exc.step_index == -1
        # No inner-loop rejections were issued — the intersection was
        # empty before any step ran.
        assert exc.rejected_attempts == ()
        assert "pre-walk-label" in str(exc)


class TestPreWalkSiteFiresEvenWithoutInnerLoop:
    """The pre-walk site predates inner-loop wiring (ADR-0023) — it
    still must raise the typed exception so refusal evidence is
    uniform whether or not the inner loop is on."""

    def test_pre_walk_raise_typed_when_inner_loop_off(self) -> None:
        vocab = _ControllableVocab(
            words=["seed", "alpha", "beta"],
            preference=[1, 2],
            versor_signs=[+1.0, +1.0, +1.0],
        )
        with pytest.raises(InnerLoopExhaustion) as excinfo:
            generate(
                _initial_state(),
                vocab,
                _IdentityPersona(),
                max_tokens=1,
                region=_empty_region(label="pre-walk-no-inner"),
                inner_loop_admissibility=False,
            )
        assert excinfo.value.step_index == -1
        assert excinfo.value.rejected_attempts == ()


# --------------------------------------------------------------------
# Property 5: compute_trace_hash determinism contract
# --------------------------------------------------------------------


_BASE_HASH_KWARGS = dict(
    input_text="hello",
    filtered_tokens=("hello",),
    surface="hi",
    walk_surface="hi",
    articulation_surface="hi",
    dialogue_role="assert",
    versor_condition=0.0,
    vault_hits=0,
    intent_tag="declare",
)


class TestTraceHashRefusalReasonFold:
    def test_default_refusal_reason_preserves_legacy_hash(self) -> None:
        """A non-refused turn (refusal_reason="") must produce the
        same trace_hash as a call that omits the kwarg entirely.  This
        is what protects every pre-Phase-2 turn hash from drift."""
        legacy = compute_trace_hash(**_BASE_HASH_KWARGS)
        with_kwarg = compute_trace_hash(refusal_reason="", **_BASE_HASH_KWARGS)
        assert legacy == with_kwarg

    def test_non_empty_refusal_reason_changes_hash(self) -> None:
        """Once a refusal is materialised, the reason becomes
        load-bearing — different reasons must yield different hashes."""
        base = compute_trace_hash(**_BASE_HASH_KWARGS)
        with_reason = compute_trace_hash(
            refusal_reason=RefusalReason.INNER_LOOP_EXHAUSTION.value,
            **_BASE_HASH_KWARGS,
        )
        assert base != with_reason

    def test_same_refusal_reason_is_stable(self) -> None:
        """Determinism: identical inputs ⇒ identical hash."""
        h1 = compute_trace_hash(
            refusal_reason=RefusalReason.INNER_LOOP_EXHAUSTION.value,
            **_BASE_HASH_KWARGS,
        )
        h2 = compute_trace_hash(
            refusal_reason=RefusalReason.INNER_LOOP_EXHAUSTION.value,
            **_BASE_HASH_KWARGS,
        )
        assert h1 == h2


# --------------------------------------------------------------------
# Property 6: CognitiveTurnResult exposes refusal_reason with safe default
# --------------------------------------------------------------------


class TestCognitiveTurnResultRefusalField:
    def test_refusal_reason_defaults_to_empty(self) -> None:
        # We do not need to construct a full CognitiveTurnResult here;
        # we only need to confirm the dataclass declares the field with
        # the empty-string default.  Use dataclasses.fields() so we
        # don't have to assemble all the other required fields.
        import dataclasses

        names = {f.name: f for f in dataclasses.fields(CognitiveTurnResult)}
        assert "refusal_reason" in names
        assert names["refusal_reason"].default == ""
