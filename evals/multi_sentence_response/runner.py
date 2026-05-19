"""Multi-sentence response eval lane runner.

Measures whether ``ChatRuntime`` emits more than one sentence when
the prompt structurally calls for elaboration.  Strips the trailing
provenance tag (``pack-grounded (...).``) before counting sentences
so the metric reflects substantive content.

Framework contract: ``run_lane(cases, config=None) -> LaneReport``.

Case schema:
    {
      "id": "...",
      "category": "...",
      "prompt": "Tell me about truth.",
      "subject_lemma": "truth",
      "expects_connective": true
    }
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime


_PROVENANCE_TAIL_RE = re.compile(
    r"\s*(pack-grounded|teaching-grounded)\s*\([^)]+\)\.?\s*$"
)

_CONNECTIVES = (
    "and", "because", "therefore", "which", "since", "also",
    "furthermore", "however", "consequently", "thus", "so", "while",
    "whereas", "moreover", "in turn",
)


def _strip_provenance(surface: str) -> str:
    return _PROVENANCE_TAIL_RE.sub("", surface).strip()


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _alpha_tokens(text: str) -> int:
    return len(re.findall(r"[A-Za-z]+", text))


def _has_connective(text: str) -> bool:
    low = text.lower()
    return any(re.search(rf"\b{re.escape(c)}\b", low) for c in _CONNECTIVES)


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    category: str
    prompt: str
    surface: str
    grounding_source: str
    sentence_count: int
    each_sentence_long_enough: bool
    connective_present: bool
    grounded: bool
    subject_named: bool
    expects_connective: bool


@dataclass
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _run_case(case: dict[str, Any]) -> CaseResult:
    rt = ChatRuntime()
    resp = rt.chat(case["prompt"])
    surface = resp.surface
    grounding = resp.grounding_source or "none"

    stripped = _strip_provenance(surface)
    sentences = _split_sentences(stripped)
    each_long = all(_alpha_tokens(s) >= 4 for s in sentences) if sentences else False

    subj = case.get("subject_lemma", "").lower()
    subj_named = (subj in surface.lower()) if subj else True

    return CaseResult(
        case_id=case["id"],
        category=case.get("category", "uncategorised"),
        prompt=case["prompt"],
        surface=surface,
        grounding_source=grounding,
        sentence_count=len(sentences),
        each_sentence_long_enough=each_long,
        connective_present=_has_connective(stripped),
        grounded=(grounding in {"pack", "teaching"}),
        subject_named=subj_named,
        expects_connective=bool(case.get("expects_connective", False)),
    )


def run_lane(cases: list[dict[str, Any]], config: Any = None) -> LaneReport:  # noqa: ARG001
    if not cases:
        return LaneReport(metrics={}, case_details=[])

    results = [_run_case(c) for c in cases]
    total = len(results)

    multi = sum(1 for r in results if r.sentence_count >= 2)
    non_frag = sum(1 for r in results if r.each_sentence_long_enough)
    grounded = sum(1 for r in results if r.grounded)
    named = sum(1 for r in results if r.subject_named)

    conn_expected = [r for r in results if r.expects_connective]
    conn_rate = (
        round(sum(1 for r in conn_expected if r.connective_present) / len(conn_expected), 4)
        if conn_expected else 1.0
    )

    metrics: dict[str, Any] = {
        "cases": total,
        "multi_sentence_rate":     round(multi / total, 4) if total else 0.0,
        "non_fragment_rate":       round(non_frag / total, 4) if total else 0.0,
        "grounded_rate":           round(grounded / total, 4) if total else 0.0,
        "subject_named_rate":      round(named / total, 4) if total else 0.0,
        "connective_present_rate": conn_rate,
    }

    case_details = [
        {
            "case_id": r.case_id,
            "category": r.category,
            "prompt": r.prompt,
            "surface": r.surface,
            "grounding_source": r.grounding_source,
            "sentence_count": r.sentence_count,
            "each_sentence_long_enough": r.each_sentence_long_enough,
            "connective_present": r.connective_present,
            "grounded": r.grounded,
            "subject_named": r.subject_named,
            "expects_connective": r.expects_connective,
        }
        for r in results
    ]

    return LaneReport(metrics=metrics, case_details=case_details)
