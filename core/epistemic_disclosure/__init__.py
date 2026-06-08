"""The Epistemic Disclosure spine (P0-1+).

CORE's served-surface governance: comprehension produces evidence, the limitation
pass classifies *what kind of gap* is blocking resolution, and (in later slices) a
disposition + disclosure-claim decide what reaches the user and under what epistemic
claim. This package is the *owner* of that machine — ``generate/derivation/verify.py``
and other serving sites may eventually *consume* it, but must never *define* it.

Shipped so far (all off-serving — nothing here imports ``generate.derivation`` /
``core.reliability_gate``):

  * :mod:`~core.epistemic_disclosure.limitation` (P0-1) — the typed limitation
    vocabulary, a CONSOLIDATING VIEW over the shipped failure-family registry +
    contemplation terminals (no fourth taxonomy).
  * :mod:`~core.epistemic_disclosure.disclosure_claim` (P0-2) — the ``DisclosureClaim``
    axis (the epistemic claim a response makes), kept SEPARATE from ``ReachLevel``.
  * :mod:`~core.epistemic_disclosure.disposition` (P0-3) — ``ServedDisposition`` and
    ``choose_served_disposition``: the pure mapping
    ``EpistemicState × LimitationAssessment × DisclosureClaim → ServedDisposition``.
    Mapping scaffold only — no rendering, no bus, no ``verify.py``; nothing consumes
    it yet.
"""

from __future__ import annotations

from core.epistemic_disclosure.disclosure_claim import (
    DEFAULT_DISCLOSURE_CLAIM,
    DisclosureClaim,
)
from core.epistemic_disclosure.disposition import (
    ServedDisposition,
    choose_served_disposition,
)
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
    "DEFAULT_DISCLOSURE_CLAIM",
    "PENDING_Q1B_RECLASSIFICATION",
    "DisclosureClaim",
    "LimitationAssessment",
    "LimitationKind",
    "ResolutionAction",
    "ServedDisposition",
    "assess_from_attempt",
    "assess_from_family",
    "choose_served_disposition",
    "terminal_for_action",
]
