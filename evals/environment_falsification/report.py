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
    build_expected_observation_frame,
    build_observation_frame,
    compare_expected_to_observation,
)
from sensorium.sensorimotor.compiler import SensorimotorCompiler
from sensorium.vision import VisionCompiler, canonicalize_image
from sensorium.vision.grid import iter_tile_signals

_ROOT = Path(__file__).resolve().parent
_AUDIO_SR = 24_000


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((_ROOT / name).read_text(encoding="utf-8"))


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


def build_environment_falsification_report() -> dict[str, object]:
    fixtures = _load_json("fixtures.json")["fixtures"]
    cases = [_case_report(idx, case) for idx, case in enumerate(fixtures)]
    passed = sum(
        1
        for case in cases
        if case["verdict_ok"] is True and case["trace_hygiene_ok"] is True
    )
    report = {
        "lane": "environment-falsification",
        "version": "v1",
        "total": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "cases": cases,
    }
    report["report_sha256"] = _report_hash(report)
    expected_hashes = _load_json("expected_hashes.json")
    report["expected_report_sha256"] = expected_hashes["report_sha256"]
    report["expected_report_hash_ok"] = report["report_sha256"] == expected_hashes["report_sha256"]
    if not report["expected_report_hash_ok"]:
        report["failed"] = int(report["failed"]) + 1
    return report


__all__ = ["build_environment_falsification_report"]
