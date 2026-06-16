"""Perception changed-slot adapter (B4 PR-3).

Critical doctrine: "FALSIFIED" is NOT enough. Only a POSITIVELY observed ``changed``-slot
contradiction may produce ``entailed_false``. Missing observations, unexpected extras, and a
whole-missing actual frame NEVER become false — they refuse.
"""

from __future__ import annotations

import pytest

from generate.frame_verdict import (
    ClosedFrame,
    FrameKind,
    FrameVerdictKind,
    PositiveRefutationKind,
    WorldAssumption,
    frame_verdict_from_perception_falsification,
)
from sensorium.environment.falsification import (
    ChangedSlot,
    FalsificationResidual,
    FalsificationRun,
)

_MISSING = "__missing_observation_frame__"


def _residual(*, matched=(), missing=(), unexpected=(), changed=()) -> FalsificationResidual:
    return FalsificationResidual(
        matched=tuple(matched), missing=tuple(missing),
        unexpected=tuple(unexpected), changed=tuple(changed), residual_sha256="rsha",
    )


def _run(residual: FalsificationResidual, *, actual="actual1", trace="trace_xyz") -> FalsificationRun:
    verdict = "SUPPORTED" if residual.is_supported else "FALSIFIED"
    return FalsificationRun(
        expected_id="exp1", actual_frame_id=actual, verdict=verdict, residual=residual,
        expected_sha256="esha", actual_trace_hash="ath", trace_hash=trace,
    )


def _pframe(kind: FrameKind = FrameKind.PERCEPTION) -> ClosedFrame:
    return ClosedFrame("pf1", kind, WorldAssumption.CLOSED, (), True, "test", ())


_CHANGED = (ChangedSlot("s1", ("k", "v", "exp"), ("k", "v", "act")),)


def test_changed_slot_contradiction_is_entailed_false() -> None:
    run = _run(_residual(changed=_CHANGED))
    v = frame_verdict_from_perception_falsification(_pframe(), run, "conforms?")
    assert v.verdict is FrameVerdictKind.ENTAILED_FALSE
    assert v.proof.producer == "sensorium.falsification" and v.proof.outcome == "FALSIFIED"
    assert v.proof.positive_refutation_kind is PositiveRefutationKind.PERCEPTION_CHANGED_SLOT
    assert v.proof.proof_sha256


def test_changed_slot_with_empty_trace_hash_raises() -> None:
    # entailed_false with an empty proof hash must fail at construction (admissibility).
    run = _run(_residual(changed=_CHANGED), trace="")
    with pytest.raises(ValueError):
        frame_verdict_from_perception_falsification(_pframe(), run, "conforms?")


def test_missing_observation_is_not_false() -> None:
    run = _run(_residual(missing=("s1",)))
    v = frame_verdict_from_perception_falsification(_pframe(), run, "conforms?")
    assert v.verdict is FrameVerdictKind.UNDETERMINED
    assert v.verdict is not FrameVerdictKind.ENTAILED_FALSE


def test_unexpected_extra_is_not_false() -> None:
    run = _run(_residual(unexpected=("s2",)))
    v = frame_verdict_from_perception_falsification(_pframe(), run, "conforms?")
    assert v.verdict is FrameVerdictKind.UNDETERMINED


def test_whole_frame_missing_is_scope_boundary() -> None:
    run = _run(_residual(missing=("s1", "s2")), actual=_MISSING)
    v = frame_verdict_from_perception_falsification(_pframe(), run, "conforms?")
    assert v.verdict is FrameVerdictKind.SCOPE_BOUNDARY
    assert v.verdict is not FrameVerdictKind.ENTAILED_FALSE


def test_supported_run_is_entailed_true() -> None:
    run = _run(_residual(matched=("s1",)))
    v = frame_verdict_from_perception_falsification(_pframe(), run, "conforms?")
    assert v.verdict is FrameVerdictKind.ENTAILED_TRUE
    assert v.proof.outcome == "SUPPORTED" and v.proof.positive_refutation_kind is None


def test_non_perception_frame_is_scope_boundary() -> None:
    run = _run(_residual(changed=_CHANGED))
    v = frame_verdict_from_perception_falsification(_pframe(kind=FrameKind.TEXT), run, "conforms?")
    assert v.verdict is FrameVerdictKind.SCOPE_BOUNDARY


def test_changed_plus_missing_still_entailed_false_on_positive_contradiction() -> None:
    # a changed slot (positive contradiction) dominates even alongside a missing slot.
    run = _run(_residual(changed=_CHANGED, missing=("s9",)))
    v = frame_verdict_from_perception_falsification(_pframe(), run, "conforms?")
    assert v.verdict is FrameVerdictKind.ENTAILED_FALSE
