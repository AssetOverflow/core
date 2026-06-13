"""Curated cognitive-pipeline persistence for Workbench trace views.

The runtime owns cognition; the workbench persists only the cheap, structured
stage evidence needed to audit a turn.  Raw field multivectors deliberately
stay out of this record.
"""

from __future__ import annotations

from typing import Any

from workbench.schemas import (
    CognitivePipelineEdge,
    CognitivePipelineRecord,
    CognitivePipelineStage,
)


REQUIRED_STAGE_IDS: tuple[str, ...] = (
    "input",
    "intent",
    "proposition_graph",
    "articulation_target",
    "realizer",
    "walk_telemetry",
    "trace_hash",
)

_PIPELINE_EDGES: tuple[CognitivePipelineEdge, ...] = (
    CognitivePipelineEdge(from_stage="input", to_stage="intent", label="classify"),
    CognitivePipelineEdge(
        from_stage="intent",
        to_stage="proposition_graph",
        label="plan graph",
    ),
    CognitivePipelineEdge(
        from_stage="proposition_graph",
        to_stage="articulation_target",
        label="topology",
    ),
    CognitivePipelineEdge(
        from_stage="articulation_target",
        to_stage="realizer",
        label="realize",
    ),
    CognitivePipelineEdge(
        from_stage="realizer",
        to_stage="walk_telemetry",
        label="retain evidence",
    ),
    CognitivePipelineEdge(
        from_stage="walk_telemetry",
        to_stage="trace_hash",
        label="seal",
    ),
)

_RAW_FIELD_KEYS = frozenset(
    {
        "F",
        "field_state_before",
        "field_state_after",
        "holonomy",
        "subject_versor",
        "predicate_versor",
        "object_versor",
    }
)


def cognitive_pipeline_record_from_result(result: Any) -> CognitivePipelineRecord:
    """Build and validate a compact, replayable pipeline record.

    A missing required stage raises ``ValueError`` before JSONL persistence, so
    the UI can never receive a partial record that still claims to be complete.
    """

    intent = _require(getattr(result, "intent", None), "intent", "intent")
    graph = _require(
        getattr(result, "proposition_graph", None),
        "proposition_graph",
        "proposition_graph",
    )
    target = _require(
        getattr(result, "articulation_target", None),
        "articulation_target",
        "articulation_target",
    )
    trace_hash = str(
        _require(getattr(result, "trace_hash", ""), "trace_hash", "trace_hash")
    )

    stages = [
        CognitivePipelineStage(
            stage_id="input",
            label="Input",
            status="recorded",
            summary=_summarize_tokens(result),
            detail={
                "input_text": str(getattr(result, "input_text", "")),
                "input_tokens": list(getattr(result, "input_tokens", ()) or ()),
                "filtered_tokens": list(getattr(result, "filtered_tokens", ()) or ()),
            },
        ),
        CognitivePipelineStage(
            stage_id="intent",
            label="Intent",
            status="recorded",
            summary=_intent_summary(intent),
            detail=_intent_detail(
                intent, getattr(result, "dropped_compound_clauses", ()) or ()
            ),
        ),
        CognitivePipelineStage(
            stage_id="proposition_graph",
            label="PropositionGraph",
            status="recorded",
            summary=f"{len(getattr(graph, 'nodes', ()) or ())} nodes / {len(getattr(graph, 'edges', ()) or ())} edges",
            detail=_graph_detail(graph),
        ),
        CognitivePipelineStage(
            stage_id="articulation_target",
            label="ArticulationTarget",
            status="recorded",
            summary=_target_summary(target),
            detail=_target_detail(target),
        ),
        CognitivePipelineStage(
            stage_id="realizer",
            label="Realizer",
            status="recorded",
            summary=_realizer_summary(result),
            detail=_realizer_detail(result),
        ),
        CognitivePipelineStage(
            stage_id="walk_telemetry",
            label="Walk Telemetry",
            status="recorded",
            summary=_walk_summary(result),
            detail=_walk_detail(result),
        ),
        CognitivePipelineStage(
            stage_id="trace_hash",
            label="Trace Hash",
            status="recorded",
            summary=trace_hash,
            detail={
                "trace_hash": trace_hash,
                "versor_condition": float(getattr(result, "versor_condition")),
                "field_digest": None,
            },
        ),
    ]
    record = CognitivePipelineRecord(
        schema_version="cognitive_pipeline_record_v1",
        status="recorded",
        missing_reason=None,
        trace_hash=trace_hash,
        versor_condition=float(getattr(result, "versor_condition")),
        field_digest=None,
        stages=stages,
        edges=list(_PIPELINE_EDGES),
    )
    validate_pipeline_record(record)
    return record


