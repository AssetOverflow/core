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
  * :mod:`~core.epistemic_disclosure.ask_serving` — a narrow Q1-D served-ASK artifact
    adapter. It validates already-rendered question artifacts and returns a typed
    decision; it does not render prose and does not acquire runtime contemplation.
  * :mod:`~core.epistemic_disclosure.verified_contract` (P1-A) — the VERIFIED contract:
    the obligation, the proof shape, the validator, and the single sanctioned route to
    ``EpistemicState.VERIFIED`` / ``DisclosureClaim.VERIFIED``. Contract only — no
    producer; a faithful solve of a WRONG read must not verify.
"""

from __future__ import annotations

from core.epistemic_disclosure.ask_serving import (
    ServedAskDecision,
    evaluate_served_ask,
)
from core.epistemic_disclosure.disclosure_claim import (
    DEFAULT_DISCLOSURE_CLAIM,
    DisclosureClaim,
)
from core.epistemic_disclosure.disposition import (
    ServedDisposition,
    choose_served_disposition,
)
from core.epistemic_disclosure.limitation import (
    Q1B_ASK_CARVE_OUT,
    LimitationAssessment,
    LimitationKind,
    MissingSlot,
    ResolutionAction,
    assess_from_attempt,
    assess_from_family,
    terminal_for_action,
)
from core.epistemic_disclosure.verified_contract import (
    VERIFICATION_OBLIGATION,
    VerificationObligation,
    VerificationProof,
    VerificationResult,
    VerificationVerdict,
    disclosure_for_verification,
    evaluate_verification,
)

__all__ = [
    "DEFAULT_DISCLOSURE_CLAIM",
    "Q1B_ASK_CARVE_OUT",
    "VERIFICATION_OBLIGATION",
    "DisclosureClaim",
    "LimitationAssessment",
    "LimitationKind",
    "MissingSlot",
    "ResolutionAction",
    "ServedAskDecision",
    "ServedDisposition",
    "VerificationObligation",
    "VerificationProof",
    "VerificationResult",
    "VerificationVerdict",
    "assess_from_attempt",
    "assess_from_family",
    "choose_served_disposition",
    "disclosure_for_verification",
    "evaluate_served_ask",
    "evaluate_verification",
    "terminal_for_action",
]
