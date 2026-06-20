import pytest
from generate.construction_affordances import (
    all_diagnostic_families,
    lookup_family,
    lookup_by_organ,
    lookup_by_relation_type,
    make_proposal,
    propose_construction,
    ConstructionProposal,
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
    # Check that they are sorted
    assert ids == sorted(ids)
    assert ids == [
        "partition.percent_partition",
        "proportional_change.decrease_to_fraction",
    ]


def test_lookups_correctness() -> None:
    # 1. lookup_family
    f1 = lookup_family("proportional_change.decrease_to_fraction")
    assert f1 is not None
    assert f1.family_id == "proportional_change.decrease_to_fraction"

    f2 = lookup_family("partition.percent_partition")
    assert f2 is not None
    assert f2.family_id == "partition.percent_partition"

    assert lookup_family("invalid_family_id") is None

    # 2. lookup_by_organ
    assert lookup_by_organ("fraction_decrease") is f1
    assert lookup_by_organ("percent_partition") is f2
    assert lookup_by_organ("invalid_organ") is None

    # 3. lookup_by_relation_type
    assert lookup_by_relation_type("decrease_to_fraction") is f1
    assert lookup_by_relation_type("percent_of") is f2
    assert lookup_by_relation_type("invalid_relation") is None


def test_make_proposal_validation_and_status() -> None:
    span = SourceSpan("test text", 0, 9)

    # 1. Closed status (runnable = True)
    prop_closed = make_proposal(
        family_id="proportional_change.decrease_to_fraction",
        evidence_spans=(span,),
        assessment_runnable=True,
        missing_roles=(),
        active_hazards=(),
    )
    assert prop_closed.family_id == "proportional_change.decrease_to_fraction"
    assert prop_closed.relation_type == "decrease_to_fraction"
    assert prop_closed.candidate_organ == "fraction_decrease"
    assert prop_closed.evidence_spans == (span,)
    assert prop_closed.status == "closed"
    assert prop_closed.missing_roles == ()
    assert prop_closed.active_hazards == ()

    # 2. Refused status (active hazards present)
    prop_refused = make_proposal(
        family_id="proportional_change.decrease_to_fraction",
        evidence_spans=(span,),
        assessment_runnable=False,
        missing_roles=(),
        active_hazards=("unbound_base_quantity",),
    )
    assert prop_refused.status == "refused"
    assert prop_refused.active_hazards == ("unbound_base_quantity",)

    # 3. Partial status (missing roles present, no active hazards)
    prop_partial = make_proposal(
        family_id="proportional_change.decrease_to_fraction",
        evidence_spans=(span,),
        assessment_runnable=False,
        missing_roles=("base_quantity_unbound",),
        active_hazards=(),
    )
    assert prop_partial.status == "partial"
    assert prop_partial.missing_roles == ("base_quantity_unbound",)

    # 4. Proposed status (not runnable, no missing roles, no active hazards)
    prop_proposed = make_proposal(
        family_id="proportional_change.decrease_to_fraction",
        evidence_spans=(span,),
        assessment_runnable=False,
        missing_roles=(),
        active_hazards=(),
    )
    assert prop_proposed.status == "proposed"

    # 5. Invalid family_id raises KeyError
    with pytest.raises(KeyError):
        make_proposal(
            family_id="invalid_family_id",
            evidence_spans=(span,),
            assessment_runnable=False,
            missing_roles=(),
            active_hazards=(),
        )


def test_propose_construction_is_preassessment_and_carries_catalog_obligations() -> None:
    span = SourceSpan("decrease to 3/4 of", 0, 18)

    proposal = propose_construction(
        "proportional_change.decrease_to_fraction",
        (span,),
    )

    assert proposal.status == "proposed"
    assert proposal.missing_roles == ()
    assert proposal.active_hazards == ()
    assert proposal.diagnostic_only is True
    assert proposal.serving_allowed is False
    assert {role.role for role in proposal.role_obligations if role.required} == {
        "base_quantity",
        "scale",
        "state_entity",
        "transition",
    }


def test_construction_proposal_status_validation() -> None:
    span = SourceSpan("test text", 0, 9)
    # Valid status doesn't raise
    ConstructionProposal(
        family_id="proportional_change.decrease_to_fraction",
        relation_type="decrease_to_fraction",
        candidate_organ="fraction_decrease",
        evidence_spans=(span,),
        status="closed",
        missing_roles=(),
        active_hazards=(),
    )

    # Invalid status raises ValueError
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