def pipeline_record_from_journal_entry(entry: Any) -> CognitivePipelineRecord:
    """Project a journal row into the first-class pipeline read model."""

    raw = getattr(entry, "pipeline_record", None)
    if raw is None:
        return missing_pipeline_record(
            trace_hash=getattr(entry, "trace_hash", None),
            reason="pipeline_record_not_persisted",
        )
    record = _coerce_pipeline_record(raw)
    if record.status == "recorded":
        validate_pipeline_record(record)
    return record


def missing_pipeline_record(
    *,
    trace_hash: str | None,
    reason: str,
) -> CognitivePipelineRecord:
    return CognitivePipelineRecord(
        schema_version="cognitive_pipeline_record_v1",
        status="missing_evidence",
        missing_reason=reason,
        trace_hash=trace_hash,
        versor_condition=None,
        field_digest=None,
        stages=[],
        edges=[],
    )


def validate_pipeline_record(record: CognitivePipelineRecord) -> None:
    stage_ids = [stage.stage_id for stage in record.stages]
    duplicates = sorted(
        {stage_id for stage_id in stage_ids if stage_ids.count(stage_id) > 1}
    )
    if duplicates:
        raise ValueError(
            "cognitive pipeline record has duplicate stages: " + ", ".join(duplicates)
        )

    present = set(stage_ids)
    missing = [stage_id for stage_id in REQUIRED_STAGE_IDS if stage_id not in present]
    if missing:
        raise ValueError(
            "cognitive pipeline record missing required stages: " + ", ".join(missing)
        )

    if record.status != "recorded":
        raise ValueError(
            f"cognitive pipeline record status is not recorded: {record.status}"
        )
    if not record.trace_hash:
        raise ValueError("cognitive pipeline record missing trace_hash")
    if record.versor_condition is None:
        raise ValueError("cognitive pipeline record missing versor_condition")

    for edge in record.edges:
        if edge.from_stage not in present:
            raise ValueError(
                f"cognitive pipeline edge source missing: {edge.from_stage}"
            )
        if edge.to_stage not in present:
            raise ValueError(f"cognitive pipeline edge target missing: {edge.to_stage}")
    for stage in record.stages:
        if stage.status != "recorded":
            raise ValueError(
                f"cognitive pipeline stage {stage.stage_id} is not recorded: {stage.status}"
            )
        _assert_no_raw_field_payload(stage.detail, path=stage.stage_id)


def _coerce_pipeline_record(raw: Any) -> CognitivePipelineRecord:
    if isinstance(raw, CognitivePipelineRecord):
        return raw
    if not isinstance(raw, dict):
        raise ValueError("pipeline_record must be an object")
    stages = [
        stage
        if isinstance(stage, CognitivePipelineStage)
        else CognitivePipelineStage(**stage)
        for stage in raw.get("stages", [])
    ]
    edges = [
        edge
        if isinstance(edge, CognitivePipelineEdge)
        else CognitivePipelineEdge(**edge)
        for edge in raw.get("edges", [])
    ]
    return CognitivePipelineRecord(
        schema_version=raw["schema_version"],
        status=raw["status"],
        missing_reason=raw.get("missing_reason"),
        trace_hash=raw.get("trace_hash"),
        versor_condition=raw.get("versor_condition"),
        field_digest=raw.get("field_digest"),
        stages=stages,
        edges=edges,
    )


