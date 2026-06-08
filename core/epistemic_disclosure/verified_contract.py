"""P1-A — the VERIFIED contract (the meaning of "verified", before any producer).

This module defines WHAT IT MEANS for a result to earn ``DisclosureClaim.VERIFIED`` /
``EpistemicState.VERIFIED`` — the soundness≠correctness gate the whole VERIFIED lane
rests on. It ships ONLY the contract: the obligation, the proof SHAPE a producer must
fill, the validator that enforces the obligation, and the single sanctioned route from
a validated proof to the verified state/claim.

It does NOT produce proofs. There is no reader, no solver, no back-substitution
computation, no serving, no ``verify.py`` call, no ``verified_serving_enabled``. P1-B+
fill :class:`VerificationProof` with real digests; P1-A only fixes the rules a proof
must satisfy — and, above all, the rule that makes the lane safe:

    A faithful solve of a WRONG read must NOT verify.

**The mechanism.** Verification requires TWO INDEPENDENT reads (distinct reader
lineages) that CONVERGE on the same canonical structure:

  * a *wrong* primary read is caught because the independent read **disagrees** —
    back-substitution alone cannot catch a read error (it only proves the solver was
    faithful to whatever structure it was handed);
  * a single reader run twice ("same answer twice") is rejected as **not independent**.

Neither gold-agreement, nor absence-of-refusal, nor a second solver over ONE read can
earn VERIFIED; only this contract can. (See [[VERIFIED-canonical-comparison-scoping-2026-06-06]]:
"independence must be in the READING, not the solving".)

**Discipline.** ``EpistemicState.VERIFIED`` must be reached ONLY via
:func:`disclosure_for_verification` over a VERIFIED :class:`VerificationResult` — never
constructed directly by producer/serving code. A future architectural invariant can
scan for direct emission; P1-A establishes the route.

Off-serving: imports no ``generate.derivation`` / ``core.reliability_gate``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique

from core.epistemic_disclosure.disclosure_claim import DisclosureClaim
from core.epistemic_disclosure.limitation import LimitationAssessment
from core.epistemic_state import EpistemicState


@unique
class VerificationVerdict(str, Enum):
    """Whether a result earns the VERIFIED claim. There is no middle state — a result
    either survives every obligation or it does not verify (refuse-preferring)."""

    VERIFIED = "verified"
    NOT_VERIFIED = "not_verified"


@dataclass(frozen=True, slots=True)
class VerificationObligation:
    """The declarative contract: which checks a proof must survive to be VERIFIED.

    A schema naming proof obligations (CLAUDE.md "Schema-Defined Proof Obligations").
    The canonical :data:`VERIFICATION_OBLIGATION` sets every flag ``True``; the flags
    exist so a test can prove each obligation is LOAD-BEARING — relax exactly one and
    the corresponding poison case slips through (see ``test_verified_contract.py``).
    """

    requires_independent_read: bool  # two DISTINCT reader lineages — not the same read twice
    rejects_wrong_read_even_if_solved: bool  # the two reads must CONVERGE — catches a wrong read
    requires_back_substitution: bool  # the answer back-substitutes into the canonical structure
    requires_boundary_clear: bool  # no organ boundary fired in the chain


#: The canonical, fully-strict obligation. VERIFIED requires ALL of it.
VERIFICATION_OBLIGATION: VerificationObligation = VerificationObligation(
    requires_independent_read=True,
    rejects_wrong_read_even_if_solved=True,
    requires_back_substitution=True,
    requires_boundary_clear=True,
)


@dataclass(frozen=True, slots=True)
class VerificationProof:
    """The replayable proof shape a producer (P1-B+) must fill. P1-A defines the shape
    and the rules; it computes none of these digests.

    The two reads are kept separate ON PURPOSE: ``primary_reader_lineage`` /
    ``independent_reader_lineage`` must DIFFER (independence), and ``primary_read_digest``
    / ``independent_read_digest`` must MATCH (convergence on one canonical structure).
    Independence + convergence together are what reject a faithful solve of a wrong read.
    """

    source_problem_digest: str  # provenance: hash of the problem text
    primary_reader_lineage: str  # identity of the primary reader
    independent_reader_lineage: str  # identity of the independent cross-check reader
    primary_read_digest: str  # canonical structure the primary read produced
    independent_read_digest: str  # canonical structure the independent read produced
    derivation_digest: str  # the derivation from the STATED quantities
    back_substitution_digest: str  # back-substitution into the canonical structure
    boundary_clear: bool  # no organ boundary fired
    contradiction_clear: bool  # no contradiction family fired


# Reason codes for a failed obligation — each names exactly one violated rule.
REASON_READS_NOT_INDEPENDENT = "reads_not_independent"  # same reader lineage twice
REASON_READS_DISAGREE = "reads_disagree"  # the wrong-read catcher
REASON_NO_BACK_SUBSTITUTION = "no_back_substitution"
REASON_BOUNDARY_FIRED = "boundary_fired"
REASON_CONTRADICTION_PRESENT = "contradiction_present"
REASON_INCOMPLETE_PROOF = "incomplete_proof_digest"
REASON_UNRESOLVED_LIMITATION = "unresolved_limitation"


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """The verdict plus the specific obligations that failed (empty iff VERIFIED)."""

    verdict: VerificationVerdict
    failed_checks: tuple[str, ...]


def evaluate_verification(
    proof: VerificationProof,
    *,
    limitation: LimitationAssessment | None,
    obligation: VerificationObligation = VERIFICATION_OBLIGATION,
) -> VerificationResult:
    """Apply the VERIFIED contract to a proof. Refuse-preferring: VERIFIED only if
    EVERY obligation survives; otherwise NOT_VERIFIED with the failed checks.

    Pure logic over the proof fields — it does NOT compute or trust any digest, it only
    enforces the rules a producer's proof must satisfy. ``limitation`` is the
    contemplation outcome: a verified answer cannot coexist with an unresolved
    limitation (a contradiction, an ambiguity, a missing datum).
    """
    failed: list[str] = []

    if obligation.requires_independent_read and (
        proof.primary_reader_lineage == proof.independent_reader_lineage
    ):
        failed.append(REASON_READS_NOT_INDEPENDENT)

    if obligation.rejects_wrong_read_even_if_solved and (
        proof.primary_read_digest != proof.independent_read_digest
    ):
        failed.append(REASON_READS_DISAGREE)

    if obligation.requires_back_substitution and not proof.back_substitution_digest:
        failed.append(REASON_NO_BACK_SUBSTITUTION)

    if obligation.requires_boundary_clear and not proof.boundary_clear:
        failed.append(REASON_BOUNDARY_FIRED)

    # Non-negotiable checks (NOT gated by the obligation flags):
    if not proof.contradiction_clear:
        failed.append(REASON_CONTRADICTION_PRESENT)

    if not (
        proof.source_problem_digest
        and proof.primary_read_digest
        and proof.derivation_digest
    ):
        failed.append(REASON_INCOMPLETE_PROOF)

    if limitation is not None:
        failed.append(REASON_UNRESOLVED_LIMITATION)

    verdict = (
        VerificationVerdict.VERIFIED if not failed else VerificationVerdict.NOT_VERIFIED
    )
    return VerificationResult(verdict=verdict, failed_checks=tuple(failed))


def disclosure_for_verification(
    result: VerificationResult,
) -> tuple[EpistemicState, DisclosureClaim]:
    """The ONLY sanctioned route to a verified state/claim.

    VERIFIED verdict → (``EpistemicState.VERIFIED``, ``DisclosureClaim.VERIFIED``);
    anything else → (``UNDETERMINED``, ``NONE``). Producer/serving code must reach
    ``EpistemicState.VERIFIED`` THROUGH this gate, never by constructing it directly —
    that is what keeps "gold agreement" / "same answer twice" / "no refusal" from ever
    masquerading as verified.
    """
    if result.verdict is VerificationVerdict.VERIFIED:
        return EpistemicState.VERIFIED, DisclosureClaim.VERIFIED
    return EpistemicState.UNDETERMINED, DisclosureClaim.NONE


__all__ = [
    "VERIFICATION_OBLIGATION",
    "VerificationObligation",
    "VerificationProof",
    "VerificationResult",
    "VerificationVerdict",
    "disclosure_for_verification",
    "evaluate_verification",
]
