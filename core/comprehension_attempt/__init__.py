"""Shared typed record of a comprehension organ's attempt at a problem (N2).

The normalization layer the contemplation batch (N3 router, N4 registry, N6 pass manager) reasons
over — uniform across the R1 and R2 setup compilers. Off-serving; imports no `evals`.
"""

from __future__ import annotations

from core.comprehension_attempt.classify import classify_r1, classify_r2
from core.comprehension_attempt.failure_family import (
    REGISTRY,
    FailureFamily,
    enrich_family,
    family_by_name,
    family_for_reason,
)
from core.comprehension_attempt.model import ComprehensionAttempt, Organ, Outcome
from core.comprehension_attempt.router import RouteResult, RouteStatus, route_setup

__all__ = [
    "REGISTRY",
    "ComprehensionAttempt",
    "FailureFamily",
    "Organ",
    "Outcome",
    "RouteResult",
    "RouteStatus",
    "classify_r1",
    "classify_r2",
    "enrich_family",
    "family_by_name",
    "family_for_reason",
    "route_setup",
]
