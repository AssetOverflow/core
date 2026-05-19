"""Deterministic fluency eval lane runner.

Six structural predicates over the runtime's final surface — no
embedding, no LLM judge, no aesthetics.  Each predicate is a
testable bool.  This lane provides the substrate for the gloss
feature's lift target (the no_provenance_only and
no_dotted_inventory rates climb when glosses replace bare
disclosure surfaces).

Framework contract: ``run_lane(cases, config=None) -> LaneReport``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime


_PLACEHOLDER_MARKERS = ("...", "<pending>", "<prior>", "<empty>")

# Bare structured-disclosure shape — e.g.
#   "doubt — pack-grounded (en_core_meta_v1): meta.mental_state.uncertainty; meta.mental_state; cognition.epistemic. No session evidence yet."
# The shape is exactly: <lemma> — pack-grounded (<pack_id>): <semi-list>. <trailing-tag>.
_PROVENANCE_ONLY_RE = re.compile(
    r"^[a-z_][a-z_]* — pack-grounded \([a-z0-9_]+\): [^.]+\. "
    r"(No session evidence yet|No prior turn in this session to correct yet)\.\s*$"
)

# Three or more dotted-path tokens joined by `;` — the "domain inventory"
# shape that pre-gloss pack_grounded_surface emits.
_DOTTED_INVENTORY_RE = re.compile(
    r"[a-z_]+\.[a-z_]+(?:\.[a-z_]+)?\s*;\s*[a-z_]+\.[a-z_]+(?:\.[a-z_]+)?\s*;\s*"
    r"[a-z_]+\.[a-z_]+(?:\.[a-z_]+)?"
)

_FINITE_VERB_PATTERNS = (
    # third-person singular forms + auxiliaries + irregulars
    re.compile(r"\b(is|are|was|were|has|have|had|does|do|did|will|would|"
               r"can|could|should|might|may|must|shall|been|being)\b"),
    # regular -s present-third-singular
    re.compile(r"\b[a-z]+(es|s)\b"),
    # regular -ed simple past
    re.compile(r"\b[a-z]+ed\b"),
    # regular -ing present-participle
    re.compile(r"\b[a-z]+ing\b"),
)


def _check_no_placeholder(surface: str) -> bool:
    return not any(m in surface for m in _PLACEHOLDER_MARKERS)


def _check_no_provenance_only(surface: str) -> bool:
    return _PROVENANCE_ONLY_RE.match(surface.strip()) is None


def _check_complete_punctuation(surface: str) -> bool:
    stripped = surface.rstrip()
    if not stripped:
        return False
    return stripped[-1] in (".", "?", "!", ";")


def _check_finite_predicate(surface: str) -> bool:
    low = surface.lower()
    return any(p.search(low) for p in _FINITE_VERB_PATTERNS)


def _check_no_dotted_inventory(surface: str) -> bool:
    return _DOTTED_INVENTORY_RE.search(surface) is None


def _check_surface_provenance_match(surface: str, grounding: str) -> bool:
    """The surface's text and the declared grounding_source must
    agree.  Specifically: when grounding_source != 'pack' / 'teaching',
    the surface must NOT contain the 'pack-grounded' marker (would be
    a metadata/text disagreement)."""
    has_marker = "pack-grounded" in surface or "teaching-grounded" in surface
    if grounding in {"pack", "teaching"}:
        return True   # marker present is allowed; absent is also allowed
                      # (gloss-backed surfaces may move the marker to a separate tag)
    return not has_marker


_PREDICATE_FNS = {
    "no_placeholder":          lambda s, g: _check_no_placeholder(s),
    "no_provenance_only":      lambda s, g: _check_no_provenance_only(s),
    "complete_punctuation":    lambda s, g: _check_complete_punctuation(s),
    "finite_predicate_shape":  lambda s, g: _check_finite_predicate(s),
    "no_dotted_inventory":     lambda s, g: _check_no_dotted_inventory(s),
    "surface_provenance_match": _check_surface_provenance_match,
}


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    category: str
    prompt: str
    surface: str
    grounding_source: str
    predicates: dict[str, bool]
    expected_predicates: tuple[str, ...]
    expected_pass: bool


@dataclass
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _run_case(case: dict[str, Any]) -> CaseResult:
    prompt = case["prompt"]
    expected = tuple(case.get("expected_predicates", ()))

    runtime = ChatRuntime()
    response = runtime.chat(prompt)
    surface = response.surface
    grounding = response.grounding_source or "none"

    predicates = {
        name: bool(fn(surface, grounding))
        for name, fn in _PREDICATE_FNS.items()
    }
    expected_pass = all(predicates[name] for name in expected)

    return CaseResult(
        case_id=case["id"],
        category=case.get("category", "uncategorised"),
        prompt=prompt,
        surface=surface,
        grounding_source=grounding,
        predicates=predicates,
        expected_predicates=expected,
        expected_pass=expected_pass,
    )


def run_lane(cases: list[dict[str, Any]], config: Any = None) -> LaneReport:  # noqa: ARG001
    if not cases:
        return LaneReport(metrics={}, case_details=[])

    results = [_run_case(c) for c in cases]
    total = len(results)

    rates: dict[str, Any] = {"cases": total}
    for name in _PREDICATE_FNS:
        passed = sum(1 for r in results if r.predicates[name])
        rates[f"{name}_rate"] = round(passed / total, 4) if total else 1.0

    expected_pass = sum(1 for r in results if r.expected_pass)
    rates["expected_predicates_pass_rate"] = round(expected_pass / total, 4)

    case_details = [
        {
            "case_id": r.case_id,
            "category": r.category,
            "prompt": r.prompt,
            "surface": r.surface,
            "grounding_source": r.grounding_source,
            "predicates": r.predicates,
            "expected_predicates": list(r.expected_predicates),
            "expected_pass": r.expected_pass,
        }
        for r in results
    ]

    return LaneReport(metrics=rates, case_details=case_details)


__all__ = ["run_lane", "LaneReport", "CaseResult"]
