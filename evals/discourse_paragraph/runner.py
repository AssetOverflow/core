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


_MIN_WORDS_PER_SENTENCE = 3


def _check_per_sentence_grammar(
    sentences: list[str],
    expected_steps: list[dict[str, Any]] | None,
) -> list[str]:
    """Per-sentence grammaticality rubric (v2).

    For each emitted sentence, verifies:
      - non-empty after strip
      - at least ``_MIN_WORDS_PER_SENTENCE`` whitespace tokens
      - starts with an uppercase alphabetic character (sentence-initial cap)
      - if expected_steps is supplied, the subject of the aligned step
        appears somewhere in the sentence (case-insensitive)

    Returns a list of failure strings; empty if every sentence passes.
    """
    failures: list[str] = []
    for idx, sent in enumerate(sentences):
        stripped = sent.strip()
        if not stripped:
            failures.append(f"sentence[{idx}] empty")
            continue
        words = stripped.split()
        if len(words) < _MIN_WORDS_PER_SENTENCE:
            failures.append(
                f"sentence[{idx}] too short ({len(words)} words): {stripped[:40]!r}"
            )
        first_alpha = next((c for c in stripped if c.isalpha()), None)
        if first_alpha is not None and not first_alpha.isupper():
            failures.append(
                f"sentence[{idx}] not capitalized: {stripped[:40]!r}"
            )
        if expected_steps is not None and idx < len(expected_steps):
            subj = expected_steps[idx].get("subject", "").lower()
            if subj and subj not in stripped.lower():
                failures.append(
                    f"sentence[{idx}] missing aligned subject {subj!r}: {stripped[:40]!r}"
                )
    return failures


def _score_runtime_roundtrip_case(case: dict[str, Any]) -> dict[str, Any]:
    """Score a runtime round-trip case: prime vault, ask a question,
    check the runtime's articulation surface is well-formed and
    replay-deterministic.

    Builds two fresh ``ChatRuntime`` instances, primes each with the
    same sequence, and runs the same question — both surfaces must
    match byte-identically.

    This is a weaker structural claim than the realizer-direct
    cases: the runtime/planner typically produces a single sentence
    per turn, so we do not assert paragraph length here.  Multi-
    sentence-from-runtime is a v3 gap (requires planner extension).
    """
    from chat.runtime import ChatRuntime

    priming: list[str] = list(case.get("priming", []))
    question: str = case["question"]

    failures: list[str] = []

    def run_once() -> tuple[str, int]:
        rt = ChatRuntime()
        for p in priming:
            rt.chat(p)
        resp = rt.chat(question)
        surface = resp.articulation_surface or resp.surface or ""
        return surface, int(getattr(resp, "vault_hits", 0))

    surface_1, hits_1 = run_once()
    surface_2, _ = run_once()
    surface = surface_1.strip()

    if not surface:
        failures.append("empty runtime surface")
    min_hits = int(case.get("min_vault_hits", 1))
    if hits_1 < min_hits:
        failures.append(f"vault_hits {hits_1} < min {min_hits} (gate likely fired)")
    if surface_1 != surface_2:
        failures.append(
            f"runtime replay non-deterministic: {surface_1!r} != {surface_2!r}"
        )

    # Sentence-initial capitalization on the runtime surface too.
    if surface:
        first_alpha = next((c for c in surface if c.isalpha()), None)
        if first_alpha is not None and not first_alpha.isupper():
            failures.append(f"runtime surface not capitalized: {surface[:40]!r}")

    must_contain = case.get("must_contain", [])
    for token in must_contain:
        if token.lower() not in surface.lower():
            failures.append(f"missing required token {token!r} in {surface[:60]!r}")

    sent_count = _sentence_count(surface)

    return {
        "id": case["id"],
        "topic": case.get("topic", "runtime_roundtrip"),
        "passed": not failures,
        "surface": surface,
        "sentence_count": sent_count,
        "subject_coverage": 1.0 if not failures else 0.0,
        "discourse_markers_found": [],
        "replay_match": surface_1 == surface_2,
        "per_sentence_failures": [],
        "vault_hits": hits_1,
        "failure_reasons": failures,
    }


def _score_case(case: dict[str, Any]) -> dict[str, Any]:
    if case.get("mode") == "runtime_roundtrip":
        return _score_runtime_roundtrip_case(case)
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

    per_sentence_failures: list[str] = []
    if case.get("require_per_sentence_grammar"):
        # v2: align emitted sentences to the case steps (one sentence per
        # step in non-folded cases) and run the per-sentence rubric.
        expected_steps_aligned: list[dict[str, Any]] | None = (
            case.get("steps") if case.get("align_steps_to_sentences") else None
        )
        per_sentence_failures = _check_per_sentence_grammar(
            sentences, expected_steps_aligned
        )
        if per_sentence_failures:
            failures.extend(per_sentence_failures)

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
        "per_sentence_failures": per_sentence_failures,
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
            "per_sentence_grammar_pass_rate": round(
                sum(
                    1
                    for d in details
                    if not d.get("per_sentence_failures")
                )
                / max(1, total),
                4,
            ),
        },
        case_details=details,
    )
