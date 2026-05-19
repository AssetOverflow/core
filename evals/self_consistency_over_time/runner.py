"""Self-consistency over time eval lane runner.

Same factual prompt is asked at multiple turn indices with unrelated
turns interleaved.  Measures whether accumulated state causes the
answer to drift.

Framework contract: ``run_lane(cases, config=None) -> LaneReport``.

Case schema:
    {
      "id": "...",
      "category": "...",
      "probe_prompt": "What is truth?",
      "expected_key_terms": ["truth", "evidence"],
      "probe_at_turns": [0, 4, 9],
      "filler_prompts": ["What is light?", "Define memory.", ...]
    }

The lane interleaves probe_prompt at the requested turn indices and
fills remaining indices with filler_prompts (cycled if needed).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime


def _alpha_tokens(text: str) -> int:
    return len(re.findall(r"[A-Za-z]+", text))


@dataclass(frozen=True, slots=True)
class ProbeResult:
    turn_index: int
    surface: str
    grounding_source: str


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    category: str
    probe_prompt: str
    probes: tuple[ProbeResult, ...]
    byte_identical: bool
    key_terms_stable: bool
    grounding_source_stable: bool
    no_walk_fragment: bool


@dataclass
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _run_case(case: dict[str, Any]) -> CaseResult:
    rt = ChatRuntime()
    probe_prompt: str = case["probe_prompt"]
    probe_turns = sorted(int(i) for i in case["probe_at_turns"])
    fillers: list[str] = list(case.get("filler_prompts", []))
    key_terms = [t.lower() for t in case.get("expected_key_terms", [])]
    max_turn = max(probe_turns)
    probes: list[ProbeResult] = []
    filler_idx = 0

    for turn in range(max_turn + 1):
        if turn in probe_turns:
            resp = rt.chat(probe_prompt)
            probes.append(ProbeResult(
                turn_index=turn,
                surface=resp.surface,
                grounding_source=resp.grounding_source or "none",
            ))
        else:
            prompt = fillers[filler_idx % len(fillers)] if fillers else "What is light?"
            filler_idx += 1
            rt.chat(prompt)

    surfaces = [p.surface for p in probes]
    groundings = [p.grounding_source for p in probes]

    byte_id = len(set(surfaces)) == 1
    grounding_stable = len(set(groundings)) == 1
    terms_stable = all(
        all(term in s.lower() for term in key_terms) for s in surfaces
    ) if key_terms else True
    no_fragment = all(_alpha_tokens(s) >= 4 for s in surfaces)

    return CaseResult(
        case_id=case["id"],
        category=case.get("category", "uncategorised"),
        probe_prompt=probe_prompt,
        probes=tuple(probes),
        byte_identical=byte_id,
        key_terms_stable=terms_stable,
        grounding_source_stable=grounding_stable,
        no_walk_fragment=no_fragment,
    )


def run_lane(cases: list[dict[str, Any]], config: Any = None) -> LaneReport:  # noqa: ARG001
    if not cases:
        return LaneReport(metrics={}, case_details=[])

    results = [_run_case(c) for c in cases]
    total = len(results)

    metrics: dict[str, Any] = {
        "cases": total,
        "byte_identical_rate":    round(sum(1 for r in results if r.byte_identical) / total, 4),
        "key_terms_stable_rate":  round(sum(1 for r in results if r.key_terms_stable) / total, 4),
        "grounding_source_stable_rate": round(
            sum(1 for r in results if r.grounding_source_stable) / total, 4
        ),
        "no_walk_fragment_rate":  round(sum(1 for r in results if r.no_walk_fragment) / total, 4),
    }

    case_details = [
        {
            "case_id": r.case_id,
            "category": r.category,
            "probe_prompt": r.probe_prompt,
            "byte_identical": r.byte_identical,
            "key_terms_stable": r.key_terms_stable,
            "grounding_source_stable": r.grounding_source_stable,
            "no_walk_fragment": r.no_walk_fragment,
            "probes": [
                {
                    "turn_index": p.turn_index,
                    "surface": p.surface,
                    "grounding_source": p.grounding_source,
                }
                for p in r.probes
            ],
        }
        for r in results
    ]

    return LaneReport(metrics=metrics, case_details=case_details)
