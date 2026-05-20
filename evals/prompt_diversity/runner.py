"""Prompt-diversity eval lane runner.

Companion to ``evals/prompt_diversity/contract.md`` (ADR-0084 sibling).

Measures how surface quality and grounding generalize across question
types — not just on the cognition-lane's chain-walk fixture.  Beyond the
cognition lane's ``intent_accuracy`` + ``versor_closure_rate``, this
runner adds three new metrics specific to this lane:

- ``response_shape_fit`` — does the surface's structural shape match
  the question shape?  Uses a small per-shape classifier driven by the
  case's ``expected_shape`` field.
- ``audit_in_surface_rate`` — fraction of surfaces leaking audit
  metadata (trust-boundary text, semantic-domain tags, "No session
  evidence yet.").  **Lower is better.**  v1 is the baseline a future
  surface-vs-envelope ADR will move down.
- ``gloss_quote_rate`` — fraction of surfaces visibly drawing from a
  pack ``glosses.jsonl`` entry rather than only from
  ``semantic_domains`` tags.  v1 ≈ 0% by design — the composer is
  unchanged in ADR-0084.  Rises with ADR-0085.

v1 has NO pass thresholds beyond ``versor_closure_rate == 1.00``.  The
lane's v1 job is to establish a baseline distribution across the
matrix.  Pass thresholds get set in v2 after ADR-0084 → 0085 → 0086 has
run and we know which axes are actually moveable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Callable

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from evals._parallel import run_cases_parallel
from generate.intent import IntentTag


# Substring markers that indicate audit-tier metadata leaked into the
# user-facing surface (the leak the surface-vs-envelope ADR will close).
# Pinned to the actual strings today's composers emit so the metric is
# falsifiable rather than wishful.
_AUDIT_MARKERS: tuple[str, ...] = (
    "teaching-grounded (",
    "pack-grounded (",
    "No session evidence yet.",
    "No prior turn in this session to correct yet.",
)
# Semantic-domain tag pattern — e.g. ``cognition.illumination``,
# ``logos.core``, ``relations.kinship.parent``.  A dotted lower-case
# token with at least two segments is almost always a domain leak.
_DOMAIN_TAG_RE = re.compile(r"\b[a-z][a-z_]*(?:\.[a-z][a-z_]*)+\b")
# Honest-disclosure markers used by today's runtime for non-grounded
# answers.  Not audit text — these *are* legitimate surfaces.
_HONEST_DISCLOSURE_MARKERS: tuple[str, ...] = (
    "i don't know",
    "no session evidence yet",
    "no prior turn",
    "i can't",
    "i cannot",
    "unknown",
    "not in my vocabulary",
)
# Procedure-shape markers.
_PROCEDURE_MARKERS: tuple[str, ...] = (
    "first,",
    "then,",
    "finally,",
    "step ",
    "1.",
    "2.",
    "→",
)
# Comparison-shape markers.
_COMPARISON_MARKERS: tuple[str, ...] = (
    "contrasts with",
    "differs from",
    "while",
    "whereas",
    "vs.",
    " versus ",
)
# Cause/why-shape markers.  Both inflected (``reveals``, from the
# chain-walk surface ``light reveals truth``) and bare (``reveal``,
# from the ADR-0085 gloss surface ``Light exists as visible medium
# that reveal truth``) forms are listed so neither composer path
# under-reports explanation-shape fit just on inflection grounds.
_CAUSE_MARKERS: tuple[str, ...] = (
    "because",
    "reveals", "reveal",
    "grounds", "ground",
    "requires", "require",
    "implies", "imply",
    "depends on",
    "is the result of",
    ", which ",
    # ADR-0085 — existential explanation frame.
    "exists as", "exists to",
    " is for ",
    "purpose of",
    # ADR-0085 — verb/adjective explanation frames.
    " is to ", " to be ",
)
# Predicate-identity markers (definition + verification).
_PREDICATE_MARKERS: tuple[str, ...] = (
    " is ",
    " are ",
    " means ",
    " refers to ",
    " denotes ",
    " requires ",
    "yes,",
    "no,",
)


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    category: str
    question_shape: str
    sophistication: str
    domain: str
    prompt: str
    intent_correct: bool
    versor_closure: bool
    versor_condition: float
    response_shape_fit: bool
    audit_in_surface: bool
    gloss_quoted: bool
    surface: str
    trace_hash: str


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _surface_has_any(surface: str, markers: tuple[str, ...]) -> bool:
    lowered = surface.lower()
    return any(marker.lower() in lowered for marker in markers)


def _classify_response_shape(surface: str, expected_shape: str) -> bool:
    """Heuristic: does *surface* match the structural *expected_shape*?

    Deliberately simple substring/regex classifier — the lane's job at
    v1 is to *measure* shape mismatch, not to fix it.  False positives
    are fine; what matters is that the metric moves when ADR-0085 lands.
    """
    lowered = surface.strip().lower()
    if not lowered:
        return False

    if expected_shape == "honest_disclosure":
        return _surface_has_any(surface, _HONEST_DISCLOSURE_MARKERS)

    if expected_shape == "predicate_identity":
        return any(marker in lowered for marker in _PREDICATE_MARKERS)

    if expected_shape == "explanation":
        return any(marker in lowered for marker in (m.lower() for m in _CAUSE_MARKERS))

    if expected_shape == "sequence":
        return any(marker in lowered for marker in _PROCEDURE_MARKERS)

    if expected_shape == "two_subject_contrast":
        return any(marker in lowered for marker in _COMPARISON_MARKERS)

    if expected_shape == "narrative":
        # Multi-clause aggregated content — at least two clauses joined
        # by commas or "and"/"which".
        return lowered.count(",") >= 2 or " which " in lowered

    # Unknown expected_shape — neutral pass to avoid penalising new
    # categories during expansion.
    return True


def _surface_has_audit_leak(surface: str) -> bool:
    """Return True iff the surface contains audit-tier metadata.

    Two leak families:
    1. Trust-boundary preamble (``teaching-grounded (...)``,
       ``pack-grounded (...)``, ``No session evidence yet.``).
    2. Semantic-domain tags as bare tokens (``cognition.illumination``,
       ``logos.core``).
    """
    if _surface_has_any(surface, _AUDIT_MARKERS):
        return True
    return bool(_DOMAIN_TAG_RE.search(surface))


def _surface_quotes_gloss(surface: str, expected_terms: tuple[str, ...]) -> bool:
    """Return True iff the surface visibly draws from a pack gloss.

    Resolves each expected term via
    :func:`chat.pack_resolver.resolve_gloss`, then asks: does the
    surface contain the gloss text verbatim?  The pack-grounded
    composer emits the gloss without paraphrasing
    (``"{Lemma} is {gloss}."``), so substring match is an exact and
    high-confidence "gloss actually quoted" signal — no fuzzy windows,
    no false-positives from one shared content word.

    Note on the v1 prediction:  the contract predicted ``≈ 0%`` here,
    on the assumption that the composer would not consume glosses
    until ADR-0085 landed.  In fact the pack-grounded composer at
    ``chat/pack_grounding.py:398-434`` was *already* gloss-aware
    pre-ADR-0084 but had no glosses to consume.  Once PR #65's content
    landed, the composer immediately started emitting glosses on
    DEFINITION/RECALL.  This metric now reflects that reality.
    """
    if not expected_terms:
        return False

    from chat.pack_resolver import resolve_gloss

    surface_lower = surface.lower()
    for term in expected_terms:
        resolved = resolve_gloss(term)
        if resolved is None:
            continue
        _pack_id, _pos, gloss = resolved
        if not gloss.strip():
            continue
        if gloss.lower().strip() in surface_lower:
            return True
    return False


def _run_case(case: dict[str, Any], pipeline: CognitiveTurnPipeline) -> CaseResult:
    prompt = case["prompt"]
    expected_intent = case["expected_intent"]
    expected_shape = case.get("expected_shape", "")
    expected_terms = tuple(case.get("expected_terms", []))

    result = pipeline.run(prompt, max_tokens=8)
    surface = result.surface

    actual_intent = result.intent.tag if result.intent else IntentTag.UNKNOWN
    intent_correct = actual_intent.value == expected_intent
    versor_ok = result.versor_condition < 1e-6

    return CaseResult(
        case_id=case["id"],
        category=case.get("category", "unknown"),
        question_shape=case.get("question_shape", "unknown"),
        sophistication=case.get("sophistication", "unknown"),
        domain=case.get("domain", "unknown"),
        prompt=prompt,
        intent_correct=intent_correct,
        versor_closure=versor_ok,
        versor_condition=result.versor_condition,
        response_shape_fit=_classify_response_shape(surface, expected_shape),
        audit_in_surface=_surface_has_audit_leak(surface),
        gloss_quoted=_surface_quotes_gloss(surface, expected_terms),
        surface=surface,
        trace_hash=result.trace_hash,
    )


def _build_case_runner(
    config: RuntimeConfig | None = None,
) -> Callable[[dict[str, Any]], CaseResult]:
    """Warm worker-local caches once, then return a per-case scorer.

    Mirrors :mod:`evals.cognition.runner` so the parallel-worker pool's
    cache-warming pattern is consistent across lanes.
    """
    if config is None:
        ChatRuntime()
    else:
        ChatRuntime(config=config)

    def _run(case: dict[str, Any]) -> CaseResult:
        runtime = ChatRuntime(config=config) if config else ChatRuntime()
        pipeline = CognitiveTurnPipeline(runtime)
        return _run_case(case, pipeline)

    return _run


def _aggregate_breakdown(
    results: list[CaseResult],
) -> dict[str, dict[str, dict[str, float]]]:
    """Group results by (question_shape, sophistication, domain) and
    compute per-cell counts + the four moveable metrics.

    The contract calls for per-cell breakdowns so we can see which axes
    move when ADR-0085 lands.  Aggregating in the runner (vs. the CLI)
    keeps the contract-shaped JSON stable across consumers.
    """
    cells: dict[tuple[str, str, str], list[CaseResult]] = {}
    for cr in results:
        key = (cr.question_shape, cr.sophistication, cr.domain)
        cells.setdefault(key, []).append(cr)

    out: dict[str, dict[str, dict[str, float]]] = {}
    for (shape, soph, domain), members in sorted(cells.items()):
        n = len(members)
        cell = {
            "n": n,
            "intent_accuracy": round(sum(1 for m in members if m.intent_correct) / n, 4),
            "response_shape_fit": round(sum(1 for m in members if m.response_shape_fit) / n, 4),
            "audit_in_surface_rate": round(sum(1 for m in members if m.audit_in_surface) / n, 4),
            "gloss_quote_rate": round(sum(1 for m in members if m.gloss_quoted) / n, 4),
        }
        out.setdefault(shape, {}).setdefault(soph, {})[domain] = cell  # type: ignore[assignment]
    return out


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
    workers: int | None = None,
) -> LaneReport:
    """Run all cases and return baseline-distribution metrics + per-case detail."""
    if not cases:
        return LaneReport(metrics={"total": 0}, case_details=[])

    case_runner_builder = partial(_build_case_runner, config=config)
    case_results: list[CaseResult] = run_cases_parallel(
        cases,
        case_runner_builder,
        n_workers=workers if workers is not None else 4,
    )

    total = len(case_results)
    intent_correct = sum(1 for cr in case_results if cr.intent_correct)
    versor_closures = sum(1 for cr in case_results if cr.versor_closure)
    shape_fits = sum(1 for cr in case_results if cr.response_shape_fit)
    audit_leaks = sum(1 for cr in case_results if cr.audit_in_surface)
    gloss_quotes = sum(1 for cr in case_results if cr.gloss_quoted)

    metrics: dict[str, Any] = {
        "total": total,
        "intent_accuracy": round(intent_correct / total, 4),
        "versor_closure_rate": round(versor_closures / total, 4),
        "response_shape_fit": round(shape_fits / total, 4),
        "audit_in_surface_rate": round(audit_leaks / total, 4),
        "gloss_quote_rate": round(gloss_quotes / total, 4),
        "breakdown": _aggregate_breakdown(case_results),
    }

    case_details: list[dict[str, Any]] = [
        {
            "case_id": cr.case_id,
            "category": cr.category,
            "question_shape": cr.question_shape,
            "sophistication": cr.sophistication,
            "domain": cr.domain,
            "intent_correct": cr.intent_correct,
            "versor_closure": cr.versor_closure,
            "versor_condition": round(cr.versor_condition, 9),
            "response_shape_fit": cr.response_shape_fit,
            "audit_in_surface": cr.audit_in_surface,
            "gloss_quoted": cr.gloss_quoted,
            "trace_hash": cr.trace_hash,
            "surface": cr.surface,
        }
        for cr in case_results
    ]

    return LaneReport(metrics=metrics, case_details=case_details)
