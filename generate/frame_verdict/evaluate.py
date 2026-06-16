"""The isolated, off-serving text-frame evaluator (ADR-0222 §4/§5.1, B4 PR-1).

``evaluate_frame_verdict`` takes a ``ClosedFrame`` (never a ``SessionContext``) and returns
a ``FrameVerdict`` (never a ``Determined``). It composes the EXISTING sound producer
``proof_chain.entail`` — it is NOT a second prover. A closed-world False is produced ONLY
from an ROBDD refutation (`(⋀prem) → ¬query` tautology); absence is never false.

PR-1 contract: TEXT frame only; ``frame.propositions`` + ``query`` are propositional-formula
strings in the proof_chain grammar (no prose lowering). Non-TEXT frame_kind, an OPEN world
assumption, or an undeclared closure all return ``SCOPE_BOUNDARY``. Firewalled out of the
open-world runtime by INV-31. Construction is delegated to ``_construct.build_frame_verdict``
(the single allowlisted site).
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
from generate.proof_chain.entail import (
    INCONSISTENT_PREMISES,
    Entailment,
    evaluate_entailment_with_trace,
)
from sensorium.audio.checksum import sha256_json

_PRODUCER = "proof_chain.entail"
_GUARD_PRODUCER = "frame_verdict.guard"


def evaluate_frame_verdict(frame: ClosedFrame, query: str) -> FrameVerdict:
    """Evaluate a CLOSED TEXT frame against ``query`` -> ``FrameVerdict``. Isolated /
    off-serving; the only text constructor of a ``FrameVerdict``."""
    # Frame gating — a negation may be asserted ONLY for a declared-complete TEXT frame.
    if (
        frame.frame_kind is not FrameKind.TEXT
        or frame.world_assumption is WorldAssumption.OPEN
        or not frame.closure_declared
    ):
        return _guard_scope_boundary(frame, query, reason="open_or_undeclared_or_non_text")

    trace = evaluate_entailment_with_trace(frame.propositions, query)
    # Order-invariant proof digest: built from the ROBDD CANONICAL keys (conjunction_key is
    # order-invariant by ROBDD canonicalization), NOT the order-sensitive premise_keys — so
    # premise reordering keeps proof_sha256 and trace_hash stable.
    psha = sha256_json(_proof_payload(trace))

    if trace.outcome is Entailment.ENTAILED:
        proof = ClosedWorldProof(
            producer=_PRODUCER, outcome="ENTAILED", proof_sha256=psha,
            proof_keys=_keys(trace.conjunction_key, trace.query_key, trace.entailment_check_key),
            positive_refutation_kind=None, trace_hash=psha,
        )
        return build_frame_verdict(frame, query, FrameVerdictKind.ENTAILED_TRUE, proof)

    if trace.outcome is Entailment.REFUTED:
        proof = ClosedWorldProof(
            producer=_PRODUCER, outcome="REFUTED", proof_sha256=psha,
            proof_keys=_keys(trace.conjunction_key, trace.query_key, trace.refutation_check_key),
            positive_refutation_kind=PositiveRefutationKind.ROBDD_REFUTATION, trace_hash=psha,
        )
        return build_frame_verdict(frame, query, FrameVerdictKind.ENTAILED_FALSE, proof)

    if trace.outcome is Entailment.UNKNOWN:
        proof = ClosedWorldProof(
            producer=_PRODUCER, outcome="UNKNOWN", proof_sha256=psha,
            proof_keys=_keys(trace.conjunction_key, trace.query_key),
            positive_refutation_kind=None, trace_hash=psha,
        )
        return build_frame_verdict(frame, query, FrameVerdictKind.UNDETERMINED, proof)

    # REFUSED: inconsistent premises => contradiction; out-of-regime / malformed => scope_boundary.
    kind = (
        FrameVerdictKind.CONTRADICTION
        if trace.reason == INCONSISTENT_PREMISES
        else FrameVerdictKind.SCOPE_BOUNDARY
    )
    proof = ClosedWorldProof(
        producer=_PRODUCER, outcome="REFUSED", proof_sha256=psha,
        proof_keys=_keys(trace.conjunction_key), positive_refutation_kind=None, trace_hash=psha,
    )
    return build_frame_verdict(frame, query, kind, proof)


def _proof_payload(trace) -> dict[str, object]:
    """The ORDER-INVARIANT slice of the entailment trace (the ROBDD canonical keys), used for
    the replay-stable proof digest. Excludes ``premise_keys`` (input-order-sensitive)."""
    return {
        "outcome": trace.outcome.value,
        "reason": trace.reason,
        "conjunction_key": trace.conjunction_key,
        "query_key": trace.query_key,
        "entailment_check_key": trace.entailment_check_key,
        "refutation_check_key": trace.refutation_check_key,
    }


def _keys(*ks: str | None) -> tuple[str, ...]:
    return tuple(k for k in ks if k)


def _guard_scope_boundary(frame: ClosedFrame, query: str, *, reason: str) -> FrameVerdict:
    psha = sha256_json({"frame_id": frame.frame_id, "guard": reason})
    proof = ClosedWorldProof(
        producer=_GUARD_PRODUCER, outcome="REFUSED", proof_sha256=psha, proof_keys=(),
        positive_refutation_kind=None, trace_hash="",
    )
    return build_frame_verdict(frame, query, FrameVerdictKind.SCOPE_BOUNDARY, proof)
