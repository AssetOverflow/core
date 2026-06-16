"""Perception -> FrameVerdict adapter (ADR-0222 §5.2, B4 PR-3).

Lifts an ADR-0211 ``FalsificationRun`` into a ``FrameVerdict``, SAFELY. The critical
doctrine: "FALSIFIED" is NOT enough. Only a POSITIVELY observed ``changed``-slot
contradiction (a declared-expected slot observed with a contradicting content identity) may
produce ``entailed_false``. Missing observations (absence), unexpected extras
(over-observation), and a whole-missing actual frame NEVER become false — they refuse
(``undetermined`` / ``scope_boundary``). Off-serving; construction is delegated to the single
allowlisted ``_construct.build_frame_verdict``.

The perception ``query`` is the frame-CONFORMANCE proposition ("the observation conforms to
the expected frame"), not an arbitrary asked proposition (ADR §5.2).
"""

from __future__ import annotations

from generate.frame_verdict._construct import build_frame_verdict
from generate.frame_verdict.types import (
    ClosedFrame,
    ClosedWorldProof,
    FrameKind,
    FrameVerdict,
    FrameVerdictKind,
    PositiveRefutationKind,
    WorldAssumption,
)
from sensorium.environment.falsification import FalsificationRun

_PRODUCER = "sensorium.falsification"
_MISSING_FRAME = "__missing_observation_frame__"


def frame_verdict_from_perception_falsification(
    frame: ClosedFrame, run: FalsificationRun, query: str
) -> FrameVerdict:
    """Map an ADR-0211 falsification run to a perception ``FrameVerdict``."""
    if frame.frame_kind is not FrameKind.PERCEPTION:
        return _verdict(frame, query, FrameVerdictKind.SCOPE_BOUNDARY, run, kind=None)

    # Frame gating — the SAME negation law the text evaluator enforces (evaluate.py): a negation
    # may be asserted ONLY for a declared-complete, non-OPEN frame. An OPEN / undeclared-closure
    # perception frame refuses (scope_boundary); it can NEVER reach entailed_false. Without this
    # the changed-slot branch below would emit an OPEN-world negation — a frame-invariant breach
    # (types.py §(0) is the structural backstop; this is the graceful upstream refusal).
    if frame.world_assumption is WorldAssumption.OPEN or not frame.closure_declared:
        return _verdict(frame, query, FrameVerdictKind.SCOPE_BOUNDARY, run, kind=None)

    # Whole actual frame missing — observed NOTHING (a coverage gap), never a refutation.
    if run.actual_frame_id == _MISSING_FRAME:
        return _verdict(frame, query, FrameVerdictKind.SCOPE_BOUNDARY, run, kind=None)

    residual = run.residual
    if residual.changed:
        # POSITIVE contradiction: a declared-expected slot observed with a contradicting
        # identity. The ONLY perception path to entailed_false.
        return _verdict(
            frame, query, FrameVerdictKind.ENTAILED_FALSE, run,
            kind=PositiveRefutationKind.PERCEPTION_CHANGED_SLOT,
        )

    if residual.is_supported:
        # the observation conforms to the expected frame — the conformance query is proven.
        return _verdict(frame, query, FrameVerdictKind.ENTAILED_TRUE, run, kind=None)

    # missing-only or unexpected-only: absence / over-observation — NEVER false.
    return _verdict(frame, query, FrameVerdictKind.UNDETERMINED, run, kind=None)


def _verdict(
    frame: ClosedFrame,
    query: str,
    verdict: FrameVerdictKind,
    run: FalsificationRun,
    *,
    kind: PositiveRefutationKind | None,
) -> FrameVerdict:
    # proof carries the FULL run trace_hash (binds expected_sha256 + actual_trace_hash +
    # verdict — ADR §5.4), not the residual hash alone. Non-empty by construction.
    proof = ClosedWorldProof(
        producer=_PRODUCER,
        outcome=run.verdict,            # "SUPPORTED" | "FALSIFIED"
        proof_sha256=run.trace_hash,
        proof_keys=(run.trace_hash,),
        positive_refutation_kind=kind,  # only PERCEPTION_CHANGED_SLOT for entailed_false
        trace_hash=run.trace_hash,
    )
    return build_frame_verdict(frame, query, verdict, proof)
