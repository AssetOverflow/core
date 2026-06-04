"""Deterministic sensorium eval reports for modality compiler lanes."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Literal

import numpy as np

from evals.audio_sensorium.synth import synthesize as synthesize_audio
from evals.sensorimotor_sensorium.synth import synthesize as synthesize_sensorimotor
from evals.vision_sensorium.synth import synthesize as synthesize_vision
from sensorium.adapters.audio import make_audio_pack
from sensorium.adapters.sensorimotor import make_sensorimotor_pack
from sensorium.adapters.vision import make_vision_pack
from sensorium.audio.canonical import canonicalize as canonicalize_audio
from sensorium.audio.compiler import AudioCompiler
from sensorium.audio.trace import audio_evidence_trace
from sensorium.audio.types import AudioIR
from sensorium.registry import ModalityRegistry
from sensorium.sensorimotor import SensorimotorCompiler, sensorimotor_evidence_trace
from sensorium.vision import VisionCompiler, canonicalize_image, vision_evidence_trace
from sensorium.vision.grid import iter_tile_signals
from sensorium.vision.types import VisionIR

ModalityName = Literal["audio", "vision", "sensorimotor"]
_ROOT = Path(__file__).resolve().parents[2]
_AUDIO_DIR = _ROOT / "evals" / "audio_sensorium"
_VISION_DIR = _ROOT / "evals" / "vision_sensorium"
_SENSORIMOTOR_DIR = _ROOT / "evals" / "sensorimotor_sensorium"
_AUDIO_SR = 24_000
_TOL = 1e-6


def _json(path: Path):
    return json.loads(path.read_text())


def _jsonl_by_id(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in path.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["id"]] = row
    return out


def _audio_counts(ir: AudioIR) -> dict[str, int]:
    events = (
        *ir.speech_spans,
        *ir.pause_spans,
        *ir.prosody_arcs,
        *ir.turn_events,
        *ir.non_speech_events,
        *ir.content_anchors,
    )
    return dict(sorted(Counter(e.event_type for e in events).items()))


def _vision_counts(ir: VisionIR) -> dict[str, int]:
    events = (
        *ir.regions,
        *ir.contour_arcs,
        *ir.orient_events,
        *ir.texture_atoms,
        *ir.salient_events,
        *ir.content_anchors,
    )
    return dict(sorted(Counter(e.event_type for e in events).items()))


def _trace_safe(trace: dict[str, object]) -> bool:
    return all(not isinstance(value, (np.ndarray, bytes, bytearray)) for value in trace.values())


def _audio_report() -> dict[str, object]:
    fixtures = _json(_AUDIO_DIR / "fixtures.json")["fixtures"]
    expected_ir = _jsonl_by_id(_AUDIO_DIR / "expected_ir.jsonl")
    expected_proj = _json(_AUDIO_DIR / "expected_projection.json")
    compiler = AudioCompiler()
    cases: list[dict[str, object]] = []
    for fx in fixtures:
        fid = fx["id"]
        unit = compiler.compile_signal(canonicalize_audio(synthesize_audio(fx), _AUDIO_SR))
        replay = compiler.compile_ir(unit.audio_ir)
        ref = np.asarray(expected_proj[fid]["reference_versor"], dtype=np.float32)
        cases.append({
            "id": fid,
            "canonical_sha256": unit.canonical_sha256,
            "ir_sha256": unit.ir_sha256,
            "projection_sha256": unit.projection_sha256,
            "shape_ok": unit.versor.shape == (32,),
            "dtype_ok": unit.versor.dtype == np.float32,
            "replay_ok": bool(np.array_equal(unit.versor, replay.versor)),
            "expected_ir_ok": unit.ir_sha256 == expected_ir[fid]["ir_sha256"],
            "expected_projection_ok": bool(np.allclose(unit.versor, ref, atol=_TOL)),
            "event_counts_ok": _audio_counts(unit.audio_ir) == expected_ir[fid]["event_type_counts"],
            "trace_hygiene_ok": _trace_safe(audio_evidence_trace(unit)),
            "versor_condition": unit.versor_condition,
        })
    reg = ModalityRegistry()
    sample = canonicalize_audio(synthesize_audio(fixtures[0]), _AUDIO_SR)
    reg.mount(make_audio_pack("audio_core_v1"), sample=sample)
    gate_closed = False
    try:
        reg.project("audio_core_v1", sample)
    except RuntimeError:
        gate_closed = True
    return _report("audio", "audio_core_v1", cases, gate_closed)


def _vision_report() -> dict[str, object]:
    fixtures = _json(_VISION_DIR / "fixtures.json")["fixtures"]
    expected_ir = _jsonl_by_id(_VISION_DIR / "expected_ir.jsonl")
    expected_proj = _json(_VISION_DIR / "expected_projection.json")
    compiler = VisionCompiler()
    cases: list[dict[str, object]] = []
    for fx in fixtures:
        fid = fx["id"]
        image = canonicalize_image(synthesize_vision(fx))
        units = compiler.compile_image(image)
        counts = Counter()
        units_ok = True
        projection_ok = True
        trace_ok = True
        for idx, unit in enumerate(units):
            replay = compiler.compile_ir(unit.vision_ir)
            units_ok = units_ok and unit.versor.shape == (32,) and unit.versor.dtype == np.float32
            units_ok = units_ok and np.array_equal(unit.versor, replay.versor)
            ref = np.asarray(expected_proj[fid][idx]["reference_versor"], dtype=np.float32)
            projection_ok = projection_ok and unit.projection_sha256 == expected_proj[fid][idx]["projection_sha256"]
            projection_ok = projection_ok and np.allclose(unit.versor, ref, atol=_TOL)
            trace_ok = trace_ok and _trace_safe(vision_evidence_trace(unit))
            counts.update(_vision_counts(unit.vision_ir))
        cases.append({
            "id": fid,
            "canonical_sha256": image.canonical_sha256,
            "unit_count": len(units),
            "unit_count_ok": len(units) == expected_ir[fid]["unit_count"],
            "units_ok": bool(units_ok),
            "expected_projection_ok": bool(projection_ok),
            "event_counts_ok": dict(sorted(counts.items())) == expected_ir[fid]["event_type_counts"],
            "trace_hygiene_ok": bool(trace_ok),
        })
    reg = ModalityRegistry()
    sample = iter_tile_signals(canonicalize_image(synthesize_vision(fixtures[0])))[0]
    reg.mount(make_vision_pack("vision_core_v1"), sample=sample)
    gate_closed = False
    try:
        reg.project("vision_core_v1", sample)
    except RuntimeError:
        gate_closed = True
    return _report("vision", "vision_core_v1", cases, gate_closed)


def _sensorimotor_report() -> dict[str, object]:
    fixtures = _json(_SENSORIMOTOR_DIR / "fixtures.json")["fixtures"]
    expected_ir = _jsonl_by_id(_SENSORIMOTOR_DIR / "expected_ir.jsonl")
    expected_proj = _json(_SENSORIMOTOR_DIR / "expected_projection.json")
    compiler = SensorimotorCompiler()
    cases: list[dict[str, object]] = []
    for fx in fixtures:
        fid = fx["id"]
        unit = compiler.compile_signal(synthesize_sensorimotor(fx))
        replay = compiler.compile_ir(unit.sensorimotor_ir)
        ref = np.asarray(expected_proj[fid]["reference_versor"], dtype=np.float32)
        cases.append({
            "id": fid,
            "canonical_sha256": unit.canonical_sha256,
            "ir_sha256": unit.ir_sha256,
            "projection_sha256": unit.projection_sha256,
            "shape_ok": unit.versor.shape == (32,),
            "dtype_ok": unit.versor.dtype == np.float32,
            "replay_ok": bool(np.array_equal(unit.versor, replay.versor)),
            "expected_ir_ok": unit.ir_sha256 == expected_ir[fid]["ir_sha256"],
            "expected_projection_ok": bool(np.allclose(unit.versor, ref, atol=_TOL)),
            "event_types_ok": [e.event_type for e in unit.sensorimotor_ir.events] == expected_ir[fid]["event_types"],
            "trace_hygiene_ok": _trace_safe(sensorimotor_evidence_trace(unit)),
            "versor_condition": unit.versor_condition,
        })
    reg = ModalityRegistry()
    sample = synthesize_sensorimotor(fixtures[0])
    reg.mount(make_sensorimotor_pack("sensorimotor_core_v1"), sample=sample)
    gate_closed = False
    try:
        reg.project("sensorimotor_core_v1", sample)
    except RuntimeError:
        gate_closed = True
    return _report("sensorimotor", "sensorimotor_core_v1", cases, gate_closed)


def _report(modality: str, pack_id: str, cases: list[dict[str, object]], gate_closed: bool) -> dict[str, object]:
    pass_count = sum(
        1 for case in cases
        if all(value is True for key, value in case.items() if key.endswith("_ok"))
    )
    return {
        "lane": "sensorium",
        "modality": modality,
        "pack_id": pack_id,
        "gate_engaged": False,
        "gate_closed": gate_closed,
        "total": len(cases),
        "passed": pass_count,
        "failed": len(cases) - pass_count,
        "cases": cases,
    }


def build_sensorium_report(modality: ModalityName) -> dict[str, object]:
    if modality == "audio":
        return _audio_report()
    if modality == "vision":
        return _vision_report()
    if modality == "sensorimotor":
        return _sensorimotor_report()
    raise ValueError(f"unsupported sensorium modality: {modality!r}")
