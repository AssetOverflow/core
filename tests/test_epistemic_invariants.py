"""ADR-0021 non-hardening invariant tests.

The Epistemic Grade Policy commits to:

1. `epistemic_status` is a position in the revision graph, not a trust
   tier.
2. No reviewed claim, relation, or proposition-graph edge ever becomes
   unrevisable — no `final`, `frozen`, `axiom`, or `permanent` flag may
   exist or be added on the runtime data model.
3. Coherence is the only admission signal — source-trust labels must not
   be part of the schema.

These tests are the structural checks behind those commitments.  They
are intentionally simple and read like contract assertions, not
behaviour tests.
"""

from __future__ import annotations

import dataclasses

from teaching import EpistemicStatus, PackMutationProposal, ReviewedTeachingExample
from teaching.correction import CorrectionCandidate
from teaching.review import ReviewOutcome


_FORBIDDEN_HARDENING_NAMES: frozenset[str] = frozenset({
    "final",
    "frozen",
    "axiom",
    "permanent",
    "immutable_truth",
    "sealed",
})

# Source-trust tier names that ADR-0021 §3 forbids in the schema.
_FORBIDDEN_TRUST_TIER_NAMES: frozenset[str] = frozenset({
    "peer_consensus",
    "outsider_empirical",
    "established",
    "unauthoritative",
    "credentialed",
    "source_trust",
    "authority",
    "trust_tier",
})


def _field_names(cls: type) -> set[str]:
    return {f.name for f in dataclasses.fields(cls)}


def _enum_value_strings(enum_cls) -> set[str]:
    return {member.value for member in enum_cls}


def test_pack_mutation_proposal_has_no_hardening_flag():
    """PackMutationProposal must not expose any name implying permanence."""
    names = _field_names(PackMutationProposal)
    forbidden = names & _FORBIDDEN_HARDENING_NAMES
    assert forbidden == set(), (
        f"PackMutationProposal exposes hardening flag(s) {forbidden}; "
        "ADR-0021 §2 forbids non-revisable state on the runtime data model."
    )


def test_reviewed_teaching_example_has_no_hardening_flag():
    """ReviewedTeachingExample must not expose any name implying permanence."""
    names = _field_names(ReviewedTeachingExample)
    forbidden = names & _FORBIDDEN_HARDENING_NAMES
    assert forbidden == set(), (
        f"ReviewedTeachingExample exposes hardening flag(s) {forbidden}; "
        "ADR-0021 §2 forbids non-revisable state on the runtime data model."
    )


def test_epistemic_status_enum_carries_no_trust_tier_names():
    """EpistemicStatus must describe revision-graph position, not source trust."""
    values = _enum_value_strings(EpistemicStatus)
    forbidden = values & _FORBIDDEN_TRUST_TIER_NAMES
    assert forbidden == set(), (
        f"EpistemicStatus enum contains source-trust tier value(s) {forbidden}; "
        "ADR-0021 §3 forbids credentialing the schema."
    )


def test_epistemic_status_enum_has_exactly_the_four_positions():
    """ADR-0021 §1 names the enum members precisely; no silent additions."""
    assert _enum_value_strings(EpistemicStatus) == {
        "coherent",
        "contested",
        "speculative",
        "falsified",
    }


def test_proposal_default_is_speculative():
    """ADR-0021 §Schema impact: proposals start SPECULATIVE; promotion is
    a separate, review-mediated transition."""
    proposal = PackMutationProposal(
        proposal_id="x",
        candidate_id="y",
        subject="z",
        correction_text="a knows b",
        prior_surface="",
    )
    assert proposal.epistemic_status is EpistemicStatus.SPECULATIVE


def test_proposal_with_status_returns_new_immutable_proposal():
    """Immutable update — the original is never mutated."""
    original = PackMutationProposal(
        proposal_id="x",
        candidate_id="y",
        subject="z",
        correction_text="a knows b",
        prior_surface="",
    )
    promoted = original.with_status(EpistemicStatus.COHERENT)

    assert promoted.epistemic_status is EpistemicStatus.COHERENT
    assert original.epistemic_status is EpistemicStatus.SPECULATIVE
    assert promoted is not original


def test_reviewed_example_default_is_speculative_for_accepted_outcome():
    """Acceptance is orthogonal to coherence ratification per ADR-0021
    §Schema impact: 'Accepting a proposal is not the same as ratifying
    it as COHERENT.'"""
    from generate.intent import DialogueIntent, IntentTag

    intent = DialogueIntent(tag=IntentTag.DEFINITION, subject="a")
    candidate = CorrectionCandidate(
        candidate_id="c1",
        intent=intent,
        correction_text="a is b",
        prior_surface="",
        prior_turn=0,
    )
    from teaching import review_correction

    reviewed = review_correction(candidate)
    assert reviewed.outcome is ReviewOutcome.ACCEPTED
    assert reviewed.epistemic_status is EpistemicStatus.SPECULATIVE
