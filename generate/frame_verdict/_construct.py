"""The single FrameVerdict construction site (INV-31 allowlist target).

Both the text evaluator and the perception adapter build their verdicts here, so the
``FrameVerdict(...)`` construction lives in exactly ONE file — the only entry in
``ALLOWED_FRAME_VERDICT_SITES``. The replay digest (``trace_hash``) is computed over a
canonical, order-stable payload here so every producer is replay-deterministic by construction.
"""

from __future__ import annotations

from generate.epistemic_basis import epistemic_basis
from generate.frame_verdict.types import (
    ClosedFrame,
    ClosedWorldProof,
    FrameVerdict,
    FrameVerdictKind,
)
from sensorium.audio.checksum import sha256_json


def build_frame_verdict(
    frame: ClosedFrame,
    query: str,
    kind: FrameVerdictKind,
    proof: ClosedWorldProof,
    *,
    basis: str | None = None,
    provenance: tuple[str, ...] | None = None,
) -> FrameVerdict:
    """Construct a ``FrameVerdict`` with a deterministic replay digest. ``basis`` defaults to
    ``epistemic_basis(())`` ("as_told" — no COHERENT grounds today); ``provenance`` defaults to
    the proof's content-addressed keys."""
    if basis is None:
        basis = epistemic_basis(())
    if provenance is None:
        provenance = proof.proof_keys
    payload = {
        "frame_id": frame.frame_id,
        "frame_kind": frame.frame_kind.value,
        "world_assumption": frame.world_assumption.value,
        "query": query,
        "verdict": kind.value,
        "basis": basis,
        "proof": {
            "producer": proof.producer,
            "outcome": proof.outcome,
            "proof_sha256": proof.proof_sha256,
            "proof_keys": list(proof.proof_keys),
            "positive_refutation_kind": (
                proof.positive_refutation_kind.value if proof.positive_refutation_kind else None
            ),
            "trace_hash": proof.trace_hash,
        },
        "provenance": list(provenance),
    }
    trace_hash = sha256_json(payload)
    return FrameVerdict(
        frame_id=frame.frame_id,
        frame_kind=frame.frame_kind,
        world_assumption=frame.world_assumption,
        query=query,
        verdict=kind,
        proof=proof,
        basis=basis,
        trace_hash=trace_hash,
        provenance=provenance,
    )
