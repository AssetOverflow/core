"""Zero-code domain acquisition eval lane runner.

Scores the deterministic realizer on novel-domain prompts authored entirely
through pack data (vocabulary, relations, axioms, teaching examples) with
no Python edits.  Each case is a PropositionGraph prompt from a surprise
domain (kinship, calendar, color).

Any Python edit required to pass is logged as an "engineering gap" —
an empty gap log at v1 pass proves the extensibility contract.

Conforms to the framework interface: ``run_lane(cases, config=None) -> report``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    domain: str
    passed: bool
    surface: str
    failure_reasons: tuple[str, ...]


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _check_word_order(order: list[str], surface_words: list[str]) -> bool:
    positions: list[int] = []
    for word in order:
        found = False
        start = positions[-1] + 1 if positions else 0
        for i in range(start, len(surface_words)):
            if surface_words[i].lower() == word.lower():
                positions.append(i)
                found = True
                break
        if not found:
            return False
    return True


def _realize_from_graph(case: dict[str, Any]) -> str:
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

    graph_data = case["proposition_graph"]
    nodes_data = graph_data["nodes"]
    edges_data = graph_data.get("edges", [])

    _RELATION_MAP = {
        "conjunction": Relation.CONJUNCTION,
        "disjunction": Relation.DISJUNCTION,
        "complement": Relation.COMPLEMENT,
        "relative": Relation.RELATIVE,
        "sequence": Relation.SEQUENCE,
        "cause": Relation.CAUSE,
        "contrast": Relation.CONTRAST,
        "elaboration": Relation.ELABORATION,
        "correction": Relation.CORRECTION,
    }

    nodes = []
    for nd in nodes_data:
        nodes.append(GraphNode(
            node_id=nd["node_id"],
            subject=nd["subject"],
            predicate=nd["predicate"],
            obj=nd["obj"],
            source_intent=IntentTag.UNKNOWN,
        ))

    edges = []
    for e in edges_data:
        rel_str = e.get("relation", "sequence")
        edges.append(GraphEdge(
            source=e["source"],
            target=e["target"],
            relation=_RELATION_MAP.get(rel_str, Relation.SEQUENCE),
        ))

    graph = PropositionGraph(nodes=tuple(nodes), edges=tuple(edges))

    node_features = {nd["node_id"]: nd for nd in nodes_data}
    steps = []
    for node in nodes:
        nd = node_features[node.node_id]
        steps.append(ArticulationStep(
            node_id=node.node_id,
            subject=node.subject,
            predicate=node.predicate,
            move=RhetoricalMove.ASSERT,
            negated=nd.get("negated", False),
            quantifier=nd.get("quantifier"),
            tense=nd.get("tense"),
            aspect=nd.get("aspect"),
        ))

    target = ArticulationTarget(steps=tuple(steps), source_intent=IntentTag.UNKNOWN)
    plan = realize_target(target, graph)
    return plan.surface.rstrip(".")


def _extract_domain(case: dict[str, Any]) -> str:
    case_id = case.get("id", "")
    if case_id.startswith("kin_"):
        return "kinship"
    if case_id.startswith("cal_"):
        return "calendar"
    if case_id.startswith("col_"):
        return "color"
    return "unknown"


def _score_case(case: dict[str, Any]) -> CaseResult:
    domain = _extract_domain(case)

    try:
        surface = _realize_from_graph(case)
    except Exception as exc:
        return CaseResult(
            case_id=case["id"],
            domain=domain,
            passed=False,
            surface=f"ERROR: {exc}",
            failure_reasons=(f"realizer error: {exc}",),
        )

    accept = case.get("accept_surfaces", [])
    constraints = case.get("constraints", {})
    failures: list[str] = []

    surface_lower = surface.lower().strip()
    exact_match = any(s.lower().strip() == surface_lower for s in accept)

    if not exact_match and constraints:
        surface_words = surface_lower.split()

        for word in constraints.get("must_contain", []):
            if word.lower() not in surface_lower:
                failures.append(f"missing required word: {word}")

        word_order = constraints.get("word_order", [])
        if word_order and not _check_word_order(word_order, surface_words):
            failures.append(f"word order violated: expected {word_order}")

        max_words = constraints.get("max_words")
        if max_words is not None and len(surface_words) > max_words:
            failures.append(f"too many words: {len(surface_words)} > {max_words}")

    reject = case.get("reject_surfaces", [])
    if any(s.lower().strip() == surface_lower for s in reject):
        failures.append("surface matched a reject pattern")

    passed = exact_match or (not failures and bool(constraints))

    return CaseResult(
        case_id=case["id"],
        domain=domain,
        passed=passed,
        surface=surface,
        failure_reasons=tuple(failures),
    )


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: Any = None,
) -> LaneReport:
    total = 0
    passed = 0
    by_domain: dict[str, dict[str, int]] = {}
    case_details: list[dict[str, Any]] = []

    for case in cases:
        cr = _score_case(case)
        total += 1
        if cr.passed:
            passed += 1

        if cr.domain not in by_domain:
            by_domain[cr.domain] = {"total": 0, "passed": 0}
        by_domain[cr.domain]["total"] += 1
        if cr.passed:
            by_domain[cr.domain]["passed"] += 1

        case_details.append({
            "case_id": cr.case_id,
            "domain": cr.domain,
            "passed": cr.passed,
            "surface": cr.surface,
            "failure_reasons": list(cr.failure_reasons),
        })

    domain_scores = {
        k: round(v["passed"] / v["total"], 4) if v["total"] else 0.0
        for k, v in sorted(by_domain.items())
    }

    all_domains_pass = all(
        score >= 0.80 for score in domain_scores.values()
    )

    metrics = {
        "total": total,
        "passed": passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "by_domain": domain_scores,
        "all_domains_pass": all_domains_pass,
    }

    return LaneReport(metrics=metrics, case_details=case_details)