def _assert_no_raw_field_payload(value: Any, *, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if key_text in _RAW_FIELD_KEYS:
                raise ValueError(
                    f"raw field payload is forbidden in pipeline record: {path}.{key_text}"
                )
            _assert_no_raw_field_payload(child, path=f"{path}.{key_text}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _assert_no_raw_field_payload(child, path=f"{path}[{index}]")


def _require(value: Any, stage_id: str, field_name: str) -> Any:
    if value is None or value == "":
        raise ValueError(f"cognitive pipeline stage {stage_id} missing {field_name}")
    return value


def _enum_value(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _intent_detail(intent: Any, dropped: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "tag": _enum_value(getattr(intent, "tag", "unknown")),
        "subject": str(getattr(intent, "subject", "")),
        "secondary_subject": getattr(intent, "secondary_subject", None),
        "object": getattr(intent, "object", None),
        "relation": getattr(intent, "relation", None),
        "negated": bool(getattr(intent, "negated", False)),
        "frame": getattr(intent, "frame", None),
        "dropped_compound_clauses": [_intent_detail(item, ()) for item in dropped],
    }


def _intent_summary(intent: Any) -> str:
    tag = _enum_value(getattr(intent, "tag", "unknown"))
    subject = str(getattr(intent, "subject", "") or "")
    return f"{tag}: {subject}" if subject else tag


def _graph_detail(graph: Any) -> dict[str, Any]:
    payload = graph.as_dict() if hasattr(graph, "as_dict") else {}
    return {
        "nodes": list(payload.get("nodes", ())),
        "edges": list(payload.get("edges", ())),
        "roots": list(graph.roots()) if hasattr(graph, "roots") else [],
        "topo_order": list(graph.topo_order()) if hasattr(graph, "topo_order") else [],
    }


def _target_detail(target: Any) -> dict[str, Any]:
    payload = target.as_dict() if hasattr(target, "as_dict") else {}
    return {
        "source_intent": payload.get("source_intent"),
        "steps": list(payload.get("steps", ())),
    }


def _target_summary(target: Any) -> str:
    steps = tuple(getattr(target, "steps", ()) or ())
    source_intent = _enum_value(getattr(target, "source_intent", "unknown"))
    return f"{len(steps)} steps / {source_intent}"


def _proposition_detail(proposition: Any) -> dict[str, Any]:
    return {
        "subject": str(getattr(proposition, "subject", "")),
        "predicate": str(getattr(proposition, "predicate", "")),
        "object": getattr(proposition, "object_", None),
        "surface": str(getattr(proposition, "surface", "")),
        "frame_id": str(getattr(proposition, "frame_id", "")),
        "relation_norm": float(getattr(proposition, "relation_norm", 0.0) or 0.0),
    }


def _realizer_detail(result: Any) -> dict[str, Any]:
    proposition = getattr(result, "proposition", None)
    return {
        "surface": str(getattr(result, "surface", "")),
        "articulation_surface": str(getattr(result, "articulation_surface", "")),
        "dialogue_role": str(getattr(result, "dialogue_role", "")),
        "proposition": _proposition_detail(proposition)
        if proposition is not None
        else None,
    }


def _realizer_summary(result: Any) -> str:
    surface = str(getattr(result, "surface", "") or "")
    return surface[:96] if surface else "surface empty"


def _walk_detail(result: Any) -> dict[str, Any]:
    admissibility_trace = getattr(result, "admissibility_trace", ()) or ()
    return {
        "walk_surface": str(getattr(result, "walk_surface", "") or ""),
        "operator_invocation": str(getattr(result, "operator_invocation", "") or ""),
        "vault_hits": int(getattr(result, "vault_hits", 0) or 0),
        "recall_energy_class": getattr(result, "recall_energy_class", None),
        "admissibility_trace_count": len(admissibility_trace),
        "admissibility_trace_hash": str(
            getattr(result, "admissibility_trace_hash", "") or ""
        ),
        "ratification_outcome": str(getattr(result, "ratification_outcome", "") or ""),
        "region_was_unconstrained": bool(
            getattr(result, "region_was_unconstrained", True)
        ),
        "refusal_reason": str(getattr(result, "refusal_reason", "") or ""),
        "dispatch_trace_present": getattr(result, "dispatch_trace", None) is not None,
        "teaching_candidate_present": getattr(result, "teaching_candidate", None)
        is not None,
        "reviewed_teaching_example_present": getattr(
            result, "reviewed_teaching_example", None
        )
        is not None,
        "pack_mutation_proposal_present": getattr(
            result, "pack_mutation_proposal", None
        )
        is not None,
    }


def _walk_summary(result: Any) -> str:
    operator = str(getattr(result, "operator_invocation", "") or "")
    if operator:
        return "operator invoked"
    vault_hits = int(getattr(result, "vault_hits", 0) or 0)
    return f"{vault_hits} vault hits"


def _summarize_tokens(result: Any) -> str:
    input_count = len(getattr(result, "input_tokens", ()) or ())
    filtered_count = len(getattr(result, "filtered_tokens", ()) or ())
    return f"{input_count} input tokens / {filtered_count} filtered"
