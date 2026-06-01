"""ADR-0199 — cross-domain learning arena.

The shared engine + interfaces every base subject plugs into. Domains live
outside this package (e.g. ``evals/gsm8k_math/practice``); this package never
imports a concrete domain.
"""

from __future__ import annotations

from core.learning_arena.engine import run_practice
from core.learning_arena.protocols import (
    Attempt,
    BaseAttempt,
    DomainProblem,
    DomainSolver,
    GoldTether,
    Problem,
)
from core.learning_arena.report import (
    REFUSAL_DIAGNOSES,
    EliminationRecord,
    PracticeReport,
    bucket_counts,
)

__all__ = [
    "run_practice",
    "Attempt",
    "BaseAttempt",
    "DomainProblem",
    "DomainSolver",
    "GoldTether",
    "Problem",
    "REFUSAL_DIAGNOSES",
    "EliminationRecord",
    "PracticeReport",
    "bucket_counts",
]
