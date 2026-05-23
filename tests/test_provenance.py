"""Unit tests for core.cognition.provenance.

Covers the four expected source profiles:
- pack only (intent classified, no vault, no teaching)
- pack + vault (recall fired)
- pack + teaching (correction captured)
- no provenance (UNKNOWN intent, no vault, no teaching)
"""

from __future__ import annotations

import numpy as np

from core.cognition.provenance import compute_provenance
from core.cognition.result import CognitiveTurnResult
from field.state import FieldState
from generate.articulation import ArticulationPlan
from generate.intent import DialogueIntent, IntentTag
from generate.proposition import Proposition
from teaching.source import ProposalSource
from teaching.store import PackMutationProposal


def _zero_versor() -> np.ndarray:
    v = np.zeros(32, dtype=np.float32)
    v[0] = 1.0
    return v


def _make_field_state() -> FieldState:
    """Build a minimal valid field state for tests."""
    F = _zero_versor()
    return FieldState(F=F)


def _make_result(
    *,
    intent_tag: IntentTag,
    vault_hits: int,
    teaching_proposal: PackMutationProposal | None,
    trace_hash: str = "deadbeef",
) -> CognitiveTurnResult:
    proposition = Proposition(
        subject="x",
        predicate="is",
        object_="y",
        surface="x is y",
        frame_id="test",
        subject_versor=_zero_versor(),
        predicate_versor=_zero_versor(),
    )
    articulation = ArticulationPlan(
        subject="x",
        predicate="is",
        object="y",
        surface="x is y",
        output_language="en",
        frame_id="test",
    )
    fs = _make_field_state()
    intent = (
        DialogueIntent(tag=intent_tag, subject="x")
        if intent_tag is not None
        else None
    )
    return CognitiveTurnResult(
        input_text="what is x?",
        input_tokens=("what", "is", "x"),
        filtered_tokens=("x",),
        field_state_before=None,
        field_state_after=fs,
        proposition=proposition,
        articulation=articulation,
        surface="x is y",
        walk_surface="x is y",
        articulation_surface="x is y",
        dialogue_role="elaborate",
        identity_score=None,
        vault_hits=vault_hits,
        intent=intent,
        proposition_graph=None,
        articulation_target=None,
        teaching_candidate=None,
        reviewed_teaching_example=None,
        pack_mutation_proposal=teaching_proposal,
        versor_condition=0.0,
        trace_hash=trace_hash,
    )


def test_pack_only_source() -> None:
    result = _make_result(
        intent_tag=IntentTag.DEFINITION,
        vault_hits=0,
        teaching_proposal=None,
    )
    prov = compute_provenance(result)

    assert prov.is_empty is False
    assert prov.kinds() == ("pack",)
    assert prov.refs("pack") == ("definition",)
    assert prov.refs("vault") == ()
    assert prov.refs("teaching") == ()


def test_pack_plus_vault() -> None:
    result = _make_result(
        intent_tag=IntentTag.RECALL,
        vault_hits=3,
        teaching_proposal=None,
    )
    prov = compute_provenance(result)

    assert prov.kinds() == ("pack", "vault")
    assert prov.refs("pack") == ("recall",)
    assert prov.refs("vault") == ("vault_hit_0", "vault_hit_1", "vault_hit_2")


def test_pack_plus_teaching() -> None:
    proposal = PackMutationProposal(
        proposal_id="abc123",
        candidate_id="cand1",
        subject="x",
        correction_text="x is z",
        prior_surface="x is y",
        source=ProposalSource(
            kind="operator", source_id="", emitted_at_revision="test"
        ),
    )
    result = _make_result(
        intent_tag=IntentTag.CORRECTION,
        vault_hits=0,
        teaching_proposal=proposal,
    )
    prov = compute_provenance(result)

    assert prov.kinds() == ("pack", "teaching")
    assert prov.refs("teaching") == ("abc123",)


def test_unknown_intent_no_vault_no_teaching_is_empty() -> None:
    result = _make_result(
        intent_tag=IntentTag.UNKNOWN,
        vault_hits=0,
        teaching_proposal=None,
    )
    prov = compute_provenance(result)

    assert prov.is_empty is True
    assert prov.kinds() == ()


def test_provenance_has_kind_helper() -> None:
    result = _make_result(
        intent_tag=IntentTag.DEFINITION,
        vault_hits=1,
        teaching_proposal=None,
    )
    prov = compute_provenance(result)

    assert prov.has_kind("pack") is True
    assert prov.has_kind("vault") is True
    assert prov.has_kind("teaching") is False


def test_trace_hash_preserved() -> None:
    result = _make_result(
        intent_tag=IntentTag.DEFINITION,
        vault_hits=0,
        teaching_proposal=None,
        trace_hash="cafebabe",
    )
    prov = compute_provenance(result)
    assert prov.turn_trace_hash == "cafebabe"
