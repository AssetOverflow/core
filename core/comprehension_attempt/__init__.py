"""Shared typed record of a comprehension organ's attempt at a problem (N2).

The normalization layer the contemplation batch (N3 router, N4 registry, N6 pass manager) reasons
over — uniform across the R1 and R2 setup compilers. Off-serving; imports no `evals`.
"""

from __future__ import annotations

from core.comprehension_attempt.classify import classify_r1, classify_r2
from core.comprehension_attempt.model import ComprehensionAttempt, Organ, Outcome

__all__ = ["ComprehensionAttempt", "Organ", "Outcome", "classify_r1", "classify_r2"]
