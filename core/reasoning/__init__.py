"""Shared deterministic reasoning evidence contracts."""

from __future__ import annotations

from core.reasoning.evidence import (
    COMMITMENT_DISAGREEMENT,
    DUPLICATE_STRUCTURAL_SIGNATURE,
    INSUFFICIENT_EVIDENCE,
    MISSING_COMMITMENT,
    TIER2_VERIFIED,
    EvidenceBundle,
    OperatorEvidence,
    Tier2Verdict,
    verify_tier2_agreement,
)
from core.reasoning.adapters import (
    evidence_from_entailment_trace,
    evidence_from_math_solution,
)

__all__ = [
    "COMMITMENT_DISAGREEMENT",
    "DUPLICATE_STRUCTURAL_SIGNATURE",
    "INSUFFICIENT_EVIDENCE",
    "MISSING_COMMITMENT",
    "TIER2_VERIFIED",
    "EvidenceBundle",
    "OperatorEvidence",
    "Tier2Verdict",
    "verify_tier2_agreement",
    "evidence_from_entailment_trace",
    "evidence_from_math_solution",
]
