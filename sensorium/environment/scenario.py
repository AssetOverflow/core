"""Hypothesis-scoped environmental falsification scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from sensorium.audio.checksum import sha256_json
from sensorium.environment.falsification import (
    ExpectedObservationFrame,
    FalsificationResidual,
    FalsificationRun,
    ObservationUnitRef,
    compare_expected_to_observation,
)
from sensorium.environment.frame import ObservationFrame

SPECULATIVE_STATUS = "SPECULATIVE"


@dataclass(frozen=True, slots=True)
class HypothesisClaim:
    """Speculative claim that gives expected evidence a reason to exist."""

    claim_id: str
    claim_text: str
    domain: str
    basis_trace_hashes: tuple[str, ...]
    hypothesis_sha256: str
    epistemic_status: str = SPECULATIVE_STATUS

    def as_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "domain": self.domain,
            "basis_trace_hashes": list(self.basis_trace_hashes),
            "hypothesis_sha256": self.hypothesis_sha256,
            "epistemic_status": self.epistemic_status,
        }


def build_hypothesis_claim(
    *,
    claim_id: str,
    claim_text: str,
    domain: str,
    basis_trace_hashes: Iterable[str] = (),
) -> HypothesisClaim:
    if not claim_id.strip():
        raise ValueError("HypothesisClaim.claim_id is required")
    if not claim_text.strip():
        raise ValueError("HypothesisClaim.claim_text is required")
    if not domain.strip():
        raise ValueError("HypothesisClaim.domain is required")
    basis = tuple(sorted(set(str(h) for h in basis_trace_hashes if str(h).strip())))
    payload = {
        "kind": "HypothesisClaim",
        "claim_id": claim_id,
        "claim_text": claim_text,
        "domain": domain,
        "basis_trace_hashes": list(basis),
        "epistemic_status": SPECULATIVE_STATUS,
    }
    return HypothesisClaim(
        claim_id=claim_id,
        claim_text=claim_text,
        domain=domain,
        basis_trace_hashes=basis,
        hypothesis_sha256=sha256_json(payload),
    )


def _canonical_expected_frames(
    frames: Iterable[ExpectedObservationFrame],
) -> tuple[ExpectedObservationFrame, ...]:
    ordered = sorted(tuple(frames), key=lambda f: (f.expected_id, f.expected_sha256))
    deduped: list[ExpectedObservationFrame] = []
    seen: set[tuple[str, str]] = set()
    seen_ids: dict[str, str] = {}
    for frame in ordered:
        key = (frame.expected_id, frame.expected_sha256)
        if key in seen:
            continue
        if frame.expected_id in seen_ids and seen_ids[frame.expected_id] != frame.expected_sha256:
            raise ValueError(f"conflicting expected frame id: {frame.expected_id}")
        seen.add(key)
        seen_ids[frame.expected_id] = frame.expected_sha256
        deduped.append(frame)
    return tuple(deduped)


@dataclass(frozen=True, slots=True)
class ExperimentPlan:
    """One speculative hypothesis plus canonical expected evidence frames."""

    hypothesis: HypothesisClaim
    expected_frames: tuple[ExpectedObservationFrame, ...]
    plan_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "hypothesis": self.hypothesis.as_dict(),
            "expected_frames": [frame.as_dict() for frame in self.expected_frames],
            "plan_sha256": self.plan_sha256,
        }


def build_experiment_plan(
    *,
    hypothesis: HypothesisClaim,
    expected_frames: Iterable[ExpectedObservationFrame],
) -> ExperimentPlan:
    frames = _canonical_expected_frames(expected_frames)
    if not frames:
        raise ValueError("ExperimentPlan requires at least one expected frame")
    payload = {
        "kind": "ExperimentPlan",
        "hypothesis": hypothesis.as_dict(),
        "expected_frames": [frame.as_dict() for frame in frames],
    }
    return ExperimentPlan(
        hypothesis=hypothesis,
        expected_frames=frames,
        plan_sha256=sha256_json(payload),
    )


@dataclass(frozen=True, slots=True)
class ScenarioActualFrame:
    """Actual observation frame bound to one expected frame id."""

    expected_id: str
    frame: ObservationFrame
    actual_refs: tuple[ObservationUnitRef, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "expected_id": self.expected_id,
            "actual_frame_id": self.frame.frame_id,
            "actual_trace_hash": self.frame.trace_hash,
            "actual_ref_slots": [ref.slot_id for ref in self.actual_refs],
        }


@dataclass(frozen=True, slots=True)
class FalsificationScenario:
    """Immutable scenario binding one plan to actual observation frames."""

    plan: ExperimentPlan
    actual_frames: tuple[ScenarioActualFrame, ...]
    scenario_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "plan": self.plan.as_dict(),
            "actual_frames": [frame.as_dict() for frame in self.actual_frames],
            "scenario_sha256": self.scenario_sha256,
        }


@dataclass(frozen=True, slots=True)
class ScenarioReport:
    """Aggregate report over ordered falsification runs."""

    hypothesis_sha256: str
    plan_sha256: str
    scenario_sha256: str
    verdict: str
    total_count: int
    supported_count: int
    falsified_count: int
    runs: tuple[FalsificationRun, ...]
    report_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "hypothesis_sha256": self.hypothesis_sha256,
            "plan_sha256": self.plan_sha256,
            "scenario_sha256": self.scenario_sha256,
            "verdict": self.verdict,
            "total_count": self.total_count,
            "supported_count": self.supported_count,
            "falsified_count": self.falsified_count,
            "runs": [run.as_dict() for run in self.runs],
            "report_sha256": self.report_sha256,
        }


def _actual_frame_items(
    plan: ExperimentPlan,
    actual_frames_by_expected_id: Mapping[str, ObservationFrame],
    actual_refs_by_expected_id: Mapping[str, Iterable[ObservationUnitRef]] | None,
) -> tuple[ScenarioActualFrame, ...]:
    refs_by_id = actual_refs_by_expected_id or {}
    expected_ids = {expected.expected_id for expected in plan.expected_frames}
    unknown_actual = sorted(set(actual_frames_by_expected_id) - expected_ids)
    if unknown_actual:
        raise ValueError(f"actual frame supplied for unknown expected_id: {unknown_actual[0]}")
    unknown_refs = sorted(set(refs_by_id) - expected_ids)
    if unknown_refs:
        raise ValueError(f"actual refs supplied for unknown expected_id: {unknown_refs[0]}")
    items: list[ScenarioActualFrame] = []
    for expected in plan.expected_frames:
        actual = actual_frames_by_expected_id.get(expected.expected_id)
        if actual is None:
            continue
        refs = tuple(refs_by_id.get(expected.expected_id, ()))
        items.append(ScenarioActualFrame(expected.expected_id, actual, refs))
    return tuple(items)


def build_falsification_scenario(
    *,
    plan: ExperimentPlan,
    actual_frames_by_expected_id: Mapping[str, ObservationFrame],
    actual_refs_by_expected_id: Mapping[str, Iterable[ObservationUnitRef]] | None = None,
) -> FalsificationScenario:
    actual_frames = _actual_frame_items(
        plan,
        actual_frames_by_expected_id,
        actual_refs_by_expected_id,
    )
    payload = {
        "kind": "FalsificationScenario",
        "plan_sha256": plan.plan_sha256,
        "actual_frames": [frame.as_dict() for frame in actual_frames],
    }
    return FalsificationScenario(
        plan=plan,
        actual_frames=actual_frames,
        scenario_sha256=sha256_json(payload),
    )


def _missing_actual_run(expected: ExpectedObservationFrame) -> FalsificationRun:
    missing = tuple(ref.slot_id for ref in expected.unit_refs)
    residual_payload = {
        "kind": "FalsificationResidual",
        "matched": [],
        "missing": list(missing),
        "unexpected": [],
        "changed": [],
    }
    residual = FalsificationResidual(
        matched=(),
        missing=missing,
        unexpected=(),
        changed=(),
        residual_sha256=sha256_json(residual_payload),
    )
    actual_trace_hash = sha256_json({
        "kind": "MissingActualObservationFrame",
        "expected_id": expected.expected_id,
    })
    trace_payload = {
        "kind": "FalsificationRun",
        "expected_id": expected.expected_id,
        "actual_frame_id": "__missing_observation_frame__",
        "verdict": "FALSIFIED",
        "residual_sha256": residual.residual_sha256,
        "expected_sha256": expected.expected_sha256,
        "actual_trace_hash": actual_trace_hash,
    }
    return FalsificationRun(
        expected_id=expected.expected_id,
        actual_frame_id="__missing_observation_frame__",
        verdict="FALSIFIED",
        residual=residual,
        expected_sha256=expected.expected_sha256,
        actual_trace_hash=actual_trace_hash,
        trace_hash=sha256_json(trace_payload),
    )


def run_falsification_scenario(
    plan: ExperimentPlan,
    actual_frames_by_expected_id: Mapping[str, ObservationFrame],
    actual_refs_by_expected_id: Mapping[str, Iterable[ObservationUnitRef]] | None = None,
) -> ScenarioReport:
    """Run a plan through the existing expected-vs-actual comparator."""
    scenario = build_falsification_scenario(
        plan=plan,
        actual_frames_by_expected_id=actual_frames_by_expected_id,
        actual_refs_by_expected_id=actual_refs_by_expected_id,
    )
    actual_by_expected = {item.expected_id: item for item in scenario.actual_frames}
    runs: list[FalsificationRun] = []
    for expected in scenario.plan.expected_frames:
        actual_item = actual_by_expected.get(expected.expected_id)
        if actual_item is None:
            runs.append(_missing_actual_run(expected))
        else:
            runs.append(
                compare_expected_to_observation(
                    expected,
                    actual_item.frame,
                    actual_refs=actual_item.actual_refs or None,
                )
            )
    supported = sum(1 for run in runs if run.verdict == "SUPPORTED")
    falsified = sum(1 for run in runs if run.verdict == "FALSIFIED")
    verdict = "FALSIFIED" if falsified else "SUPPORTED"
    payload = {
        "kind": "ScenarioReport",
        "hypothesis_sha256": scenario.plan.hypothesis.hypothesis_sha256,
        "plan_sha256": scenario.plan.plan_sha256,
        "scenario_sha256": scenario.scenario_sha256,
        "verdict": verdict,
        "total_count": len(runs),
        "supported_count": supported,
        "falsified_count": falsified,
        "run_trace_hashes": [run.trace_hash for run in runs],
    }
    return ScenarioReport(
        hypothesis_sha256=scenario.plan.hypothesis.hypothesis_sha256,
        plan_sha256=scenario.plan.plan_sha256,
        scenario_sha256=scenario.scenario_sha256,
        verdict=verdict,
        total_count=len(runs),
        supported_count=supported,
        falsified_count=falsified,
        runs=tuple(runs),
        report_sha256=sha256_json(payload),
    )


__all__ = [
    "ExperimentPlan",
    "FalsificationScenario",
    "HypothesisClaim",
    "ScenarioActualFrame",
    "ScenarioReport",
    "build_experiment_plan",
    "build_falsification_scenario",
    "build_hypothesis_claim",
    "run_falsification_scenario",
]
