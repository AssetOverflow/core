from __future__ import annotations

import builtins
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from sensorium.environment import (
    ObservationUnitRef,
    build_expected_observation_frame,
    build_observation_frame,
    compare_expected_to_observation,
)


@dataclass(frozen=True, slots=True)
class _Unit:
    canonical_sha256: str
    ir_sha256: str
    pack_id: str
    pack_manifest_sha256: str
    projection_sha256: str
    versor: np.ndarray
    versor_condition: float = 0.0

    @property
    def merge_key(self) -> tuple[str, str, str]:
        return (self.canonical_sha256, self.ir_sha256, self.projection_sha256)


def _unit(name: str, pack_id: str = "vision_core_v1") -> _Unit:
    v = np.zeros(32, dtype=np.float32)
    v[0] = 1.0
    return _Unit(name, f"ir-{name}", pack_id, "manifest", f"proj-{name}", v)


def _ref(slot: str, name: str, pack_id: str = "vision_core_v1") -> ObservationUnitRef:
    return ObservationUnitRef(slot, _unit(name, pack_id))


def test_adr_0211_contract_is_documented():
    root = Path(__file__).resolve().parents[1]
    adr = root / "docs" / "decisions" / "ADR-0211-conformal-falsification-bench.md"
    runtime = root / "docs" / "runtime_contracts.md"
    assert adr.exists()
    adr_text = adr.read_text(encoding="utf-8")
    runtime_text = runtime.read_text(encoding="utf-8")
    assert "`ObservationFrame` remains afferent-only evidence" in adr_text
    assert "SUPPORTED" in adr_text
    assert "FALSIFIED" in adr_text
    assert "Environmental falsification contract (ADR-0211)" in runtime_text


def test_expected_frame_hash_is_order_invariant_and_duplicate_safe():
    a = _ref("slot:a", "a")
    b = _ref("slot:b", "b")
    f1 = build_expected_observation_frame(
        monotonic_tick=1,
        source_clock="fixture",
        unit_refs=(a, b, a),
    )
    f2 = build_expected_observation_frame(
        monotonic_tick=1,
        source_clock="fixture",
        unit_refs=(b, a),
    )
    assert f1.expected_sha256 == f2.expected_sha256
    assert f1.expected_id == f2.expected_id
    assert len(f1.unit_refs) == 2


def test_raw_payloads_are_rejected():
    @dataclass(frozen=True, slots=True)
    class BadUnit(_Unit):
        pixels: bytes = b"raw"

    with pytest.raises(TypeError, match="unsafe environmental evidence payload"):
        ObservationUnitRef(
            "bad",
            BadUnit("a", "ir-a", "vision_core_v1", "manifest", "proj-a", np.zeros(32, dtype=np.float32)),
        )


def test_efferent_and_motor_units_are_rejected():
    @dataclass(frozen=True, slots=True)
    class ActionUnit(_Unit):
        efferent: bool = True

    with pytest.raises(ValueError, match="efferent"):
        ObservationUnitRef(
            "action",
            ActionUnit("m", "ir-m", "motor_test", "manifest", "proj-m", np.zeros(32, dtype=np.float32)),
        )
    with pytest.raises(ValueError, match="motor"):
        ObservationUnitRef("motor", _unit("m", "motor_test"))


def test_exact_expected_vs_actual_match_is_supported():
    refs = (_ref("slot:a", "a"), _ref("slot:b", "b"))
    expected = build_expected_observation_frame(
        monotonic_tick=2,
        source_clock="fixture",
        unit_refs=refs,
    )
    actual = build_observation_frame(
        monotonic_tick=2,
        source_clock="fixture",
        units=[ref.unit for ref in refs],
    )
    run = compare_expected_to_observation(expected, actual, actual_refs=refs)
    assert run.verdict == "SUPPORTED"
    assert run.residual.matched == ("slot:a", "slot:b")
    assert run.residual.missing == ()
    assert run.residual.unexpected == ()
    assert run.residual.changed == ()


def test_missing_unexpected_and_changed_slots_are_falsified():
    expected_refs = (
        _ref("slot:a", "a"),
        _ref("slot:b", "b"),
        _ref("slot:c", "c"),
    )
    actual_refs = (
        _ref("slot:a", "a"),
        _ref("slot:b", "b2"),
        _ref("slot:d", "d"),
    )
    expected = build_expected_observation_frame(
        monotonic_tick=3,
        source_clock="fixture",
        unit_refs=expected_refs,
    )
    actual = build_observation_frame(
        monotonic_tick=3,
        source_clock="fixture",
        units=[ref.unit for ref in actual_refs],
    )
    run = compare_expected_to_observation(expected, actual, actual_refs=actual_refs)
    assert run.verdict == "FALSIFIED"
    assert run.residual.matched == ("slot:a",)
    assert run.residual.missing == ("slot:c",)
    assert run.residual.unexpected == ("slot:d",)
    assert len(run.residual.changed) == 1
    assert run.residual.changed[0].slot_id == "slot:b"


def test_run_trace_is_hash_only():
    refs = (_ref("slot:a", "a"),)
    expected = build_expected_observation_frame(
        monotonic_tick=4,
        source_clock="fixture",
        unit_refs=refs,
    )
    actual = build_observation_frame(
        monotonic_tick=4,
        source_clock="fixture",
        units=[ref.unit for ref in refs],
    )
    payload = compare_expected_to_observation(expected, actual, actual_refs=refs).as_dict()
    assert "versor" not in str(payload)
    assert "pixels" not in str(payload)
    assert "command" not in str(payload)


def test_comparator_does_not_import_generate_or_call_decode(monkeypatch):
    refs = (_ref("slot:a", "a"),)
    expected = build_expected_observation_frame(
        monotonic_tick=5,
        source_clock="fixture",
        unit_refs=refs,
    )
    actual = build_observation_frame(
        monotonic_tick=5,
        source_clock="fixture",
        units=[ref.unit for ref in refs],
    )
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.startswith("generate"):
            raise AssertionError("falsification comparator must not import generate")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    from sensorium.registry import ModalityRegistry

    monkeypatch.setattr(
        ModalityRegistry,
        "decode",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("decode called")),
    )
    run = compare_expected_to_observation(expected, actual, actual_refs=refs)
    assert run.verdict == "SUPPORTED"
