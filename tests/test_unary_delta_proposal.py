"""Diagnostic-only contract tests for ``state_change.unary_delta``."""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import generate.problem_frame_contracts as problem_frame_contracts
import pytest

from generate.kernel_facts import SourceSpan
from generate.problem_frame_builder import build_problem_frame
from generate.problem_frame_contracts import assess_contracts, assess_unary_delta


FAMILY_ID = "state_change.unary_delta"
CANDIDATE_ORGAN = "unary_delta_transition"


def _proposal(frame):
    proposals = tuple(
        proposal for proposal in frame.proposals if proposal.family_id == FAMILY_ID
    )
    assert len(proposals) == 1
    return proposals[0]


def _relation(frame):
    relations = tuple(
        relation
        for relation in frame.bound_relations
        if relation.relation_type == "unary_delta"
    )
    assert len(relations) == 1
    return relations[0]


def _assessment(frame):
    assessments = tuple(
        assessment
        for assessment in assess_contracts(frame)
        if assessment.candidate_organ == CANDIDATE_ORGAN
    )
    assert len(assessments) == 1
    return assessments[0]


@pytest.mark.parametrize(
    ("problem_text", "cue", "direction"),
    (
        ("Ana gained 3 marbles.", "gained", "increase"),
        ("The jar lost 2 cookies.", "lost", "decrease"),
    ),
)
def test_exact_local_gained_lost_event_is_proposed_bound_and_assessed(
    problem_text: str,
    cue: str,
    direction: str,
) -> None:
    frame = build_problem_frame(problem_text)
    proposal = _proposal(frame)
    relation = _relation(frame)
    assessment = _assessment(frame)

    assert proposal.status == "proposed"
    assert proposal.diagnostic_only is True
    assert proposal.serving_allowed is False
    assert not hasattr(proposal, "runnable")

    roles = {role.role: role for role in relation.roles}
    assert set(roles) == {"action_cue", "delta_quantity", "changed_object", "direction"}
    assert roles["direction"].target_id == direction
    assert roles["action_cue"].target_id == "cue-0000"
    assert roles["action_cue"].evidence_spans[0].text == cue

    assert len(frame.unary_delta_cues) == 1
    assert frame.unary_delta_cues[0].cue_id == "cue-0000"
    assert frame.unary_delta_cues[0].surface == cue
    assert frame.unary_delta_cues[0].direction == direction

    assert assessment.runnable is True
    assert assessment.missing_bindings == ()
    assert assessment.unresolved_hazards == ()
    assert all(
        span.text == problem_text[span.start : span.end]
        for span in (
            *proposal.evidence_spans,
            *relation.evidence_spans,
            *assessment.evidence_spans,
        )
    )


def test_builder_publishes_unary_delta_proposal_before_assessment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_statuses: list[str] = []
    original = problem_frame_contracts.assess_contracts

    def observe(frame):
        observed_statuses.append(_proposal(frame).status)
        return original(frame)

    monkeypatch.setattr(problem_frame_contracts, "assess_contracts", observe)

    frame = build_problem_frame("Ana gained 3 marbles.")

    assert observed_statuses == ["proposed"]
    assert _assessment(frame).runnable is True


def test_proposal_free_frame_does_not_dispatch_unary_delta_contract() -> None:
    frame = build_problem_frame("Ana gained 3 marbles.")
    proposal_free = dataclasses.replace(frame, proposals=())

    assert CANDIDATE_ORGAN not in {
        assessment.candidate_organ for assessment in assess_contracts(proposal_free)
    }
    assessment = assess_unary_delta(proposal_free)
    assert assessment.runnable is False
    assert "unary_delta_proposal_required" in assessment.missing_bindings


@pytest.mark.parametrize(
    "problem_text",
    (
        "There are 12 apples.",
        "Tom has 12 apples.",
        "Tom gave Ana 3 apples.",
        "Tom sent Ana 3 apples.",
        "Tom received 3 apples.",
        "Tom bought 3 apples.",
        "Tom put 3 apples in the box.",
        "Tom took 3 apples from the box.",
        "Tom had 12 apples and lost 3.",
        "Tom gained 3 apples and oranges.",
        "Tom gained 3 and 4 apples.",
        "Tom gained 3 more apples than Ana.",
        "20% of apples were gained.",
        "3 apples per child were gained.",
        "Tom did not gain 3 apples.",
        "Tom gained 3 apples and lost 2 apples.",
    ),
)
def test_confusers_do_not_dispatch_unary_delta(problem_text: str) -> None:
    frame = build_problem_frame(problem_text)

    assert FAMILY_ID not in {proposal.family_id for proposal in frame.proposals}
    assert not any(
        relation.relation_type == "unary_delta" for relation in frame.bound_relations
    )
    assert CANDIDATE_ORGAN not in {
        assessment.candidate_organ for assessment in assess_contracts(frame)
    }


