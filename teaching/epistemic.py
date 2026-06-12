"""Epistemic Grade Policy — typed status surface per ADR-0021.

`EpistemicStatus` is a *position in the revision graph*, not a trust tier.
Source labels (peer_consensus, outsider_empirical, established,
unauthoritative) are deliberately not part of this enum — they would
re-import the bias ADR-0021 refuses.

The four positions form an open lattice under review.  No member carries
a "hardened" or "permanent" flag (non-hardening invariant, ADR-0021 §2).
Every claim remains revisable; a Stage-3 inversion path is always
available for `FALSIFIED` claims.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EpistemicStatus(Enum):
    """Position of a claim in the reviewed revision graph.

    Coherence is the only admission signal (ADR-0021 §3): a status is a
    function of coherence with the existing reviewed field, never of
    source authority, credentials, or the system's own asserted output.

    The *judgment behind* a transition is curator-mediated by default —
    ``review_correction`` carries the resulting status as an input, it does
    not compute it.  One arm of ADR-0021's "Named gap (v2 work)" is now
    wired (ADR-0218, ratified 2026-06-11): for the deductively *entailed*
    subclass, ``teaching/proof_promotion.py`` certifies entailment over an
    all-COHERENT, curator-certified premise set via the sound
    ``deductive_logic_v1`` engine, and
    ``VaultStore.apply_certified_promotion`` owns the SPECULATIVE→COHERENT
    transition after independent re-verification.  No runtime turn path
    invokes it yet.  Every other transition remains curator-mediated — see
    ``docs/issues/proof-carrying-coherence-promotion.md``.
    """

    COHERENT = "coherent"
    CONTESTED = "contested"
    SPECULATIVE = "speculative"
    FALSIFIED = "falsified"


# Statuses that admit a claim as evidence in downstream inference.
# `SPECULATIVE` is admissible only as a candidate, not as evidence.
# `CONTESTED` is admissible but cannot drive inferences depending on its truth.
# `FALSIFIED` is retained for provenance and Stage-3 inversion, not evidence.
ADMISSIBLE_AS_EVIDENCE: frozenset[EpistemicStatus] = frozenset({
    EpistemicStatus.COHERENT,
})


def parse_status(value: str | None) -> EpistemicStatus:
    """Parse a serialised status string, defaulting to SPECULATIVE.

    SPECULATIVE is the safe default at proposal creation per ADR-0021
    §Schema impact: "transitions to COHERENT / CONTESTED / FALSIFIED only
    via the review path."  An absent or unknown value must not silently
    promote a claim to COHERENT.
    """
    if value is None or value == "":
        return EpistemicStatus.SPECULATIVE
    for status in EpistemicStatus:
        if status.value == value:
            return status
    return EpistemicStatus.SPECULATIVE
