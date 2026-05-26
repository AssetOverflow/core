"""ADR-0159 / W-025 — read-only contemplation quality evaluation.

The lane scores the structured report emitted by ``core demo learning-arc
--json``.  It intentionally does not create proposals, accept proposals,
mutate corpora, mutate packs, or write engine_state.  Replay-equivalence is
measured as a quality signal only; it is never treated as permission to ratify.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from evals.learning_arc.run_demo import run_demo as run_learning_arc_demo


_REQUIRED_SCENES: tuple[str, ...] = (
    "S1_cold_session",
    "S2_checkpoint_enrichment",
    "S3_engine_authored_proposal",
    "S4_operator_ratifies",
    "S5_grounded_session",
)


@dataclass(frozen=True, slots=True)
class QualityMetric:
    """One deterministic, non-mutating quality gate."""

    name: str
    passed: bool
    value: Any
    expected: Any
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "value": self.value,
            "expected": self.expected,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ContemplationQualityReport:
    """Read-only quality report over one learning-arc output."""

    lane: str
    source: str
    source_digest: str
    metrics: tuple[QualityMetric, ...]

    @property
    def passed(self) -> bool:
        return all(metric.passed for metric in self.metrics)

    def as_dict(self) -> dict[str, Any]:
        passed_count = sum(1 for metric in self.metrics if metric.passed)
        total = len(self.metrics)
        return {
            "lane": self.lane,
            "source": self.source,
            "source_digest": self.source_digest,
            "passed": self.passed,
            "score": {
                "passed": passed_count,
                "total": total,
                "rate": passed_count / total if total else 0.0,
            },
            "metrics": [metric.as_dict() for metric in self.metrics],
        }


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _scene(report: dict[str, Any], scene_name: str) -> dict[str, Any]:
    for scene in report.get("scenes", []):
        if isinstance(scene, dict) and scene.get("scene") == scene_name:
            detail = scene.get("detail", {})
            return detail if isinstance(detail, dict) else {}
    return {}


def _metric(
    name: str,
    passed: bool,
    value: Any,
    expected: Any,
    reason: str,
) -> QualityMetric:
    return QualityMetric(
        name=name,
        passed=bool(passed),
        value=value,
        expected=expected,
        reason=reason,
    )


def evaluate_report(report: dict[str, Any]) -> ContemplationQualityReport:
    """Score a ``core demo learning-arc --json`` report.

    This function is pure over the provided dictionary.  It is suitable for
    testing stored CI contemplation reports without touching runtime state.
    """

    scene_names = tuple(
        scene.get("scene")
        for scene in report.get("scenes", [])
        if isinstance(scene, dict)
    )
    s1 = _scene(report, "S1_cold_session")
    s2 = _scene(report, "S2_checkpoint_enrichment")
    s3 = _scene(report, "S3_engine_authored_proposal")
    s4 = _scene(report, "S4_operator_ratifies")
    s5 = _scene(report, "S5_grounded_session")

    replay = s3.get("replay_evidence", {})
    if not isinstance(replay, dict):
        replay = {}
    proposed_chain = s3.get("proposed_chain", {})
    if not isinstance(proposed_chain, dict):
        proposed_chain = {}
    engine_chain = s2.get("engine_chain", {})
    if not isinstance(engine_chain, dict):
        engine_chain = {}

    before = report.get("before", {})
    after = report.get("after", {})
    if not isinstance(before, dict):
        before = {}
    if not isinstance(after, dict):
        after = {}

    metrics = (
        _metric(
            "scene_contract",
            scene_names == _REQUIRED_SCENES,
            scene_names,
            _REQUIRED_SCENES,
            "ADR-0152 learning-arc output must retain the five audited scenes in order.",
        ),
        _metric(
            "deterministic_replay_integrity",
            replay.get("replay_equivalent") is True
            and replay.get("regressed_metrics") == [],
            {
                "replay_equivalent": replay.get("replay_equivalent"),
                "regressed_metrics": replay.get("regressed_metrics"),
            },
            {"replay_equivalent": True, "regressed_metrics": []},
            "ADR-0057 replay-equivalence must pass before proposal review eligibility.",
        ),
        _metric(
            "typed_contemplation_provenance",
            s3.get("source_kind") == "contemplation",
            s3.get("source_kind"),
            "contemplation",
            "ADR-0151/0152 require engine-authored proposals to carry contemplation provenance.",
        ),
        _metric(
            "engine_authored_specificity",
            s2.get("engine_chain_found") is True
            and engine_chain.get("connective") == report.get("engine_connective")
            and engine_chain.get("object") == report.get("engine_object")
            and proposed_chain.get("connective") == report.get("engine_connective")
            and proposed_chain.get("object") == report.get("engine_object"),
            {
                "engine_chain_found": s2.get("engine_chain_found"),
                "engine_chain": engine_chain,
                "proposed_chain": proposed_chain,
            },
            "engine chain and proposed chain share the same engine-derived connective/object",
            "The W-025 eval scores specificity, not generic proposal existence.",
        ),
        _metric(
            "grounding_transition",
            s1.get("grounding_source") != "teaching"
            and s5.get("grounding_source") == "teaching"
            and report.get("learning_arc_closed") is True,
            {
                "before_grounding_source": s1.get("grounding_source"),
                "after_grounding_source": s5.get("grounding_source"),
                "learning_arc_closed": report.get("learning_arc_closed"),
            },
            {"before_not": "teaching", "after": "teaching", "learning_arc_closed": True},
            "The proposal must produce a measured same-prompt transition into teaching-grounded output.",
        ),
        _metric(
            "downstream_gain_observed",
            before.get("surface") != after.get("surface"),
            {"before": before.get("surface"), "after": after.get("surface")},
            "before surface differs from after surface",
            "The accepted transient chain must have an observable effect on the same prompt.",
        ),
        _metric(
            "active_corpus_boundary",
            report.get("active_corpus_byte_identical") is True
            and s4.get("active_corpus_byte_identical") is True,
            {
                "report_active_corpus_byte_identical": report.get("active_corpus_byte_identical"),
                "s4_active_corpus_byte_identical": s4.get("active_corpus_byte_identical"),
            },
            True,
            "ADR-0152/0155: contemplation-quality scoring must never imply active corpus mutation.",
        ),
        _metric(
            "pending_not_auto_accepted",
            s3.get("state") == "pending",
            s3.get("state"),
            "pending",
            "ADR-0057: replay-equivalence is a precondition, never permission to auto-accept.",
        ),
        _metric(
            "stable_proposal_identity_present",
            bool(str(s3.get("proposal_id", "")).strip()),
            s3.get("proposal_id"),
            "non-empty deterministic proposal_id",
            "ADR-0151 idempotency requires stable proposal identity to avoid duplicate pressure.",
        ),
    )

    return ContemplationQualityReport(
        lane="contemplation-quality",
        source="core demo learning-arc --json",
        source_digest=_digest(report),
        metrics=metrics,
    )


def run_eval() -> ContemplationQualityReport:
    """Run the source demo and score its output.

    ``run_demo(emit_json=True)`` uses tempdirs/transient corpus paths per
    ADR-0152.  This eval adds no write path of its own.
    """

    return evaluate_report(run_learning_arc_demo(emit_json=True))


__all__ = [
    "ContemplationQualityReport",
    "QualityMetric",
    "evaluate_report",
    "run_eval",
]