def test_missing_object_literal_surface_stays_unbound_and_non_runnable() -> None:
    frame = build_problem_frame("Tom gained 3.")

    assert FAMILY_ID in {proposal.family_id for proposal in frame.proposals}
    assert not any(
        relation.relation_type == "unary_delta" for relation in frame.bound_relations
    )
    assessment = _assessment(frame)
    assert assessment.runnable is False
    assert "changed_object_unbound" in assessment.missing_bindings


def test_missing_quantity_blocks_runnable_unary_delta() -> None:
    frame = build_problem_frame("Tom gained 3 apples.")
    relation = _relation(frame)
    stripped_roles = tuple(
        role for role in relation.roles if role.role != "delta_quantity"
    )
    broken = dataclasses.replace(
        frame, bound_relations=(dataclasses.replace(relation, roles=stripped_roles),)
    )

    assessment = assess_unary_delta(broken)

    assert assessment.runnable is False
    assert "delta_quantity_unbound" in assessment.missing_bindings


def test_quantity_kind_conflict_blocks_runnable_unary_delta() -> None:
    frame = build_problem_frame("Tom gained 3 degrees.")
    assessment = _assessment(frame)

    assert assessment.runnable is False
    assert "quantity_kind_unresolved" in assessment.missing_bindings


def test_synthetic_or_mismatched_unary_delta_evidence_refuses() -> None:
    frame = build_problem_frame("Ana gained 3 marbles.")
    proposal = _proposal(frame)
    relation = _relation(frame)
    synthetic = SourceSpan("synthetic", 0, 9)
    cue = SourceSpan("Ana gained", 0, 10)
    bad_relation = dataclasses.replace(
        relation,
        roles=tuple(
            dataclasses.replace(role, evidence_spans=(synthetic,))
            if role.role == "action_cue"
            else role
            for role in relation.roles
        ),
        evidence_spans=(cue, *relation.evidence_spans[1:]),
    )
    broken = dataclasses.replace(
        frame,
        proposals=(dataclasses.replace(proposal, evidence_spans=(synthetic,)),),
        bound_relations=(bad_relation,),
    )

    assessment = assess_unary_delta(broken)

    assert assessment.runnable is False
    assert "provenance_span_inexact" in assessment.missing_bindings


def test_unary_delta_replay_is_deterministic() -> None:
    problem_text = "Ana gained 3 marbles."

    first = build_problem_frame(problem_text)
    second = build_problem_frame(problem_text)

    assert first.proposals == second.proposals
    assert first.bound_relations == second.bound_relations
    assert assess_contracts(first) == assess_contracts(second)


def test_existing_proposal_first_families_do_not_gain_unary_delta_dispatch() -> None:
    percent_partition = (
        "A school has 100 students. Half of the students are girls, the other half are boys. "
        "20% of the girls have dogs and 10% of the boys have dogs. "
        "How many students own dogs?"
    )
    fraction_decrease = (
        "A tank's temperature will decrease to 3/4 of its current temperature. "
        "If the current temperature is 84 degrees, how many degrees will it decrease by?"
    )
    quantity_entity = "A school has 100 students."

    for problem_text in (percent_partition, fraction_decrease, quantity_entity):
        frame = build_problem_frame(problem_text)
        assert FAMILY_ID not in {proposal.family_id for proposal in frame.proposals}
        assert CANDIDATE_ORGAN not in {
            assessment.candidate_organ for assessment in assess_contracts(frame)
        }


def test_missing_object_confuser_strict_isolation() -> None:
    # Tom gained 3.
    # Expected: state_change.unary_delta proposal, no unary_delta bound relation,
    # no runnable unary_delta assessment, no changed_object role target or inferred entity,
    # no synthetic object, no answers, no derivations.
    frame = build_problem_frame("Tom gained 3.")
    assert FAMILY_ID in {proposal.family_id for proposal in frame.proposals}
    assert not any(r.relation_type == "unary_delta" for r in frame.bound_relations)
    assessment = _assessment(frame)
    assert assessment.runnable is False
    assert "changed_object_unbound" in assessment.missing_bindings


