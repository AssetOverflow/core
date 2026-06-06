"""Deterministic environmental falsification replay report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from evals.audio_sensorium.synth import synthesize as synthesize_audio
from evals.sensorimotor_sensorium.synth import synthesize as synthesize_sensorimotor
from evals.vision_sensorium.synth import synthesize as synthesize_vision
from sensorium.audio.canonical import canonicalize as canonicalize_audio
from sensorium.audio.compiler import AudioCompiler
from sensorium.audio.checksum import sha256_json
from sensorium.environment import (
    ObservationUnitRef,
    build_experiment_plan,
    build_expected_observation_frame,
    build_hypothesis_claim,
    build_observation_frame,
    compare_expected_to_observation,
    run_falsification_scenario,
)
from sensorium.logs import import_witness_jsonl, import_witness_records
from sensorium.sensorimotor.compiler import SensorimotorCompiler
from sensorium.vision import VisionCompiler, canonicalize_image
from sensorium.vision.grid import iter_tile_signals

_ROOT = Path(__file__).resolve().parent
_AUDIO_SR = 24_000


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((_ROOT / name).read_text(encoding="utf-8"))


def _load_jsonl(name: str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (_ROOT / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _trace_safe(value: object) -> bool:
    if isinstance(value, (np.ndarray, bytes, bytearray)):
        return False
    if isinstance(value, dict):
        return all(_trace_safe(child) for child in value.values())
    if isinstance(value, (list, tuple)):
        return all(_trace_safe(child) for child in value)
    return True


def _compile_unit(spec: dict[str, Any]):
    modality = spec["modality"]
    signal = spec["signal"]
    if modality == "audio":
        return AudioCompiler().compile_signal(
            canonicalize_audio(synthesize_audio(signal), _AUDIO_SR)
        )
    if modality == "vision":
        image = canonicalize_image(synthesize_vision(signal))
        tile = iter_tile_signals(image)[0]
        return VisionCompiler().compile_tile(tile)
    if modality == "sensorimotor":
        return SensorimotorCompiler().compile_signal(synthesize_sensorimotor(signal))
    raise ValueError(f"unsupported falsification fixture modality: {modality!r}")


def _refs(spec: dict[str, Any]) -> tuple[ObservationUnitRef, ...]:
    return tuple(
        ObservationUnitRef(slot_id=slot_id, unit=_compile_unit(unit_spec))
        for slot_id, unit_spec in sorted(spec.items())
    )


def _actual_spec(case: dict[str, Any]) -> dict[str, Any]:
    actual = case["actual"]
    if actual == "same":
        return case["expected"]
    return actual


def _case_report(index: int, case: dict[str, Any]) -> dict[str, object]:
    expected_refs = _refs(case["expected"])
    actual_refs = _refs(_actual_spec(case))
    expected = build_expected_observation_frame(
        monotonic_tick=index,
        source_clock="environment-falsification-fixture",
        unit_refs=expected_refs,
        causal_parent_ids=(),
    )
    actual = build_observation_frame(
        monotonic_tick=index,
        source_clock="environment-falsification-fixture",
        units=tuple(ref.unit for ref in actual_refs),
        causal_parent_ids=(expected.expected_id,),
    )
    run = compare_expected_to_observation(expected, actual, actual_refs=actual_refs)
    expected_verdict = str(case["expected_verdict"])
    row = {
        "id": case["id"],
        "expected_verdict": expected_verdict,
        "actual_verdict": run.verdict,
        "verdict_ok": run.verdict == expected_verdict,
        "trace_hygiene_ok": _trace_safe(run.as_dict()),
        "expected_sha256": expected.expected_sha256,
        "actual_trace_hash": actual.trace_hash,
        "run_trace_hash": run.trace_hash,
        "residual": run.residual.as_dict(),
    }
    return row


def _report_hash(report_without_hash: dict[str, object]) -> str:
    return sha256_json(report_without_hash)


def _frame_report(cases: list[dict[str, object]]) -> dict[str, object]:
    passed = sum(
        1
        for case in cases
        if case["verdict_ok"] is True and case["trace_hygiene_ok"] is True
    )
    return {
        "lane": "environment-falsification",
        "version": "v1",
        "total": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "cases": cases,
    }


def _scenario_case_report(index: int, scenario: dict[str, Any]) -> dict[str, object]:
    hypothesis_spec = scenario["hypothesis"]
    hypothesis = build_hypothesis_claim(
        claim_id=str(hypothesis_spec["claim_id"]),
        claim_text=str(hypothesis_spec["claim_text"]),
        domain=str(hypothesis_spec["domain"]),
        basis_trace_hashes=tuple(hypothesis_spec.get("basis_trace_hashes", ())),
    )
    expected_frames = []
    actual_frames_by_expected_id = {}
    actual_refs_by_expected_id = {}
    for offset, frame_spec in enumerate(scenario["frames"]):
        tick = int(frame_spec.get("tick", index * 100 + offset))
        expected_refs = _refs(frame_spec["expected"])
        expected = build_expected_observation_frame(
            monotonic_tick=tick,
            source_clock="environment-falsification-scenario-fixture",
            unit_refs=expected_refs,
            causal_parent_ids=tuple(frame_spec.get("causal_parent_ids", ())),
        )
        expected_frames.append(expected)
        if frame_spec["actual"] == "missing":
            continue
        actual_spec = frame_spec["expected"] if frame_spec["actual"] == "same" else frame_spec["actual"]
        actual_refs = _refs(actual_spec)
        actual = build_observation_frame(
            monotonic_tick=tick,
            source_clock="environment-falsification-scenario-fixture",
            units=tuple(ref.unit for ref in actual_refs),
            causal_parent_ids=(expected.expected_id,),
        )
        actual_frames_by_expected_id[expected.expected_id] = actual
        actual_refs_by_expected_id[expected.expected_id] = actual_refs

    plan = build_experiment_plan(hypothesis=hypothesis, expected_frames=expected_frames)
    report = run_falsification_scenario(
        plan,
        actual_frames_by_expected_id=actual_frames_by_expected_id,
        actual_refs_by_expected_id=actual_refs_by_expected_id,
    )
    expected_verdict = str(scenario["expected_verdict"])
    row = {
        "id": scenario["id"],
        "expected_verdict": expected_verdict,
        "actual_verdict": report.verdict,
        "verdict_ok": report.verdict == expected_verdict,
        "trace_hygiene_ok": _trace_safe(report.as_dict()),
        "hypothesis_sha256": hypothesis.hypothesis_sha256,
        "plan_sha256": plan.plan_sha256,
        "scenario_sha256": report.scenario_sha256,
        "scenario_report_sha256": report.report_sha256,
        "total_count": report.total_count,
        "supported_count": report.supported_count,
        "falsified_count": report.falsified_count,
        "run_trace_hashes": [run.trace_hash for run in report.runs],
    }
    return row


def _witness_import_report() -> dict[str, object]:
    payloads = _load_json("witness_payloads.json")["payloads"]

    def resolve(payload_ref: str):
        return _compile_unit(payloads[payload_ref])

    path = _ROOT / "witness_log.jsonl"
    imported = import_witness_jsonl(path, resolve_payload_ref=resolve)
    repeated = import_witness_jsonl(path, resolve_payload_ref=resolve)
    rows = _load_jsonl("witness_log.jsonl")
    permuted = import_witness_records(reversed(rows), resolve_payload_ref=resolve)
    trace = imported.as_dict()
    frame_trace_hashes = [frame.trace_hash for frame in imported.frames]
    return {
        "id": "jsonl_witness_import",
        "record_count": imported.manifest.record_count,
        "frame_count": len(imported.frames),
        "trace_hash": imported.trace_hash,
        "manifest_sha256": imported.manifest.manifest_sha256,
        "frame_trace_hashes": frame_trace_hashes,
        "deterministic_reimport_ok": imported.trace_hash == repeated.trace_hash,
        "order_stability_ok": imported.trace_hash == permuted.trace_hash,
        "trace_hygiene_ok": _trace_safe(trace) and "pixels" not in str(trace) and "action_trace" not in str(trace),
        "no_actuation_ok": all(
            not unit.pack_id.startswith("motor")
            for frame in imported.frames
            for unit in frame.units
        ),
    }


def build_environment_falsification_report() -> dict[str, object]:
    fixtures = _load_json("fixtures.json")["fixtures"]
    cases = [_case_report(idx, case) for idx, case in enumerate(fixtures)]
    frame_report = _frame_report(cases)
    frame_report_sha256 = _report_hash(frame_report)
    scenario_fixtures = _load_json("scenario_fixtures.json")["scenarios"]
    scenario_cases = [
        _scenario_case_report(idx, scenario)
        for idx, scenario in enumerate(scenario_fixtures)
    ]
    scenario_passed = sum(
        1
        for case in scenario_cases
        if case["verdict_ok"] is True and case["trace_hygiene_ok"] is True
    )
    witness_import = _witness_import_report()
    witness_ok = all(
        witness_import[key] is True
        for key in (
            "deterministic_reimport_ok",
            "order_stability_ok",
            "trace_hygiene_ok",
            "no_actuation_ok",
        )
    )
    frame_passed = int(frame_report["passed"])
    frame_failed = int(frame_report["failed"])
    total = len(cases) + len(scenario_cases) + 1
    passed = frame_passed + scenario_passed + (1 if witness_ok else 0)
    report = {
        "lane": "environment-falsification",
        "version": "v1",
        "total": total,
        "passed": passed,
        "failed": frame_failed + (len(scenario_cases) - scenario_passed) + (0 if witness_ok else 1),
        "cases": cases,
        "frame_report_sha256": frame_report_sha256,
        "scenario_cases": scenario_cases,
        "witness_import": witness_import,
    }
    report["report_sha256"] = _report_hash(report)
    expected_hashes = _load_json("expected_hashes.json")
    expected_frame_report_sha256 = expected_hashes.get(
        "frame_report_sha256",
        expected_hashes["report_sha256"],
    )
    report["expected_frame_report_sha256"] = expected_frame_report_sha256
    report["expected_frame_report_hash_ok"] = frame_report_sha256 == expected_frame_report_sha256
    report["expected_report_sha256"] = expected_hashes["report_sha256"]
    report["expected_report_hash_ok"] = report["report_sha256"] == expected_hashes["report_sha256"]
    if not report["expected_frame_report_hash_ok"]:
        report["failed"] = int(report["failed"]) + 1
    if not report["expected_report_hash_ok"]:
        report["failed"] = int(report["failed"]) + 1
    return report


__all__ = ["build_environment_falsification_report"]
