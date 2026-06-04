"""Adapters from existing operator traces into shared reasoning evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from core.reasoning.evidence import OperatorEvidence
from generate.math_problem_graph import MathProblemGraph
from generate.math_solver import SolutionTrace
from generate.proof_chain import Entailment, EntailmentTrace


def evidence_from_entailment_trace(trace: EntailmentTrace) -> OperatorEvidence:
    """Convert propositional entailment trace evidence to the shared contract."""
    query_key = trace.query_key or ""
    check_keys = tuple(
        key for key in (
            trace.conjunction_key,
            trace.entailment_check_key,
            trace.refutation_check_key,
        )
        if key
    )
    if trace.outcome is Entailment.REFUSED:
        commitment_key = ""
    else:
        commitment_key = f"entailment:{trace.outcome.value}:{query_key}"
    structural_signature = _sha256_text(
        json.dumps(
            {
                "operator": "propositional_entailment",
                "premise_keys": list(trace.premise_keys),
                "check_keys": list(check_keys),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return OperatorEvidence(
        domain="mathematics_logic",
        operator="propositional_entailment",
        outcome=trace.outcome.value,
        reason=trace.reason,
        input_keys=(*trace.premise_keys, query_key),
        check_keys=check_keys,
        commitment_key=commitment_key,
        structural_signature=structural_signature,
        payload={"entailment_trace": trace.as_dict()},
    )


def evidence_from_math_solution(
    *,
    graph: MathProblemGraph,
    trace: SolutionTrace,
    reader_trace: tuple[str, ...] = (),
    operator: str = "math_problem_graph_solve_verify",
    reason: str = "solver_verifier_passed",
) -> OperatorEvidence:
    """Convert a verified MathProblemGraph solution to shared evidence."""
    graph_hash = hashlib.sha256(graph.canonical_bytes()).hexdigest()
    trace_hash = hashlib.sha256(trace.canonical_bytes()).hexdigest()
    operation_kinds = tuple(step.operation_kind for step in trace.steps)
    commitment_key = json.dumps(
        {
            "answer_entity": trace.answer_entity,
            "answer_unit": trace.answer_unit,
            "answer_value": trace.answer_value,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    structural_signature = _sha256_text(
        json.dumps(
            {
                "graph_hash": graph_hash,
                "operation_kinds": list(operation_kinds),
                "operator": operator,
                "pack_id": trace.pack_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return OperatorEvidence(
        domain="mathematics_logic",
        operator=operator,
        outcome="verified",
        reason=reason,
        input_keys=(graph_hash,),
        check_keys=(trace_hash, trace.graph_canonical_hash),
        commitment_key=commitment_key,
        structural_signature=structural_signature,
        payload={
            "answer_entity": trace.answer_entity,
            "answer_unit": trace.answer_unit,
            "answer_value": trace.answer_value,
            "graph_hash": graph_hash,
            "operation_kinds": list(operation_kinds),
            "pack_id": trace.pack_id,
            "reader_trace": tuple(_reader_event(ev) for ev in reader_trace),
            "trace_hash": trace_hash,
        },
    )


def _reader_event(event: str) -> Any:
    try:
        return json.loads(event)
    except json.JSONDecodeError:
        return event


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
