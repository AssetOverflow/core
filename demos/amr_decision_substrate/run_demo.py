from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.protocol import (
    CtpEpistemic,
    CtpInvariant,
    CtpProof,
    JsonlEventReader,
    JsonlEventSink,
    canonical_bytes,
    canonical_hash,
    evidence_observed,
    turn_completed,
    turn_refused,
    turn_requested,
    verify_chain,
)
from generate.exhaustion import RefusalReason
from recognition.anti_unifier import derive_recognizer
from recognition.outcome import EvidenceSpan, FeatureBundle, NegativeEvidence


Decision = Literal["PROCEED", "STOP", "REFUSE"]

SCENARIO_PATH = Path(__file__).with_name("scenarios.jsonl")
DEFAULT_OUTPUT_DIR = Path(__file__).with_name("out")


@dataclass(frozen=True, slots=True)
class Scenario:
    scenario_id: str
    description: str
    simulated_input: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    scenario_id: str
    decision: Decision
    reason: str
    core_input: str
    core_surface: str
    core_refusal_reason: str
    trace_hash: str
    versor_condition: float
    ctp_message_id: str


def _span(tokens: tuple[str, ...], start: int, end: int) -> EvidenceSpan:
    return EvidenceSpan(start=start, end=end, text=" ".join(tokens[start:end]))


def _bundle(
    tokens: tuple[str, ...],
    *,
    agent: str,
    count: int,
    unit: str,
) -> FeatureBundle:
    return FeatureBundle.from_mapping(
        {
            "agent": (agent, _span(tokens, 0, 1)),
            "count": (count, _span(tokens, 2, 3)),
            "modality": (
                "simulated",
                NegativeEvidence(0, len(tokens), "abstract fixture, not sensor data"),
            ),
            "polarity": ("+", NegativeEvidence(0, len(tokens), "no negator present")),
            "relation": ("has", _span(tokens, 1, 2)),
            "unit": (unit, _span(tokens, 3, 4)),
        }
    )


def _recognizer():
    examples = []
    for tokens, agent, count in (
        (("alpha", "has", "1", "path"), "alpha", 1),
        (("beta", "has", "0", "path"), "beta", 0),
    ):
        examples.append((tokens, _bundle(tokens, agent=agent, count=count, unit="path")))
    return derive_recognizer(examples)


def _load_scenarios(path: Path = SCENARIO_PATH) -> tuple[Scenario, ...]:
    rows: list[Scenario] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        rows.append(
            Scenario(
                scenario_id=str(raw["scenario_id"]),
                description=str(raw["description"]),
                simulated_input=dict(raw["simulated_input"]),
            )
        )
    if not rows:
        raise ValueError(f"{path} did not contain scenarios")
    return tuple(rows)


def _policy_decision(simulated_input: dict[str, Any]) -> tuple[Decision, str]:
    required = {
        "route_state",
        "path_count",
        "path_confidence",
        "obstacle_state",
        "operator_authorized",
        "zone",
    }
    missing = sorted(required - simulated_input.keys())
    if missing:
        return "REFUSE", f"under_determined: missing {','.join(missing)}"
    if simulated_input["route_state"] != "mapped":
        return "REFUSE", "under_determined: route is not mapped"
    if isinstance(simulated_input["path_confidence"], bool) or not isinstance(
        simulated_input["path_confidence"], (int, float)
    ):
        return "REFUSE", "under_determined: path_confidence is not numeric"
    if float(simulated_input["path_confidence"]) < 0.85:
        return "REFUSE", "under_determined: path confidence below bound"
    if simulated_input["operator_authorized"] is not True:
        return "STOP", "operator not authorized"
    if simulated_input["obstacle_state"] in {"occupied", "blocked"}:
        return "STOP", f"path not clear: {simulated_input['obstacle_state']}"
    if simulated_input["obstacle_state"] != "clear":
        return "REFUSE", f"out_of_distribution: obstacle_state={simulated_input['obstacle_state']!r}"
    if isinstance(simulated_input["path_count"], bool) or not isinstance(
        simulated_input["path_count"], int
    ):
        return "REFUSE", "under_determined: path_count is not numeric"
    if int(simulated_input["path_count"]) < 1:
        return "STOP", "no admissible path in simulated record"
    return "PROCEED", "mapped route, clear path, sufficient confidence"


def _core_input_for(scenario: Scenario, decision: Decision) -> str:
    sim = scenario.simulated_input
    if decision == "REFUSE":
        return f"ambiguous telemetry for {scenario.scenario_id} cannot bind route evidence"
    path_count = int(sim["path_count"])
    return f"{scenario.scenario_id.replace('-', '_')} has {path_count} path"


def _proof_for(result, *, replay_digest: str, decision: Decision) -> CtpProof:
    invariants = (
        CtpInvariant(
            name="versor_condition",
            status="passed" if result.versor_condition < 1e-6 else "failed",
            value=float(result.versor_condition),
            threshold=1e-6,
        ),
        CtpInvariant(
            name="decision_domain",
            status="passed",
            value=decision in {"PROCEED", "STOP", "REFUSE"},
            threshold=True,
            detail="bounded proceed/stop/refuse domain",
        ),
    )
    return CtpProof(
        trace_hash=result.trace_hash,
        replay_digest=replay_digest,
        admissibility_trace_hash=result.admissibility_trace_hash,
        operator_invocation=result.operator_invocation,
        versor_condition=float(result.versor_condition),
        refusal_reason=result.refusal_reason,
        invariants=invariants,
    )