def test_missing_quantity_confuser_strict_isolation() -> None:
    # Tom gained apples.
    # Expected: state_change.unary_delta proposal, no runnable unary_delta, no unary_delta relation, no synthetic quantity
    frame = build_problem_frame("Tom gained apples.")
    assert FAMILY_ID in {proposal.family_id for proposal in frame.proposals}
    assert not any(r.relation_type == "unary_delta" for r in frame.bound_relations)
    assessment = _assessment(frame)
    assert assessment.runnable is False
    assert "delta_quantity_unbound" in assessment.missing_bindings


@pytest.mark.parametrize(
    ("problem_text", "cue", "direction", "qty_text", "obj_text"),
    (
        ("Ana gained 3 marbles.", "gained", "increase", "3", "marbles"),
        ("The jar lost 2 cookies.", "lost", "decrease", "2", "cookies"),
    ),
)
def test_positive_controls_strict_isolation(
    problem_text: str,
    cue: str,
    direction: str,
    qty_text: str,
    obj_text: str,
) -> None:
    frame = build_problem_frame(problem_text)

    # Exactly one unary_delta proposal
    unary_proposals = [p for p in frame.proposals if p.family_id == FAMILY_ID]
    assert len(unary_proposals) == 1
    proposal = unary_proposals[0]

    # Proposal status exactly "proposed"
    assert proposal.status == "proposed"
    # Diagnostic-only / serving-disallowed posture preserved
    assert proposal.diagnostic_only is True
    assert proposal.serving_allowed is False
    assert not hasattr(proposal, "runnable")

    # Exactly one unary_delta relation
    unary_relations = [
        r for r in frame.bound_relations if r.relation_type == "unary_delta"
    ]
    assert len(unary_relations) == 1
    relation = unary_relations[0]

    roles = {role.role: role for role in relation.roles}
    assert set(roles) == {"action_cue", "delta_quantity", "changed_object", "direction"}
    assert roles["direction"].target_id == direction

    # Spans
    cue_span = roles["action_cue"].evidence_spans[0]
    qty_span = roles["delta_quantity"].evidence_spans[0]
    obj_span = roles["changed_object"].evidence_spans[0]

    assert cue_span.text == cue
    assert qty_span.text == qty_text
    assert obj_span.text == obj_text

    # Exact span assertions
    assert problem_text[cue_span.start : cue_span.end] == cue
    assert problem_text[qty_span.start : qty_span.end] == qty_text
    assert problem_text[obj_span.start : obj_span.end] == obj_text

    # Runnable ContractAssessment only when role-complete
    unary_assessments = [
        a for a in assess_contracts(frame) if a.candidate_organ == CANDIDATE_ORGAN
    ]
    assert len(unary_assessments) == 1
    assessment = unary_assessments[0]
    assert assessment.runnable is True
    assert assessment.missing_bindings == ()
    assert assessment.unresolved_hazards == ()

    # No answer or derivation or serving path
    assert not hasattr(frame, "answer")
    assert not hasattr(frame, "derivation")


@pytest.mark.parametrize(
    "problem_text",
    (
        "There are 12 apples.",
        "Tom has 12 apples.",
    ),
)
def test_static_quantity_possession_isolation(problem_text: str) -> None:
    frame = build_problem_frame(problem_text)

    # May exercise existing quantity_entity behavior if already authorized
    # but must not emit unary_delta proposal, relation, or assessment
    assert FAMILY_ID not in {p.family_id for p in frame.proposals}
    assert not any(r.relation_type == "unary_delta" for r in frame.bound_relations)
    assert CANDIDATE_ORGAN not in {a.candidate_organ for a in assess_contracts(frame)}


@pytest.mark.parametrize(
    "problem_text",
    (
        "Tom gave Ana 3 apples.",
        "Tom sent Ana 3 apples.",
        "Tom received 3 apples.",
        "Tom bought 3 apples.",
        "Tom sold 3 apples.",
        "Tom spent 3 dollars.",
    ),
)
def test_transfer_isolation(problem_text: str) -> None:
    frame = build_problem_frame(problem_text)
    # no unary_delta proposal, no relation, no owner/source/target inference, no transfer semantics
    assert FAMILY_ID not in {p.family_id for p in frame.proposals}
    assert not any(r.relation_type == "unary_delta" for r in frame.bound_relations)
    assert CANDIDATE_ORGAN not in {a.candidate_organ for a in assess_contracts(frame)}


