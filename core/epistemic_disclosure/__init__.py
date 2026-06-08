"""The Epistemic Disclosure spine (P0-1+).

CORE's served-surface governance: comprehension produces evidence, the limitation
pass classifies *what kind of gap* is blocking resolution, and (in later slices) a
disposition + disclosure-claim decide what reaches the user and under what epistemic
claim. This package is the *owner* of that machine — ``generate/derivation/verify.py``
and other serving sites may eventually *consume* it, but must never *define* it.

P0-1 ships only :mod:`core.epistemic_disclosure.limitation` — the typed limitation
vocabulary and its mapping as a CONSOLIDATING VIEW over the shipped failure-family
registry + contemplation terminals (no fourth taxonomy). Off-serving: nothing here
imports ``generate.derivation`` / ``core.reliability_gate``.
"""

from __future__ import annotations

from core.epistemic_disclosure.limitation import (
    PENDING_Q1B_RECLASSIFICATION,
    LimitationAssessment,
    LimitationKind,
    ResolutionAction,
    assess_from_attempt,
    assess_from_family,
    terminal_for_action,
)

__all__ = [
    "PENDING_Q1B_RECLASSIFICATION",
    "LimitationAssessment",
    "LimitationKind",
    "ResolutionAction",
    "assess_from_attempt",
    "assess_from_family",
    "terminal_for_action",
]
