from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

import workbench.pipeline_record as pipeline_record
from generate.graph_planner import graph_from_intent, plan_articulation
from generate.intent import DialogueIntent, IntentTag


def _result() -> SimpleNamespace:
    intent = DialogueIntent(tag=IntentTag.DEFINITION, subject="truth")
    graph = graph_from_intent(intent)
    target = plan_articulation(graph)
    proposition = SimpleNamespace(
        subject="truth",
        predicate="is",
        object_="coherence",
        surface="Truth is coherence.",
        frame_id="definition",
        relation_norm=1.0,
    )
    return SimpleNamespace(
        input_text="What is truth?",
        input_tokens=("what", "is", "truth"),
        filtered_tokens=("truth",),
        intent=intent,
        proposition_graph=graph,
        articulation_target=target,
        proposition=proposition,
        surface="Truth is coherence.",
        articulation_surface="Truth is coherence.",
        walk_surface="truth -> coherence",
        dialogue_role="answer",
        vault_hits=1,
        recall_energy_class="stable",
        operator_invocation="",
        admissibility_trace=(),
        admissibility_trace_hash="",
        ratification_outcome="passthrough",
        region_was_unconstrained=True,
        refusal_reason="",
        dispatch_trace=None,
        teaching_candidate=None,
        reviewed_teaching_example=None,
        pack_mutation_proposal=None,
        dropped_compound_clauses=(),
        versor_condition=0.0,
        trace_hash="0" * 64,
    )


def test_pipeline_record_persists_curated_required_stages_only() -> None:
    record = pipeline_record.cognitive_pipeline_record_from_result(_result())

    assert record.status == "recorded"
    assert record.trace_hash == "0" * 64
    assert record.versor_condition == 0.0
    assert record.field_digest is None
    assert [stage.stage_id for stage in record.stages] == list(
        pipeline_record.REQUIRED_STAGE_IDS
    )
    assert record.stages[2].detail["nodes"][0]["subject"] == "truth"
    assert "field_state_after" not in str(record)
    assert "subject_versor" not in str(record)


def test_missing_pipeline_stage_data_fails_before_persistence() -> None:
    result = _result()
    result.proposition_graph = None

    with pytest.raises(ValueError, match="proposition_graph"):
        pipeline_record.cognitive_pipeline_record_from_result(result)


def test_future_required_stage_cannot_be_silently_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pipeline_record,
        "REQUIRED_STAGE_IDS",
        (*pipeline_record.REQUIRED_STAGE_IDS, "field_invariant"),
    )

    with pytest.raises(ValueError, match="field_invariant"):
        pipeline_record.cognitive_pipeline_record_from_result(_result())


def test_raw_field_payloads_are_rejected() -> None:
    record = pipeline_record.cognitive_pipeline_record_from_result(_result())
    bad_stage = replace(record.stages[0], detail={"F": [0.0] * 32})
    bad_record = replace(record, stages=[bad_stage, *record.stages[1:]])

    with pytest.raises(ValueError, match="raw field payload"):
        pipeline_record.validate_pipeline_record(bad_record)
