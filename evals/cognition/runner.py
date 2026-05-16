"""Cognition eval lane runner.

Conforms to the framework interface: ``run_lane(cases, config=None) -> report``
where report has ``.metrics`` (dict) and ``.case_details`` (list[dict]).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from core.cognition.pipeline import CognitiveTurnPipeline
from generate.intent import IntentTag


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    category: str
    prompt: str
    intent_correct: bool
    terms_captured: tuple[str, ...]
    terms_expected: tuple[str, ...]
    surface_contains_pass: bool
    versor_closure: bool
    versor_condition: float
    trace_hash: str
    surface: str


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _run_case(case: dict[str, Any], pipeline: CognitiveTurnPipeline) -> CaseResult:
    prompt = case["prompt"]
    expected_intent = case["expected_intent"]
    expected_terms = case.get("expected_terms", [])
    expected_surface_contains = case.get("expected_surface_contains", [])

    result = pipeline.run(prompt, max_tokens=8)

    actual_intent = result.intent.tag if result.intent else IntentTag.UNKNOWN
    intent_correct = actual_intent.value == expected_intent

    surface_lower = result.surface.lower()
    terms_captured = tuple(
        t for t in expected_terms if t.lower() in surface_lower
    )
    surface_contains_pass = all(
        s.lower() in surface_lower for s in expected_surface_contains
    )

    versor_ok = result.versor_condition < 1e-6

    return CaseResult(
        case_id=case["id"],
        category=case.get("category", "unknown"),
        prompt=prompt,
        intent_correct=intent_correct,
        terms_captured=terms_captured,
        terms_expected=tuple(expected_terms),
        surface_contains_pass=surface_contains_pass,
        versor_closure=versor_ok,
        versor_condition=result.versor_condition,
        trace_hash=result.trace_hash,
        surface=result.surface,
    )


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
) -> LaneReport:
    """Run all cases through CognitiveTurnPipeline and return metrics + details."""
    total = 0
    intent_correct = 0
    terms_expected = 0
    terms_captured = 0
    surface_grounded = 0
    versor_closures = 0
    case_details: list[dict[str, Any]] = []

    for case in cases:
        runtime = ChatRuntime(config=config) if config else ChatRuntime()
        pipeline = CognitiveTurnPipeline(runtime)
        cr = _run_case(case, pipeline)

        total += 1
        if cr.intent_correct:
            intent_correct += 1
        terms_expected += len(cr.terms_expected)
        terms_captured += len(cr.terms_captured)
        if cr.surface_contains_pass:
            surface_grounded += 1
        if cr.versor_closure:
            versor_closures += 1

        case_details.append({
            "case_id": cr.case_id,
            "category": cr.category,
            "intent_correct": cr.intent_correct,
            "surface_contains_pass": cr.surface_contains_pass,
            "versor_closure": cr.versor_closure,
            "versor_condition": round(cr.versor_condition, 9),
            "trace_hash": cr.trace_hash,
            "surface": cr.surface,
        })

    metrics = {
        "total": total,
        "intent_accuracy": round(intent_correct / total, 4) if total else 0.0,
        "term_capture_rate": round(terms_captured / terms_expected, 4) if terms_expected else 1.0,
        "surface_groundedness": round(surface_grounded / total, 4) if total else 0.0,
        "versor_closure_rate": round(versor_closures / total, 4) if total else 0.0,
    }

    return LaneReport(metrics=metrics, case_details=case_details)
