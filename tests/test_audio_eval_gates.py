"""
ADR-0181 PR-4 — audio compiler eval gate table.

Implements the acceptance gates that lift `audio_core_v1` from gate-closed to
gate-engaged (eval plan §2). Each fixture is a deterministic synthesis spec
with a *predicted* parse, so the gates grade parser semantics as well as
determinism.

Gate → assertion:
  projection shape            -> exactly (32,)
  projection dtype            -> exactly float32
  compiler replay             -> bit-identical within a run
  versor_condition            -> < 1e-6
  canonical checksum stability-> canonical_sha256 == frozen pin (int/cast-stable)
  IR replay                   -> compile_ir versor equal + ir_sha256 == frozen
  cross-platform stability    -> versor within atol=1e-6 of reference (float-safe)
  semantic structure          -> event_type_counts == frozen pin (parser accuracy)
  trace hygiene               -> no PCM in the evidence trace
  gate closure                -> closed pack refuses projection

The int-derived pins (ir_sha256, event_type_counts, canonical_sha256) are
asserted hard cross-platform; the float versor is compared within tolerance
(eval plan: "cross-platform stability — equal within declared numeric
tolerance"). Regenerate pins with
``uv run python -m evals.audio_sensorium.generate_expected``.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from evals.audio_sensorium.synth import synthesize
from sensorium.audio.canonical import canonicalize
from sensorium.audio.compiler import AudioCompiler
from sensorium.audio.trace import audio_evidence_trace
from sensorium.audio.types import AudioIR
from sensorium.adapters.audio import make_audio_pack

_EVAL_DIR = Path("evals/audio_sensorium")
SR = 24_000
TOL = 1e-6


def _load_fixtures() -> list[dict]:
    return json.loads((_EVAL_DIR / "fixtures.json").read_text())["fixtures"]


def _load_expected_ir() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in (_EVAL_DIR / "expected_ir.jsonl").read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["id"]] = row
    return out


def _load_expected_projection() -> dict[str, dict]:
    return json.loads((_EVAL_DIR / "expected_projection.json").read_text())


FIXTURES = _load_fixtures()
EXPECTED_IR = _load_expected_ir()
EXPECTED_PROJ = _load_expected_projection()
IDS = [fx["id"] for fx in FIXTURES]


def _event_type_counts(ir: AudioIR) -> dict[str, int]:
    events = (
        *ir.speech_spans, *ir.pause_spans, *ir.prosody_arcs,
        *ir.turn_events, *ir.non_speech_events, *ir.content_anchors,
    )
    return dict(sorted(Counter(e.event_type for e in events).items()))


@pytest.fixture(scope="module")
def compiler() -> AudioCompiler:
    return AudioCompiler()


@pytest.mark.parametrize("fx", FIXTURES, ids=IDS)
def test_gate_table(fx, compiler):
    signal = canonicalize(synthesize(fx), SR)
    unit = compiler.compile_signal(signal)
    fid = fx["id"]

    # shape / dtype
    assert unit.versor.shape == (32,)
    assert unit.versor.dtype == np.float32

    # versor condition (A-5)
    assert unit.versor_condition < TOL

    # compiler replay — bit-identical within a run (A-1)
    again = compiler.compile_signal(canonicalize(synthesize(fx), SR))
    assert np.array_equal(unit.versor, again.versor)
    assert unit.merge_key == again.merge_key

    # canonical checksum stability (int/cast-stable pin)
    assert unit.canonical_sha256 == EXPECTED_IR[fid]["canonical_sha256"]

    # IR replay + frozen ir_sha256
    replay = compiler.compile_ir(unit.audio_ir)
    assert np.array_equal(unit.versor, replay.versor)
    assert unit.ir_sha256 == replay.ir_sha256 == EXPECTED_IR[fid]["ir_sha256"]

    # semantic structure — the parser-accuracy gate
    assert _event_type_counts(unit.audio_ir) == EXPECTED_IR[fid]["event_type_counts"]

    # cross-platform projection stability — within tolerance of the reference
    reference = np.asarray(EXPECTED_PROJ[fid]["reference_versor"], dtype=np.float32)
    assert np.allclose(unit.versor, reference, atol=TOL)


@pytest.mark.parametrize("fx", FIXTURES, ids=IDS)
def test_trace_hygiene_no_pcm(fx, compiler):
    unit = compiler.compile_signal(canonicalize(synthesize(fx), SR))
    trace = audio_evidence_trace(unit)
    for value in trace.values():
        assert not isinstance(value, (np.ndarray, bytes, bytearray))
    assert "samples" not in trace


def test_gate_closure_refuses_projection():
    """A gate-closed pack refuses to project (eval plan: gate closure)."""
    from sensorium.registry import ModalityRegistry
    sig = canonicalize(synthesize(FIXTURES[1]), SR)
    reg = ModalityRegistry()
    reg.mount(make_audio_pack("audio_core_v1"), sample=sig)
    with pytest.raises(RuntimeError, match="gate is not engaged"):
        reg.project("audio_core_v1", sig)


def test_semantic_expectations_match_designed_fixtures():
    """Guard the fixture design intent: the frozen event_type_counts must match
    what each fixture's 'expect' note describes (rise/fall/pause/noise)."""
    must_contain = {
        "silence_500ms": {"pause.long", "turn.boundary"},
        "rise_question": {"speech.voiced", "prosody.rise"},
        "fall_statement": {"speech.voiced", "prosody.fall"},
        "noise_burst": {"nonspeech.noise"},
        "speech_then_pause": {"speech.voiced", "pause.long", "turn.boundary"},
    }
    for fid, required in must_contain.items():
        assert required <= set(EXPECTED_IR[fid]["event_type_counts"]), fid
