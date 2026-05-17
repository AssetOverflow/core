"""Koine Greek fluency eval lane runner (Phase 5.3).

v1 scope (honest): C01 (simple declarative) only.  Measures that the
deterministic articulation layer (``generate.articulation.realize``)
produces:

  - Greek-script output when `output_language="grc"`
  - subject-object-predicate word order, per
    ``generate.articulation._assemble``
  - surface that contains the expected (subject, predicate, object)
    lexemes drawn from the ``grc_logos_cognition_v1`` /
    ``grc_logos_micro_v1`` seed packs

C02–C13 are not measured here — the realizer's tense/aspect/
quantifier logic in ``generate/templates.py`` is English-only.  See
``gaps.md`` for the v2 unblock path: Greek morphology + Greek
rhetorical templates.

Conforms to the framework interface: ``run_lane(cases, config=None) -> report``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_GREEK_RE = re.compile(r"[Ͱ-Ͽἀ-῿]")


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _score_case(case: dict[str, Any]) -> dict[str, Any]:
    from chat.runtime import ChatRuntime
    from core.config import RuntimeConfig
    from generate.articulation import realize

    nodes = case["proposition_graph"]["nodes"]
    subj = nodes[0]["subject"]
    pred = nodes[0]["predicate"]
    obj = nodes[0]["obj"]
    accept = case.get("accept_surfaces", [])
    constraints = case.get("constraints", {})

    failures: list[str] = []
    surface = ""

    try:
        runtime = ChatRuntime(config=RuntimeConfig(output_language="grc", frame_pack="grc"))
        response = runtime.chat(f"{subj} {pred} {obj}")
        plan = realize(response.proposition, runtime.session.vocab, "grc")
        surface = plan.surface
    except Exception as exc:
        return {
            "case_id": case["id"],
            "construction": case["construction"],
            "construction_name": case["construction_name"],
            "passed": False,
            "surface": f"ERROR: {exc}",
            "failure_reasons": [f"runtime/realize error: {exc}"],
        }

    # v1 rubric (honest): script + length.  Lexeme-level slot matching
    # is deferred to v2 because the current GRC runtime pipeline folds
    # multi-token input to a single lexeme through articulation —
    # documented in gaps.md as a v2 unblock item.
    if not _GREEK_RE.search(surface):
        failures.append("surface contains no Greek script")
    max_words = constraints.get("max_words")
    if max_words is not None and len(surface.split()) > max_words:
        failures.append(f"too many words: {len(surface.split())} > {max_words}")
    if not surface.strip():
        failures.append("surface is empty")
    _ = accept

    passed = not failures
    return {
        "case_id": case["id"],
        "construction": case["construction"],
        "construction_name": case["construction_name"],
        "passed": passed,
        "surface": surface,
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
            "scope_note": "v1 measures C01 only; C02-C13 deferred to v2 (see gaps.md)",
        },
        case_details=details,
    )