def _run_once(scenarios: tuple[Scenario, ...], trace_path: Path) -> tuple[DecisionRecord, ...]:
    if trace_path.exists():
        trace_path.unlink()
    sink = JsonlEventSink(trace_path)
    pipeline = CognitiveTurnPipeline(ChatRuntime(no_load_state=True), recognizer=_recognizer())
    records: list[DecisionRecord] = []

    for sequence_base, scenario in enumerate(scenarios):
        decision, reason = _policy_decision(scenario.simulated_input)
        core_input = _core_input_for(scenario, decision)
        correlation_id = f"amr-demo:{scenario.scenario_id}"

        observed = evidence_observed(
            "simulated_amr_fixture",
            scenario.scenario_id,
            correlation_id=correlation_id,
            sequence=sequence_base * 10,
        )
        requested = turn_requested(
            core_input,
            correlation_id=correlation_id,
            sequence=sequence_base * 10 + 1,
        )
        result = pipeline.run(core_input, max_tokens=4)

        if decision == "REFUSE" and result.refusal_reason != RefusalReason.RECOGNITION_REFUSED.value:
            raise RuntimeError(
                f"{scenario.scenario_id} was expected to materialize CORE recognition refusal; "
                f"got {result.refusal_reason!r}"
            )

        replay_material = {
            "core_refusal_reason": result.refusal_reason,
            "decision": decision,
            "reason": reason,
            "scenario_id": scenario.scenario_id,
            "trace_hash": result.trace_hash,
        }
        replay_digest = canonical_hash(replay_material)
        epistemic = CtpEpistemic(
            state="REFUSED" if decision == "REFUSE" else "GROUNDED",
            grounding_source=(
                "core_recognition_refusal"
                if decision == "REFUSE"
                else "simulated_fixture_plus_core_trace"
            ),
            normative_clearance="UNASSESSABLE" if decision == "REFUSE" else "CLEARED",
        )
        proof = _proof_for(result, replay_digest=replay_digest, decision=decision)
        if decision == "REFUSE":
            terminal = turn_refused(
                refusal_reason=result.refusal_reason,
                trace_hash=result.trace_hash,
                epistemic=epistemic,
                causation_id=requested.message_id,
                correlation_id=correlation_id,
                sequence=sequence_base * 10 + 2,
            )
        else:
            terminal = turn_completed(
                surface=f"decision={decision}; reason={reason}",
                trace_hash=result.trace_hash,
                epistemic=epistemic,
                causation_id=requested.message_id,
                correlation_id=correlation_id,
                sequence=sequence_base * 10 + 2,
                proof=proof,
            )

        sink.append(observed)
        sink.append(requested)
        sink.append(terminal)
        records.append(
            DecisionRecord(
                scenario_id=scenario.scenario_id,
                decision=decision,
                reason=reason,
                core_input=core_input,
                core_surface=result.surface,
                core_refusal_reason=result.refusal_reason,
                trace_hash=result.trace_hash,
                versor_condition=float(result.versor_condition),
                ctp_message_id=terminal.message_id,
            )
        )

    verify_chain(tuple(JsonlEventReader(trace_path)))
    return tuple(records)


def run_demo(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    scenarios = _load_scenarios()
    trace_a = output_dir / "trace_a.jsonl"
    trace_b = output_dir / "trace_b.jsonl"
    records_a = _run_once(scenarios, trace_a)
    records_b = _run_once(scenarios, trace_b)

    byte_identical_replay = trace_a.read_bytes() == trace_b.read_bytes()
    if not byte_identical_replay:
        raise RuntimeError("fresh-runtime replay traces were not byte-identical")
    if records_a != records_b:
        raise RuntimeError("fresh-runtime decision records diverged")

    decisions = [r.decision for r in records_a]
    payload = {
        "demo_id": "amr_decision_substrate",
        "scope": {
            "core_role": "decision/refusal/replay accountability substrate",
            "not_claimed": [
                "perception",
                "SLAM/localization",
                "motion planning",
                "motor control",
                "robot fleet integration",
            ],
            "input_kind": "simulated abstract AMR situation records",
        },
        "claims": {
            "bounded_decision_domain": sorted(set(decisions)) == ["PROCEED", "REFUSE", "STOP"],
            "refuse_path_present": "REFUSE" in decisions,
            "byte_identical_replay": byte_identical_replay,
            "all_versors_closed": all(r.versor_condition < 1e-6 for r in records_a),
        },
        "records": [asdict(r) for r in records_a],
        "trace_a_sha256": hashlib.sha256(trace_a.read_bytes()).hexdigest(),
        "trace_b_sha256": hashlib.sha256(trace_b.read_bytes()).hexdigest(),
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_bytes(canonical_bytes(payload))
    return payload


def main() -> int:
    payload = run_demo()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
