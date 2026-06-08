"""P0-2 — the DisclosureClaim axis (the epistemic claim a served response makes).

A served response carries two ORTHOGONAL governance properties:

  * ``ReachLevel`` (``core/response_governance/policy.py``) — how far PAST
    fully-grounded fact the response reaches (STRICT < APPROXIMATE < EXTRAPOLATE
    < CREATIVE).
  * ``DisclosureClaim`` (here) — the EPISTEMIC CLAIM the response makes about its
    own truth status.

These are deliberately separate axes. ``verified`` is **not** a reach level — it is
a claim about *proof state*, not about how far the response speculates. Conflating
them (e.g. a hypothetical ``ReachLevel.VERIFIED``) would let a proven answer inherit
an "approximate" surface, or an approximation inherit a "verified" badge. Keeping the
axes distinct is the architectural commitment behind the Stage-2 lockfile
(``docs/analysis/stage2-epistemic-disclosure-bus-verified-v1-scoping-2026-06-08.md`` §0).

**Discipline — no claim without a producer** (the spine enforces on itself what it
enforces on answers). Every member has a real or imminent emitter:

  * ``NONE``          — every response today (the baseline; STRICT + NONE).
  * ``APPROXIMATE``   — active: the cognition Step-E disclosed estimate
                        (``estimation_enabled`` / ADR-0206 §5).
  * ``PROPOSAL_ONLY`` — active: ``teaching/proposals`` emits review-only proposals.
  * ``VERIFIED``      — the imminent frontier: its producer is Phase 1 (P1-A..),
                        declared because it is the v1 target the bus is built around.

Two claims are intentionally ABSENT, because nothing can emit them — and the spine
will not declare a label it cannot earn:

  * ``PROVEN``    — a claim stronger than VERIFIED; no plan to build a producer.
  * ``ESTIMATED`` — a *future* split of ``APPROXIMATE`` into a distinct
                    numeric-estimate claim, added ONLY once a real estimator producer
                    exists. Until then the cognition estimate is ``APPROXIMATE``.

P0-2 ships ONLY the axis + its default. No bus behaviour, no mapping to a disposition
(that is P0-3 / ServedDisposition). Off-serving: this module imports nothing.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class DisclosureClaim(str, Enum):
    """The epistemic claim a served surface makes about its own truth status.

    Orthogonal to ``ReachLevel``. ``str``-valued for stable serialization into
    telemetry / disposition records (the same convention as ``EpistemicState``).
    """

    NONE = "none"  # no epistemic claim beyond the plain surface (the default)
    VERIFIED = "verified"  # independently confirmed under a canonical-comparison contract
    APPROXIMATE = "approximate"  # a disclosed best-estimate from incomplete evidence
    PROPOSAL_ONLY = "proposal_only"  # offered as a proposal for review, not asserted


#: The default claim: a surface asserts nothing about its truth status unless a
#: producer upgrades it. ``STRICT`` reach + ``NONE`` claim is today's every-response
#: baseline.
DEFAULT_DISCLOSURE_CLAIM: DisclosureClaim = DisclosureClaim.NONE


__all__ = ["DEFAULT_DISCLOSURE_CLAIM", "DisclosureClaim"]
