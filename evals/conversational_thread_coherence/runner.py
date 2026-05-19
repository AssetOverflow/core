"""Conversational thread coherence eval lane runner.

Measures whether ``ChatRuntime`` maintains coherent grounding and
topic continuity across an 8-12 turn thread.  Predicates are
deterministic and lexical — no LLM judge, no embedding similarity.

Framework contract: ``run_lane(cases, config=None) -> LaneReport``.

Case schema (``cases.jsonl`` line):

    {
      "id": "...",
      "category": "...",
      "turns": [
        {
          "prompt": "...",
          "subject_lemma": "truth",            # optional — for topic-anchor check
          "expects_grounded": true,            # default true
          "anaphora_anchor_to": "truth",       # optional — prior subject expected to appear
          "is_replay_of_prompt_at_turn": 0     # optional — drift check
        }
      ]
    }
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime


_PLACEHOLDER_MARKERS = ("...", "<pending>", "<prior>", "<empty>")

_FINITE_VERB_RE = re.compile(
    r"\b(is|are|was|were|has|have|had|does|do|did|will|would|can|could|"
    r"should|might|may|must|shall|been|being|[a-z]+(?:es|ed|ing)s?)\b",
    re.IGNORECASE,
)


def _check_no_placeholder(surface: str) -> bool:
    return not any(m in surface for m in _PLACEHOLDER_MARKERS)


def _check_not_fragment(surface: str) -> bool:
    tokens = [t for t in re.findall(r"[A-Za-z]+", surface)]
    if len(tokens) < 4:
        return False
    return bool(_FINITE_VERB_RE.search(surface))


def _check_length_adequate(surface: str) -> bool:
    return len(surface.strip()) >= 20


def _check_is_grounded(grounding_source: str, expects: bool) -> bool:
    if not expects:
        return True
    return grounding_source in {"pack", "teaching", "vault", "oov", "partial"}


@dataclass(frozen=True, slots=True)
class TurnResult:
    turn_index: int
    prompt: str
    surface: str
    grounding_source: str
    no_placeholder: bool
    not_walk_fragment: bool
    length_adequate: bool
    is_grounded: bool
    topic_anchor_satisfied: bool | None  # None when not applicable


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    category: str
    turn_results: tuple[TurnResult, ...]
    no_topic_drift: bool


@dataclass
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _run_case(case: dict[str, Any]) -> CaseResult:
    rt = ChatRuntime()
    turns: list[TurnResult] = []
    grounding_by_prompt: dict[str, list[str]] = {}

    for idx, turn in enumerate(case["turns"]):
        prompt = turn["prompt"]
        expects_grounded = bool(turn.get("expects_grounded", True))
        anaphora_anchor = turn.get("anaphora_anchor_to")

        resp = rt.chat(prompt)
        surface = resp.surface
        grounding = resp.grounding_source or "none"

        anchor_ok: bool | None = None
        if anaphora_anchor:
            anchor_ok = anaphora_anchor.lower() in surface.lower()

        turns.append(TurnResult(
            turn_index=idx,
            prompt=prompt,
            surface=surface,
            grounding_source=grounding,
            no_placeholder=_check_no_placeholder(surface),
            not_walk_fragment=_check_not_fragment(surface),
            length_adequate=_check_length_adequate(surface),
            is_grounded=_check_is_grounded(grounding, expects_grounded),
            topic_anchor_satisfied=anchor_ok,
        ))
        grounding_by_prompt.setdefault(prompt, []).append(grounding)

    # No topic drift: any prompt that repeats must produce the SAME
    # grounding tier on every firing (pack/teaching once → pack/teaching
    # always).  Drops to `none` after a successful grounding indicate
    # state corruption.
    no_drift = True
    for srcs in grounding_by_prompt.values():
        if len(srcs) <= 1:
            continue
        strong = {"pack", "teaching"}
        if any(s in strong for s in srcs) and any(s == "none" for s in srcs):
            no_drift = False
            break

    return CaseResult(
        case_id=case["id"],
        category=case.get("category", "uncategorised"),
        turn_results=tuple(turns),
        no_topic_drift=no_drift,
    )


def run_lane(cases: list[dict[str, Any]], config: Any = None) -> LaneReport:  # noqa: ARG001
    if not cases:
        return LaneReport(metrics={}, case_details=[])

    results = [_run_case(c) for c in cases]
    total_turns = sum(len(r.turn_results) for r in results)

    def _rate(pred: str) -> float:
        passing = sum(1 for r in results for t in r.turn_results if getattr(t, pred))
        return round(passing / total_turns, 4) if total_turns else 1.0

    anchor_turns = [t for r in results for t in r.turn_results
                    if t.topic_anchor_satisfied is not None]
    anchor_rate = (
        round(sum(1 for t in anchor_turns if t.topic_anchor_satisfied) / len(anchor_turns), 4)
        if anchor_turns else 1.0
    )

    metrics: dict[str, Any] = {
        "cases": len(results),
        "total_turns": total_turns,
        "no_placeholder_rate": _rate("no_placeholder"),
        "not_walk_fragment_rate": _rate("not_walk_fragment"),
        "length_adequate_rate": _rate("length_adequate"),
        "is_grounded_rate": _rate("is_grounded"),
        "topic_anchor_rate": anchor_rate,
        "no_topic_drift_rate": (
            round(sum(1 for r in results if r.no_topic_drift) / len(results), 4)
            if results else 1.0
        ),
    }

    case_details = [
        {
            "case_id": r.case_id,
            "category": r.category,
            "no_topic_drift": r.no_topic_drift,
            "turns": [
                {
                    "turn_index": t.turn_index,
                    "prompt": t.prompt,
                    "surface": t.surface,
                    "grounding_source": t.grounding_source,
                    "no_placeholder": t.no_placeholder,
                    "not_walk_fragment": t.not_walk_fragment,
                    "length_adequate": t.length_adequate,
                    "is_grounded": t.is_grounded,
                    "topic_anchor_satisfied": t.topic_anchor_satisfied,
                }
                for t in r.turn_results
            ],
        }
        for r in results
    ]

    return LaneReport(metrics=metrics, case_details=case_details)
