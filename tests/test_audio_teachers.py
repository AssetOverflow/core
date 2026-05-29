"""
ADR-0181 PR-6 — teacher / shadow lane proof obligations.

The load-bearing rule (eval-plan §4): teachers label or align, they NEVER define
the substrate. The structural guarantee is that admitting any teacher hint leaves
the **versor and `projection_sha256` byte-identical** — a hint adds IR evidence
(`content_anchors`) and moves only `ir_sha256`, never the geometry that crosses
the ProjectionHead boundary.

Per CLAUDE.md §Schema-Defined Proof Obligations, the tests FAIL LOUDLY under the
violation each names: if a teacher anchor ever lowered to a rotor (e.g. attached
under an operator category instead of `content.*`), the substrate-invariance test
breaks; if `attach_teacher_hints` silently dropped hints, the evidence-recorded
test breaks.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from evals.audio_sensorium.synth import synthesize
from sensorium.audio.canonical import canonicalize
from sensorium.audio.compiler import AudioCompiler
from sensorium.audio.operators import DEFAULT_OPERATOR_REGISTRY
from sensorium.audio.parser import ir_sha256_of
from sensorium.audio.teachers import (
    KNOWN_TEACHER_LANES,
    StubTranscriptTeacher,
    TeacherHint,
    TeacherUnavailable,
    attach_teacher_hints,
    is_lane_available,
    load_teacher,
)

SR = 24_000
_EVAL_DIR = Path("evals/audio_sensorium")


def _fixtures() -> list[dict]:
    return json.loads((_EVAL_DIR / "fixtures.json").read_text())["fixtures"]


@pytest.fixture(scope="module")
def compiler() -> AudioCompiler:
    return AudioCompiler()


@pytest.fixture(scope="module")
def signal():
    # a voiced fixture so the base versor is non-trivial (real rotors fold in)
    fx = next(f for f in _fixtures() if f["id"] == "rise_question")
    return canonicalize(synthesize(fx), SR)


@pytest.fixture
def base_unit(compiler, signal):
    return compiler.compile_signal(signal)


@pytest.fixture
def hints(signal):
    return StubTranscriptTeacher().annotate(signal)


# --- the load-bearing rule: teachers never define the substrate ------------


def test_teacher_hint_does_not_change_versor(compiler, base_unit, hints):
    augmented_ir = attach_teacher_hints(base_unit.audio_ir, hints)
    taught = compiler.compile_ir(augmented_ir)

    # substrate is invariant to the teacher
    assert np.array_equal(base_unit.versor, taught.versor)
    assert base_unit.projection_sha256 == taught.projection_sha256
    assert taught.versor_condition < 1e-6


def test_teacher_hint_is_recorded_as_evidence(compiler, base_unit, hints):
    augmented_ir = attach_teacher_hints(base_unit.audio_ir, hints)
    taught = compiler.compile_ir(augmented_ir)

    # evidence is recorded => ir_sha256 (and only the ir leg of merge_key) moves
    assert taught.ir_sha256 != base_unit.ir_sha256
    assert taught.merge_key != base_unit.merge_key
    assert taught.merge_key[2] == base_unit.merge_key[2]  # projection leg unchanged
    assert len(augmented_ir.content_anchors) == len(hints)


def test_teacher_anchors_carry_no_operator(base_unit, hints):
    """Structural guarantee: content.* anchors are not operator keys, so
    compile_events skips them (no rotor)."""
    augmented_ir = attach_teacher_hints(base_unit.audio_ir, hints)
    for anchor in augmented_ir.content_anchors:
        assert anchor.event_type.startswith("content.")
        assert anchor.event_type not in DEFAULT_OPERATOR_REGISTRY


def test_attach_is_immutable(base_unit, hints):
    original_anchors = base_unit.audio_ir.content_anchors
    original_sha = base_unit.audio_ir.ir_sha256
    _ = attach_teacher_hints(base_unit.audio_ir, hints)
    assert base_unit.audio_ir.content_anchors == original_anchors
    assert base_unit.audio_ir.ir_sha256 == original_sha


def test_attach_empty_is_noop(base_unit):
    assert attach_teacher_hints(base_unit.audio_ir, ()) is base_unit.audio_ir


# --- ir_sha256_of refactor regression guard --------------------------------


def test_ir_sha256_of_matches_parse(base_unit):
    # the extracted hash function must reproduce what parse() stored
    assert ir_sha256_of(base_unit.audio_ir) == base_unit.ir_sha256


def test_attached_ir_sha_is_recomputable(base_unit, hints):
    augmented = attach_teacher_hints(base_unit.audio_ir, hints)
    assert ir_sha256_of(augmented) == augmented.ir_sha256


# --- hint typing / versioning / checksum -----------------------------------


def test_hint_is_versioned_and_checksummed():
    a = TeacherHint.make(
        lane_id="x", lane_version="v1", hint_type="transcript",
        start_hop=0, end_hop=5, payload=(("token", "abcd"),), confidence_q=100,
    )
    same = TeacherHint.make(
        lane_id="x", lane_version="v1", hint_type="transcript",
        start_hop=0, end_hop=5, payload=(("token", "abcd"),), confidence_q=100,
    )
    diff = TeacherHint.make(
        lane_id="x", lane_version="v1", hint_type="transcript",
        start_hop=0, end_hop=5, payload=(("token", "WXYZ"),), confidence_q=100,
    )
    assert a.hint_sha256 == same.hint_sha256          # content-addressed, stable
    assert a.hint_sha256 != diff.hint_sha256          # changes with payload
    assert a.evidence_id == f"x:v1:{a.hint_sha256}"


def test_stub_teacher_is_deterministic(signal):
    t = StubTranscriptTeacher()
    assert t.annotate(signal)[0].hint_sha256 == t.annotate(signal)[0].hint_sha256


# --- lane registry: declared, gated, graceful ------------------------------


def test_known_lanes_match_eval_plan():
    assert set(KNOWN_TEACHER_LANES) == {"whisper", "nemo", "clap", "encodec"}


def test_load_unknown_lane_raises_value_error():
    with pytest.raises(ValueError, match="unknown teacher lane"):
        load_teacher("does_not_exist")


def test_load_declared_lane_without_adapter_is_unavailable():
    # lanes are declared + gated; no adapter is wired yet -> loud, never silent
    with pytest.raises(TeacherUnavailable):
        load_teacher("whisper")


def test_is_lane_available_does_not_raise():
    # pure probe; returns a bool for known and unknown lanes
    assert isinstance(is_lane_available("whisper"), bool)
    assert is_lane_available("does_not_exist") is False