@pytest.mark.parametrize(
    "problem_text",
    (
        "Tom put 3 apples in the box.",
        "Tom took 3 apples from the box.",
        "Tom moved 3 apples into the basket.",
    ),
)
def test_containment_movement_isolation(problem_text: str) -> None:
    frame = build_problem_frame(problem_text)
    # no unary_delta proposal, no relation, no container/source/target inference
    assert FAMILY_ID not in {p.family_id for p in frame.proposals}
    assert not any(r.relation_type == "unary_delta" for r in frame.bound_relations)
    assert CANDIDATE_ORGAN not in {a.candidate_organ for a in assess_contracts(frame)}


@pytest.mark.parametrize(
    "problem_text",
    (
        "Tom had 12 apples and now has 15 apples.",
        "Tom had 12 apples and lost 3.",
        "There are 12 apples. Tom lost 3.",
    ),
)
def test_before_after_isolation(problem_text: str) -> None:
    frame = build_problem_frame(problem_text)
    # no broad before/after state inference, no cross-sentence repair,
    # no object borrowed from prior sentence/clause, no arithmetic closure, no answer
    assert FAMILY_ID not in {p.family_id for p in frame.proposals}
    assert not any(r.relation_type == "unary_delta" for r in frame.bound_relations)
    assert CANDIDATE_ORGAN not in {a.candidate_organ for a in assess_contracts(frame)}


@pytest.mark.parametrize(
    "problem_text",
    (
        "Tom gained 3 more apples than Ana.",
        "3 apples per child were gained.",
        "20% of apples were gained.",
    ),
)
def test_comparison_rate_percent_isolation(problem_text: str) -> None:
    frame = build_problem_frame(problem_text)
    # no unary_delta relation, no rate/percent/comparison collapse into unary_delta
    assert FAMILY_ID not in {p.family_id for p in frame.proposals}
    assert not any(r.relation_type == "unary_delta" for r in frame.bound_relations)
    assert CANDIDATE_ORGAN not in {a.candidate_organ for a in assess_contracts(frame)}


@pytest.mark.parametrize(
    "problem_text",
    (
        "Tom did not gain 3 apples.",
        "Tom may have gained 3 apples.",
        "3 apples were gained by Tom.",
    ),
)
def test_negation_modality_passive_isolation(problem_text: str) -> None:
    frame = build_problem_frame(problem_text)
    # Proposes for gained matches, but doesn't propose for did not gain
    if "gained" in problem_text:
        assert FAMILY_ID in {p.family_id for p in frame.proposals}
        assessment = _assessment(frame)
        assert assessment.runnable is False
    else:
        assert FAMILY_ID not in {p.family_id for p in frame.proposals}


@pytest.mark.parametrize(
    "problem_text",
    (
        "Tom gained 3 apples and lost 2 apples.",
        "Tom gained 3 and 4 apples.",
        "Tom gained 3 apples and oranges.",
    ),
)
def test_multi_event_ambiguity_isolation(problem_text: str) -> None:
    frame = build_problem_frame(problem_text)
    # no single unary_delta closure, no arbitrary first-match success,
    # no silent ambiguity normalization
    assert FAMILY_ID not in {p.family_id for p in frame.proposals}
    assert not any(
        a.candidate_organ == CANDIDATE_ORGAN and a.runnable
        for a in assess_contracts(frame)
    )
    # Ensure there isn't exactly one relation resolving both
    unary_relations = [
        r for r in frame.bound_relations if r.relation_type == "unary_delta"
    ]
    assert len(unary_relations) == 0


def test_unit_object_conflict_isolation() -> None:
    # Tom gained 3 degrees.
    # Expected: no runnable unary_delta (blocked by unit/quantity kind unresolved),
    # no object widening, no answer
    frame = build_problem_frame("Tom gained 3 degrees.")
    assert not any(
        a.candidate_organ == CANDIDATE_ORGAN and a.runnable
        for a in assess_contracts(frame)
    )


def test_exact_span_assertions() -> None:
    frame = build_problem_frame("Ana gained 3 marbles.")
    proposal = [p for p in frame.proposals if p.family_id == FAMILY_ID][0]
    relation = [r for r in frame.bound_relations if r.relation_type == "unary_delta"][0]
    assessment = [
        a for a in assess_contracts(frame) if a.candidate_organ == CANDIDATE_ORGAN
    ][0]

    # Positives: problem_text[span.start:span.end] == span.text
    for span in (
        *proposal.evidence_spans,
        *relation.evidence_spans,
        *assessment.evidence_spans,
    ):
        assert frame.problem_text[span.start : span.end] == span.text

    # Negatives: no synthetic span, no widened span, no normalized span
    # We check that there are no spans that do not exactly slice the text or are empty/synthesized
    for span in (*proposal.evidence_spans, *relation.evidence_spans):
        assert span.start >= 0
        assert span.end <= len(frame.problem_text)
        assert span.end > span.start
        assert span.text.strip() == span.text


