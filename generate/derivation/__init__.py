"""ADR-0175 Phase 3 — grounded derivation search + self-verification gate.

Phase 3a (this surface): the self-verification gate — grounded operands ∧
grounded operation cues ∧ unit consistency ∧ uniqueness. The wrong=0-critical
guard that keeps the (Phase 3b) bounded search honest.
"""

from __future__ import annotations

from generate.derivation.model import GroundedDerivation, Quantity, Step, VALID_OPS
from generate.derivation.verify import (
    Resolution,
    SelfVerification,
    select_self_verified,
    self_verifies,
)

__all__ = [
    "GroundedDerivation",
    "Quantity",
    "Resolution",
    "SelfVerification",
    "Step",
    "VALID_OPS",
    "select_self_verified",
    "self_verifies",
]
