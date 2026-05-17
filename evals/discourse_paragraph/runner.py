"""discourse_paragraph eval lane runner.

Exercises paragraph-scale realization: given a multi-step
ArticulationTarget, the deterministic realizer should produce a
multi-sentence surface with discourse markers (next, furthermore,
in contrast) and full subject coverage.

Bypasses ChatRuntime grounding so the paragraph claim is isolated
to the realizer.  Runtime round-tripping is named as a v2 gap.

Conforms to the framework interface: run_lane(cases, config=None) -> report.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from generate.graph_planner import (
    ArticulationStep,
    ArticulationTarget,
    GraphEdge,
    GraphNode,
    PropositionGraph,
    Relation,
    RhetoricalMove,
)
from generate.intent import IntentTag
from generate.realizer import realize_target


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


_SENTENCE_SPLIT_RE = re.compile(r"[.!?]\s+|[.!?]$")


def _sentence_count(surface: str) -> int:
    if not surface.strip():
        return 0
    parts = [p for p in _SENTENCE_SPLIT_RE.split(surface) if p.strip()]
    return len(parts)


def _build_target_from_case(case: dict[str, Any]) -> tuple[ArticulationTarget, PropositionGraph]:
    nodes_data = case["graph"]["nodes"]
    edges_data = case["graph"].get("edges", [])
    nodes = tuple(
        GraphNode(
            node_id=nd["node_id"],
            subject=nd["subject"],
            predicate=nd["predicate"],
            obj=nd["obj"],
            source_intent=IntentTag.UNKNOWN,
        )
        for nd in nodes_data
    )
    edges = tuple(
        GraphEdge(
            source=e["source"],
            target=e["target"],
            relation=Relation[e.get("relation", "SEQUENCE").upper()],
        )
        for e in edges_data
    )
    graph = PropositionGraph(nodes=nodes, edges=edges)
    by_id = {n.node_id: n for n in nodes}
    steps = tuple(
        ArticulationStep(
            node_id=s["node_id"],
            subject=by_id[s["node_id"]].subject,
            predicate=by_id[s["node_id"]].predicate,
            move=RhetoricalMove[s["move"].upper()],
        )
        for s in case["steps"]
    )
    target = ArticulationTarget(steps=steps, source_intent=IntentTag.UNKNOWN)
    return target, graph


def _score_case(case: dict[str, Any]) -> dict[str, Any]:
    target, graph = _build_target_from_case(case)
    plan_1 = realize_target(target, graph)
    plan_2 = realize_target(target, graph)
    surface = plan_1.surface
    surface_lower = surface.lower()

    failures: list[str] = []
    sent_count = _sentence_count(surface)
    min_sentences = int(case["min_sentences"])
    max_sentences = int(case.get("max_sentences", min_sentences + 2))
    if sent_count < min_sentences:
        failures.append(f"sentence_count {sent_count} < min {min_sentences}")
    if sent_count > max_sentences:
        failures.append(f"sentence_count {sent_count} > max {max_sentences}")

    must_contain = case.get("must_contain_subjects", [])
    present = [s for s in must_contain if s.lower() in surface_lower]
    coverage = len(present) / max(1, len(must_contain))
    if coverage < 0.75:
        missing = [s for s in must_contain if s.lower() not in surface_lower]
        failures.append(f"subject_coverage {coverage:.2f} < 0.75; missing={missing}")

    expected_markers = case.get("discourse_markers", [])
    if expected_markers:
        found = [m for m in expected_markers if m.lower() in surface_lower]
        if not found:
            failures.append(
                f"no discourse marker present; expected one of {expected_markers}"
            )
    else:
        found = []

    # Sentence-initial capitalization (G4): every sentence-leading
    # alphabetic character must be uppercase.  This is the gate that
    # turned "wisdom grounds knowledge." into "Wisdom grounds
    # knowledge." — addresses the open scope item.
    sentences = [p.strip() for p in _SENTENCE_SPLIT_RE.split(surface) if p.strip()]
    badly_cased: list[str] = []
    for sent in sentences:
        for ch in sent:
            if ch.isalpha():
                if not ch.isupper():
                    badly_cased.append(sent[:30])
                break
    if badly_cased:
        failures.append(
            f"sentence-initial capitalization missing in {len(badly_cased)} "
            f"sentence(s): {badly_cased}"
        )

    replay_match = plan_1.surface == plan_2.surface
    if not replay_match:
        failures.append("replay determinism broken: surfaces differ")

    passed = not failures
    return {
        "id": case["id"],
        "topic": case.get("topic", ""),
        "passed": passed,
        "surface": surface,
        "sentence_count": sent_count,
        "subject_coverage": coverage,
        "discourse_markers_found": found,
        "replay_match": replay_match,
        "failure_reasons": failures,
    }


def run_lane(cases: list[dict[str, Any]], *, config: Any = None) -> LaneReport:
    details = [_score_case(c) for c in cases]
    total = len(details)
    passed = sum(1 for d in details if d["passed"])
    return LaneReport(
        metrics={
            "total": total,
            "passed": passed,
            "accuracy": round(passed / total, 4) if total else 0.0,
            "mean_sentence_count": round(
                sum(d["sentence_count"] for d in details) / max(1, total), 3
            ),
            "mean_subject_coverage": round(
                sum(d["subject_coverage"] for d in details) / max(1, total), 4
            ),
            "replay_determinism_rate": round(
                sum(1 for d in details if d["replay_match"]) / max(1, total), 4
            ),
        },
        case_details=details,
    )