def test_authority_boundary_checks() -> None:
    # proposals remain hypotheses
    # proposal object does not carry runnable/refused authority
    frame = build_problem_frame("Ana gained 3 marbles.")
    proposal = [p for p in frame.proposals if p.family_id == FAMILY_ID][0]

    assert not hasattr(proposal, "runnable")
    assert not hasattr(proposal, "verdict")
    assert not hasattr(proposal, "missing_bindings")
    assert not hasattr(proposal, "unresolved_hazards")

    # ContractAssessment is sole runnable/refused authority
    assessment = [
        a for a in assess_contracts(frame) if a.candidate_organ == CANDIDATE_ORGAN
    ][0]
    assert hasattr(assessment, "runnable")
    assert hasattr(assessment, "missing_bindings")
    assert hasattr(assessment, "unresolved_hazards")

    # proposal-free frames do not dispatch unary_delta
    proposal_free = dataclasses.replace(frame, proposals=())
    assert CANDIDATE_ORGAN not in {
        a.candidate_organ for a in assess_contracts(proposal_free)
    }


def test_forbidden_import_coupling_checks() -> None:
    # Add guard coverage that unary_delta does not import/call:
    # generate.derivation.*, generate.math_candidate_graph, legacy semantic-state ledger, runtime serving paths
    forbidden = [
        "generate.derivation",
        "generate.math_candidate_graph",
        "generate.derivation.state",
        "chat.runtime",
        "runtime.serving",
    ]
    for module in (
        "generate.problem_frame_builder",
        "generate.problem_frame_contracts",
    ):
        path = Path(__import__(module, fromlist=["__file__"]).__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        for name in ast.walk(tree):
            if isinstance(name, ast.Import):
                for alias in name.names:
                    imported.add(alias.name)
        for forbid in forbidden:
            assert forbid not in imported
            for imp in imported:
                assert not imp.startswith(forbid)


def test_unary_delta_cue_conformance() -> None:
    from generate.problem_frame import GroundedUnaryDeltaCue
    from generate.kernel_facts import SourceSpan

    # 1. Invalid surface/action_kind/direction triples must raise ValueError
    span = SourceSpan("gained", 0, 6)
    with pytest.raises(ValueError):
        GroundedUnaryDeltaCue("cue-0000", "gained", "loss", "increase", span)
    with pytest.raises(ValueError):
        GroundedUnaryDeltaCue("cue-0000", "gained", "gain", "decrease", span)
    with pytest.raises(ValueError):
        GroundedUnaryDeltaCue("cue-0000", "lost", "gain", "decrease", span)
    with pytest.raises(ValueError):
        GroundedUnaryDeltaCue("cue-0000", "lost", "loss", "increase", span)
    with pytest.raises(ValueError):
        GroundedUnaryDeltaCue("cue-0000", "gained", "gain", "increase", SourceSpan("lost", 0, 4))

    # Valid triples must succeed
    c1 = GroundedUnaryDeltaCue("cue-0001", "gained", "gain", "increase", span)
    assert c1.cue_id == "cue-0001"

    # 2. Test exact span resolution in _bound_relations
    from generate.problem_frame_builder import _bound_relations, GroundedMention, MentionBinding, ConstructionProposal
    mentions = (
        GroundedMention("m-0000", "quantity", "3", SourceSpan("3", 7, 8)),
        GroundedMention("m-0001", "object", "apples", SourceSpan("apples", 9, 15)),
    )
    bindings = (
        MentionBinding("b-0000", "quantity_entity", "m-0000", "m-0001", (SourceSpan("3 apples", 7, 15),)),
    )
    proposals = (
        ConstructionProposal(
            family_id="state_change.unary_delta",
            relation_type="unary_delta",
            candidate_organ="unary_delta_transition",
            evidence_spans=(span,),
            status="proposed",
            diagnostic_only=True,
            serving_allowed=False,
        ),
    )
    # If the cue has a different ID and is passed in, _bound_relations must resolve and use it
    cues = (
        GroundedUnaryDeltaCue("cue-1234", "gained", "gain", "increase", span),
    )
    relations = _bound_relations("gained 3 apples", mentions, bindings, proposals, cues)
    assert len(relations) == 1
    action_cue_role = next(r for r in relations[0].roles if r.role == "action_cue")
    assert action_cue_role.target_id == "cue-1234"
