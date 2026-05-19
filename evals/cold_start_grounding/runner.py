"""Cold-start grounding eval lane runner.

Measures cold-start routing of conversational prompts to the correct
grounding source.  Each case is fed through a **fresh** ``ChatRuntime()``
so the metric reflects routing, not multi-turn accumulation.

Framework contract: exposes ``run_lane(cases, **kwargs) -> LaneReport``
where ``LaneReport.metrics`` is a dict and ``LaneReport.case_details``
is a list of per-case dicts.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime
from generate.intent import classify_compound_intent, classify_intent


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    category: str
    prompt: str
    expected_intent: str
    actual_intent: str
    intent_match: bool
    expected_grounding_source: str
    actual_grounding_source: str
    grounding_match: bool
    expected_subject: str | None
    actual_subject: str
    subject_match: bool | None
    surface: str


@dataclass
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _run_case(case: dict[str, Any]) -> CaseResult:
    """Run a single case through a *fresh* ChatRuntime to measure
    cold-start routing.  Re-using a runtime across cases would
    contaminate vault state from earlier turns."""
    prompt = case["prompt"]
    expected_intent = case["expected_intent"]
    expected_grounding = case["expected_grounding_source"]
    expected_subject_raw = case.get("expected_subject")
    expected_subject = (
        expected_subject_raw.strip().lower()
        if isinstance(expected_subject_raw, str)
        else None
    )

    # Classify intent independently for the subject-match check —
    # avoids round-tripping through the runtime when the prompt
    # bypasses pack-grounding for an OOV/none case.
    compound = classify_compound_intent(prompt)
    classified = compound.primary if compound.is_compound() else classify_intent(prompt)
    actual_subject = (classified.subject or "").strip().lower()

    # Fresh runtime — cold-start invariant.
    runtime = ChatRuntime()
    response = runtime.chat(prompt)
    actual_grounding = (response.grounding_source or "none").lower()
    actual_intent_tag = classified.tag.value

    intent_match = actual_intent_tag == expected_intent
    grounding_match = actual_grounding == expected_grounding
    subject_match: bool | None
    if expected_subject is not None:
        subject_match = actual_subject == expected_subject
    else:
        subject_match = None

    return CaseResult(
        case_id=case["id"],
        category=case.get("category", "uncategorised"),
        prompt=prompt,
        expected_intent=expected_intent,
        actual_intent=actual_intent_tag,
        intent_match=intent_match,
        expected_grounding_source=expected_grounding,
        actual_grounding_source=actual_grounding,
        grounding_match=grounding_match,
        expected_subject=expected_subject,
        actual_subject=actual_subject,
        subject_match=subject_match,
        surface=response.surface,
    )


def run_lane(cases: list[dict[str, Any]], config: Any = None) -> LaneReport:  # noqa: ARG001 — config param required by framework contract
    """Run the cold-start grounding lane over *cases*.

    Returns a ``LaneReport`` with three rate metrics plus a per-category
    breakdown so regressions can be attributed to a specific
    intent-classification or grounding pattern.
    """
    results: list[CaseResult] = [_run_case(c) for c in cases]
    total = len(results)
    if total == 0:
        return LaneReport(metrics={}, case_details=[])

    intent_correct = sum(1 for r in results if r.intent_match)
    grounding_correct = sum(1 for r in results if r.grounding_match)
    subject_total = sum(1 for r in results if r.subject_match is not None)
    subject_correct = sum(
        1 for r in results if r.subject_match is True
    )

    grounding_distribution = Counter(r.actual_grounding_source for r in results)
    expected_distribution = Counter(r.expected_grounding_source for r in results)

    per_category: dict[str, dict[str, int]] = {}
    for r in results:
        cat = per_category.setdefault(
            r.category,
            {"total": 0, "intent_correct": 0, "grounding_correct": 0},
        )
        cat["total"] += 1
        if r.intent_match:
            cat["intent_correct"] += 1
        if r.grounding_match:
            cat["grounding_correct"] += 1

    metrics: dict[str, Any] = {
        "cases": total,
        "intent_accuracy": round(intent_correct / total, 4),
        "grounding_accuracy": round(grounding_correct / total, 4),
        "subject_accuracy": (
            round(subject_correct / subject_total, 4) if subject_total else 1.0
        ),
        "subject_assertions": subject_total,
        "grounding_distribution_actual": dict(grounding_distribution),
        "grounding_distribution_expected": dict(expected_distribution),
        "per_category": per_category,
    }

    case_details = [
        {
            "case_id": r.case_id,
            "category": r.category,
            "prompt": r.prompt,
            "expected_intent": r.expected_intent,
            "actual_intent": r.actual_intent,
            "intent_match": r.intent_match,
            "expected_grounding_source": r.expected_grounding_source,
            "actual_grounding_source": r.actual_grounding_source,
            "grounding_match": r.grounding_match,
            "expected_subject": r.expected_subject,
            "actual_subject": r.actual_subject,
            "subject_match": r.subject_match,
            "surface": r.surface,
        }
        for r in results
    ]

    return LaneReport(metrics=metrics, case_details=case_details)


__all__ = ["run_lane", "LaneReport", "CaseResult"]
