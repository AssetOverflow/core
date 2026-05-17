"""Learning-curve bench — capability vs reviewed-teaching depth.

Runs an eval lane at successive teaching depths (e.g. 0, 5, 10, 25,
50, 100 reviewed corrections) sharing one TeachingStore across the
pipelines instantiated for each case. Produces:

- A monotonic score curve per lane.
- A per-step trace-hash digest proving every intermediate post-teaching
  state is byte-identical across reruns (the deterministic-replay claim
  applied to the teaching loop).

The bench is the load-bearing demo for Tier 3 of evals/CLAIMS.md:
"N corrections -> +X% on lane L, locked deterministically, replayable
forever." Without it, the teaching-loop claim is unfalsifiable from
the outside.

Usage:

    from benchmarks.learning_curve import run_learning_curve
    curve = run_learning_curve(
        lane="cognition",
        cycles=(0, 5, 10, 25, 50, 100),
        teaching_examples=load_my_corrections(),
    )
    assert curve.is_monotonic
    assert curve.replay_deterministic
    print(curve.summary())

CLI surface (added to core/cli.py separately):

    core bench learning-curve <lane> --cycles 0,5,25,100
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from evals.framework import get_lane, load_cases
from generate.intent import DialogueIntent, IntentTag
from teaching.correction import CorrectionCandidate, _candidate_id
from teaching.epistemic import EpistemicStatus
from teaching.review import ReviewOutcome, ReviewedTeachingExample, _review_hash
from teaching.store import TeachingStore


@dataclass(frozen=True, slots=True)
class TeachingExampleSpec:
    """Minimal spec to synthesize a ReviewedTeachingExample for replay.

    Bench corrections are reviewed examples that are content-addressed
    by (subject, correction_text). They must not reference live dialogue
    state, otherwise the curve depends on session order and stops being
    replayable.
    """
    subject: str
    correction_text: str

    def to_reviewed(self) -> ReviewedTeachingExample:
        intent = DialogueIntent(tag=IntentTag.CORRECTION, subject=self.subject)
        prior_surface = ""
        prior_turn = 0
        cand = CorrectionCandidate(
            correction_text=self.correction_text,
            intent=intent,
            prior_surface=prior_surface,
            prior_turn=prior_turn,
            candidate_id=_candidate_id(self.correction_text, prior_surface, prior_turn),
        )
        outcome = ReviewOutcome.ACCEPTED
        return ReviewedTeachingExample(
            candidate=cand,
            outcome=outcome,
            review_hash=_review_hash(cand, outcome),
            epistemic_status=EpistemicStatus.SPECULATIVE,
        )


@dataclass(frozen=True, slots=True)
class CurvePoint:
    cycle: int
    metrics: dict[str, float]
    store_digest: str
    lane_trace_digest: str


@dataclass(frozen=True, slots=True)
class LearningCurveReport:
    lane: str
    version: str
    primary_metric: str
    points: tuple[CurvePoint, ...]
    replay_points: tuple[CurvePoint, ...]

    @property
    def is_monotonic(self) -> bool:
        scores = [p.metrics.get(self.primary_metric, 0.0) for p in self.points]
        return all(b >= a for a, b in zip(scores, scores[1:]))

    @property
    def replay_deterministic(self) -> bool:
        if len(self.points) != len(self.replay_points):
            return False
        for first, second in zip(self.points, self.replay_points):
            if first.store_digest != second.store_digest:
                return False
            if first.lane_trace_digest != second.lane_trace_digest:
                return False
        return True

    def as_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "version": self.version,
            "primary_metric": self.primary_metric,
            "is_monotonic": self.is_monotonic,
            "replay_deterministic": self.replay_deterministic,
            "points": [
                {
                    "cycle": p.cycle,
                    "metrics": p.metrics,
                    "store_digest": p.store_digest,
                    "lane_trace_digest": p.lane_trace_digest,
                }
                for p in self.points
            ],
        }

    def summary(self) -> str:
        head = f"learning_curve[{self.lane}@{self.version}] metric={self.primary_metric}"
        rows = "\n".join(
            f"  cycle={p.cycle:>4}  {self.primary_metric}={p.metrics.get(self.primary_metric, 0.0):.4f}  "
            f"trace={p.lane_trace_digest[:12]}  store={p.store_digest[:12]}"
            for p in self.points
        )
        flags = (
            f"  monotonic={self.is_monotonic}  replay_deterministic={self.replay_deterministic}"
        )
        return f"{head}\n{rows}\n{flags}"


def _store_digest(store: TeachingStore) -> str:
    payload = json.dumps(
        [p.as_dict() for p in store.pending_proposals()],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _lane_trace_digest(case_details: list[dict[str, Any]]) -> str:
    hashes = [d.get("trace_hash", "") for d in case_details]
    return hashlib.sha256("|".join(hashes).encode("utf-8")).hexdigest()


def _build_store(specs: Iterable[TeachingExampleSpec], depth: int) -> TeachingStore:
    """Construct a fresh store and add the first `depth` specs in order.

    Re-built per depth (rather than mutated in place) so each curve
    point is reproducible from `(specs, depth)` alone — not from the
    history of a long-lived process.
    """
    store = TeachingStore(capacity=max(depth, 1) * 4 + 8)
    for spec in list(specs)[:depth]:
        store.add(spec.to_reviewed())
    return store


def _run_lane_with_store(
    lane_cases: list[dict[str, Any]],
    store: TeachingStore,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    """Run cognition-lane-style cases through pipelines that share `store`.

    We do not go through `evals.framework.run_lane` because the framework
    runner constructs its own pipeline per case with a fresh empty store.
    To make the teaching depth load-bearing, the bench must inject the
    store. The metric extraction below intentionally mirrors
    `evals/cognition/runner.py` so the curve numbers are directly
    comparable to the published lane scores.
    """
    from evals.cognition.runner import _run_case

    total = 0
    intent_correct = 0
    terms_expected = 0
    terms_captured = 0
    surface_grounded = 0
    versor_closures = 0
    case_details: list[dict[str, Any]] = []

    for case in lane_cases:
        runtime = ChatRuntime()
        pipeline = CognitiveTurnPipeline(runtime, teaching_store=store)
        cr = _run_case(case, pipeline)

        total += 1
        if cr.intent_correct:
            intent_correct += 1
        terms_expected += len(cr.terms_expected)
        terms_captured += len(cr.terms_captured)
        if cr.surface_contains_pass:
            surface_grounded += 1
        if cr.versor_closure:
            versor_closures += 1

        case_details.append({
            "case_id": cr.case_id,
            "intent_correct": cr.intent_correct,
            "surface_contains_pass": cr.surface_contains_pass,
            "versor_closure": cr.versor_closure,
            "versor_condition": round(cr.versor_condition, 9),
            "trace_hash": cr.trace_hash,
        })

    metrics = {
        "total": float(total),
        "intent_accuracy": round(intent_correct / total, 4) if total else 0.0,
        "term_capture_rate": round(terms_captured / terms_expected, 4) if terms_expected else 1.0,
        "surface_groundedness": round(surface_grounded / total, 4) if total else 0.0,
        "versor_closure_rate": round(versor_closures / total, 4) if total else 0.0,
    }
    return metrics, case_details


def run_learning_curve(
    *,
    lane: str,
    cycles: tuple[int, ...],
    teaching_examples: Iterable[TeachingExampleSpec],
    version: str = "v1",
    split: str = "public",
    primary_metric: str = "intent_accuracy",
    verify_replay: bool = True,
) -> LearningCurveReport:
    """Run `lane` at each teaching depth in `cycles`, return a curve report.

    `verify_replay` re-runs the entire curve a second time and asserts
    both the per-step store digest and the per-step lane trace digest
    are byte-identical to the first pass. This is the deterministic
    replay claim applied to the teaching loop, not just to one prompt.
    """
    lane_info = get_lane(lane)
    cases_path = lane_info.public_cases_path(version) if split == "public" else lane_info.dev_cases_path()
    cases = load_cases(cases_path)
    specs = tuple(teaching_examples)

    def _one_pass() -> tuple[CurvePoint, ...]:
        out: list[CurvePoint] = []
        for depth in cycles:
            store = _build_store(specs, depth)
            metrics, details = _run_lane_with_store(cases, store)
            out.append(CurvePoint(
                cycle=depth,
                metrics=metrics,
                store_digest=_store_digest(store),
                lane_trace_digest=_lane_trace_digest(details),
            ))
        return tuple(out)

    first = _one_pass()
    second = _one_pass() if verify_replay else first

    return LearningCurveReport(
        lane=lane,
        version=version,
        primary_metric=primary_metric,
        points=first,
        replay_points=second,
    )


def write_curve(report: LearningCurveReport, root: Path | None = None) -> Path:
    """Persist a curve report to evals/reports/learning_curves/<lane>.json."""
    base = root or Path(__file__).resolve().parent.parent / "evals" / "reports" / "learning_curves"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{report.lane}.json"
    path.write_text(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    return path


DEFAULT_COGNITION_TEACHING: tuple[TeachingExampleSpec, ...] = (
    TeachingExampleSpec(subject="truth", correction_text="truth is coherence"),
    TeachingExampleSpec(subject="knowledge", correction_text="knowledge is justified true belief"),
    TeachingExampleSpec(subject="wisdom", correction_text="wisdom is applied knowledge"),
    TeachingExampleSpec(subject="light", correction_text="light is electromagnetic radiation"),
    TeachingExampleSpec(subject="meaning", correction_text="meaning is reference plus use"),
    TeachingExampleSpec(subject="concept", correction_text="a concept is a coherent abstraction"),
    TeachingExampleSpec(subject="coherence", correction_text="coherence is mutual support among propositions"),
    TeachingExampleSpec(subject="proposition", correction_text="a proposition is a truth-apt claim"),
)
