from __future__ import annotations

import builtins
import json
from dataclasses import dataclass

import numpy as np
import pytest

from sensorium.logs import import_witness_jsonl, import_witness_records


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


def _resolver(ref: str):
    return _unit(ref)


def _rows():
    return [
        {
            "tick": 2,
            "source_clock": "fixture",
            "modality": "vision",
            "slot_id": "vision:anchor",
            "payload_ref": "vision_anchor",
        },
        {
            "tick": 1,
            "source_clock": "fixture",
            "modality": "sensorimotor",
            "slot_id": "sensorimotor:contact",
            "payload_ref": "contact_anchor",
        },
    ]


def test_witness_import_is_order_stable_and_trace_safe():
    first = import_witness_records(_rows(), resolve_payload_ref=_resolver)
    second = import_witness_records(reversed(_rows()), resolve_payload_ref=_resolver)
    assert first.trace_hash == second.trace_hash
    assert [frame.monotonic_tick for frame in first.frames] == [1, 2]
    payload = first.as_dict()
    assert "vision_anchor" not in str(payload)
    assert "versor" not in str(payload)
    assert "pixels" not in str(payload)
    assert "action_trace" not in str(payload)


def test_witness_jsonl_import_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="path traversal"):
        import_witness_jsonl(tmp_path / ".." / "witness.jsonl", resolve_payload_ref=_resolver)


def test_witness_import_rejects_raw_payload_and_live_handles():
    bad_raw = dict(_rows()[0])
    bad_raw["pixels"] = [1, 2, 3]
    with pytest.raises(ValueError, match="raw payload"):
        import_witness_records([bad_raw], resolve_payload_ref=_resolver)

    bad_live = dict(_rows()[0])
    bad_live["socket"] = "localhost:11311"
    with pytest.raises(ValueError, match="live device"):
        import_witness_records([bad_live], resolve_payload_ref=_resolver)


def test_witness_jsonl_repeated_import_is_identical(tmp_path):
    path = tmp_path / "witness.jsonl"
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in _rows()) + "\n")
    first = import_witness_jsonl(path, resolve_payload_ref=_resolver)
    second = import_witness_jsonl(path, resolve_payload_ref=_resolver)
    assert first.trace_hash == second.trace_hash
    assert first.manifest.manifest_sha256 == second.manifest.manifest_sha256


def test_witness_jsonl_rejects_malformed_json_line(tmp_path):
    path = tmp_path / "witness.jsonl"
    good = json.dumps(_rows()[0], sort_keys=True)
    path.write_text(good + "\n{ this is not json\n")
    with pytest.raises(ValueError, match="line 2: malformed JSON"):
        import_witness_jsonl(path, resolve_payload_ref=_resolver)


def test_witness_record_missing_field_is_clean_value_error():
    bad = dict(_rows()[0])
    del bad["payload_ref"]
    with pytest.raises(ValueError, match="missing required field: payload_ref"):
        import_witness_records([bad], resolve_payload_ref=_resolver)


def test_witness_record_non_object_is_rejected():
    with pytest.raises(ValueError, match="must be a JSON object"):
        import_witness_records([[1, 2, 3]], resolve_payload_ref=_resolver)


def test_witness_record_non_integer_tick_is_clean_value_error():
    bad = dict(_rows()[0])
    bad["tick"] = "not-an-int"
    with pytest.raises(ValueError, match="tick must be an integer"):
        import_witness_records([bad], resolve_payload_ref=_resolver)


def test_witness_jsonl_rejects_oversized_log(tmp_path, monkeypatch):
    from sensorium.logs import importer as _importer

    monkeypatch.setattr(_importer, "_MAX_WITNESS_LOG_BYTES", 8)
    path = tmp_path / "witness.jsonl"
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in _rows()) + "\n")
    with pytest.raises(ValueError, match="witness log too large"):
        import_witness_jsonl(path, resolve_payload_ref=_resolver)


def test_witness_importer_does_not_import_generate_or_call_decode(monkeypatch):
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.startswith("generate"):
            raise AssertionError("witness importer must not import generate")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    from sensorium.registry import ModalityRegistry

    monkeypatch.setattr(
        ModalityRegistry,
        "decode",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("decode called")),
    )
    imported = import_witness_records(_rows(), resolve_payload_ref=_resolver)
    assert len(imported.frames) == 2
