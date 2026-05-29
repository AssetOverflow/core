"""ADR-0175 Phase 3 — grounded derivation search + self-verification gate.

Phase 3a (this surface): the self-verification gate — grounded operands ∧
grounded operation cues ∧ unit consistency ∧ uniqueness. The wrong=0-critical
guard that keeps the (Phase 3b) bounded search honest.
"""

from __future__ import annotations

from generate.derivation.clauses import (
    ClauseResult,
    clause_local_results,
    segment_clauses,
)
from generate.derivation.comparatives import (
    ComparativeScalar,
    comparative_step,
    extract_comparative_scalars,
)
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step, VALID_OPS
from generate.derivation.multistep import search_chain
from generate.derivation.search import MULTIPLICATIVE_CUES, search_multiplicative
from generate.derivation.target import Target, extract_target
from generate.derivation.verify import (
    Resolution,
    SelfVerification,
    select_self_verified,
    self_verifies,
)

__all__ = [
    "ClauseResult",
    "ComparativeScalar",
    "GroundedDerivation",
    "MULTIPLICATIVE_CUES",
    "Quantity",
    "Resolution",
    "SelfVerification",
    "Step",
    "Target",
    "VALID_OPS",
    "clause_local_results",
    "comparative_step",
    "extract_comparative_scalars",
    "extract_quantities",
    "extract_target",
    "search_chain",
    "search_multiplicative",
    "segment_clauses",
    "select_self_verified",
    "self_verifies",
]
