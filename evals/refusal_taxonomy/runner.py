"""ADR-0163 Phase A — refusal-taxonomy lane runner.

Read-only.  The lane categorises refused statements by *statement shape*
and emits a histogram.  It never mutates corpora, packs, language packs,
proposals, or engine state.

Per ADR-0163 §Constraint #4 and CLAUDE.md, the categorizer is rules-only:
no LLM call, no embedding, no learned classifier, no normalization beyond
lowercasing for substring matching.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from evals.refusal_taxonomy.shape_categories import (
    SHAPE_CATEGORY_ORDER,
    ShapeCategory,
    categorize,
)


@dataclass(frozen=True, slots=True)
class CategorizedCase:
    """One refused case decorated with its shape category."""

    case_id: str
    statement: str
    shape_category: ShapeCategory
    refusal_reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "statement": self.statement,
            "shape_category": self.shape_category.value,
            "refusal_reason": self.refusal_reason,
        }


@dataclass(frozen=True, slots=True)
class LaneReport:
    """Adapter shape expected by ``evals.framework.run_lane``."""

    metrics: dict[str, Any]
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _empty_histogram() -> dict[str, int]:
    return {category.value: 0 for category in SHAPE_CATEGORY_ORDER}


def _digest(records: list[dict[str, Any]]) -> str:
    payload = json.dumps(records, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def categorize_cases(cases: list[dict[str, Any]]) -> list[CategorizedCase]:
    """Pure helper — categorise a list of refused-case dicts."""

    out: list[CategorizedCase] = []
    for case in cases:
        if not isinstance(case, dict):
            raise TypeError("each case must be a dictionary")
        case_id = str(case.get("case_id", "")).strip()
        statement = case.get("statement", "")
        refusal_reason = str(case.get("refusal_reason", "")).strip()
        if not case_id:
            raise ValueError("case missing case_id")
        if not isinstance(statement, str) or not statement.strip():
            raise ValueError(f"case {case_id!r} has empty statement")
        out.append(
            CategorizedCase(
                case_id=case_id,
                statement=statement,
                shape_category=categorize(statement),
                refusal_reason=refusal_reason,
            )
        )
    return out


def build_report(cases: list[dict[str, Any]]) -> LaneReport:
    """Build a ``LaneReport`` from a refused-case dict list.

    The report is the lane's full deterministic output: the histogram over
    all shape categories, the categorized-rate (1 - uncategorized share),
    and per-case details.
    """

    categorized = categorize_cases(cases)
    histogram = _empty_histogram()
    for record in categorized:
        histogram[record.shape_category.value] += 1

    total = len(categorized)
    uncategorized = histogram[ShapeCategory.UNCATEGORIZED.value]
    categorized_rate = (
        (total - uncategorized) / total if total else 0.0
    )

    case_details = [record.as_dict() for record in categorized]
    metrics: dict[str, Any] = {
        "total": total,
        "by_category": histogram,
        "uncategorized": uncategorized,
        "categorized_rate": categorized_rate,
        "case_digest": _digest(case_details),
    }
    return LaneReport(metrics=metrics, case_details=case_details)


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: Any = None,
    workers: int | None = None,
) -> LaneReport:
    """Generic eval-framework entry point.

    ``config`` and ``workers`` are accepted for framework compatibility and
    ignored — the categorizer is pure and synchronous.
    """

    del config, workers
    if not isinstance(cases, list):
        raise TypeError("cases must be a list of dictionaries")
    return build_report(cases)


__all__ = [
    "CategorizedCase",
    "LaneReport",
    "build_report",
    "categorize_cases",
    "run_lane",
]
