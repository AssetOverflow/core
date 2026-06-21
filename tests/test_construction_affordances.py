from __future__ import annotations

import pytest

from generate.construction_affordances import (
    ConstructionProposal,
    all_diagnostic_families,
    lookup_by_organ,
    lookup_by_relation_type,
    lookup_family,
    make_proposal,
    propose_construction,
)
from generate.kernel_facts import SourceSpan


def test_catalog_entries_are_diagnostic_only_and_serving_forbidden() -> None:
    families = all_diagnostic_families()
    assert len(families) == 2
    for family in families:
        assert family.diagnostic_only is True
        assert family.serving_allowed is False


def test_catalog_ordering_is_deterministic() -> None:
    families = all_diagnostic_families()
    ids = [f.family_id for f in families]
    assert ids == sorted(ids)
    assert ids == [
        "partition.percent_partition",
        "proportional_change.decrease_to_fraction",
    ]


def test_lookups_correctness() -> None:
    fraction_family = lookup_family("proportional_change.decrease_to_fraction")
    assert fraction_family is not None
    assert lookup_by_organ("fraction_decrease") is fraction_family
    assert lookup_by_relation_type("decrease_to_fraction") is fraction_family

    partition_family = lookup_family("partition.percent_partition")
    assert partition_family is not None
    assert lookup_by_organ("percent_partition") is partition_family
    assert lookup_by_relation_type("percent_of") is partition_family

    assert lookup_family("invalid_family_id") is None
    assert lookup_by_organ("invalid_organ") is None
    assert lookup_by_relation_type("invalid_relation") is None


@pytest.mark.parametrize(
    ("family_id", "relation_type", "candidate_organ", "required_roles"),
    (
        (
            "proportional_change.decrease_to_fraction",
            "decrease_to_fraction",
            "fraction_decrease",
            {"base_quantity", "scale", "state_entity", "transition"},
        ),
        (
            "partition.percent_partition",
            "percent_of",
            "percent_partition",
            {"whole", "part", "scale"},
        ),
    ),
)
def test_propose_construction_is_preassessment_and_catalog_backed(
    family_id: str,
    relation_type: str,
    candidate_organ: str,
    required_roles: set[str],
) -> None:
    span = SourceSpan("surface cue", 0, 11)

    proposal = propose_construction(family_id, (span,))

    assert proposal.family_id == family_id
    assert proposal.relation_type == relation_type
    assert proposal.candidate_organ == candidate_organ
    assert proposal.evidence_spans == (span,)
    assert proposal.status == "proposed"
    assert proposal.missing_roles == ()
    assert proposal.active_hazards == ()
    assert proposal.diagnostic_only is True
    assert proposal.serving_allowed is False
    assert {role.role for role in proposal.role_obligations if role.required} == required_roles


@pytest.mark.parametrize(
    "family_id",
    (
        "proportional_change.decrease_to_fraction",
        "partition.percent_partition",
    ),
)
def test_make_proposal_rejects_migrated_proposal_first_families(
    family_id: str,
) -> None:
    span = SourceSpan("surface cue", 0, 11)

    with pytest.raises(
        ValueError,
        match=rf"{family_id} is proposal-first; use propose_construction before assessment",
    ):
        make_proposal(
            family_id=family_id,
            evidence_spans=(span,),
            assessment_runnable=True,
            missing_roles=(),
            active_hazards=(),
        )


def test_make_proposal_still_rejects_unknown_family_ids() -> None:
    span = SourceSpan("surface cue", 0, 11)

    with pytest.raises(KeyError):
        propose_construction("invalid_family_id", (span,))


def test_construction_proposal_status_validation() -> None:
    span = SourceSpan("test text", 0, 9)
    ConstructionProposal(
        family_id="proportional_change.decrease_to_fraction",
        relation_type="decrease_to_fraction",
        candidate_organ="fraction_decrease",
        evidence_spans=(span,),
        status="closed",
        missing_roles=(),
        active_hazards=(),
    )

    with pytest.raises(ValueError, match="status must be one of"):
        ConstructionProposal(
            family_id="proportional_change.decrease_to_fraction",
            relation_type="decrease_to_fraction",
            candidate_organ="fraction_decrease",
            evidence_spans=(span,),
            status="invalid_status",
            missing_roles=(),
            active_hazards=(),
        )
