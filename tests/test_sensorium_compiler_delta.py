from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from sensorium.compiler import ContentAddressedDelta, merge_deltas, merge_trace_hash


@dataclass(frozen=True, slots=True)
class _Unit:
    canonical_sha256: str
    ir_sha256: str
    pack_id: str
    pack_manifest_sha256: str
    projection_sha256: str
    versor: np.ndarray
    versor_condition: float

    @property
    def merge_key(self) -> tuple[str, str, str]:
        return (self.canonical_sha256, self.ir_sha256, self.projection_sha256)


def _unit(name: str) -> _Unit:
    v = np.zeros(32, dtype=np.float32)
    v[0] = 1.0
    return _Unit(name, f"ir-{name}", "pack", "manifest", f"proj-{name}", v, 0.0)


def _trace(unit: _Unit) -> dict[str, object]:
    return {"merge_key": list(unit.merge_key), "pack_id": unit.pack_id}


def test_content_addressed_delta_is_canonical_and_idempotent():
    a, b, c = _unit("a"), _unit("b"), _unit("c")
    delta = ContentAddressedDelta.from_units([c, a, b, a])
    assert delta.merge_keys == (a.merge_key, b.merge_key, c.merge_key)
    assert len(delta) == 3


def test_join_is_commutative_associative_and_merge_equivalent():
    a, b, c = _unit("a"), _unit("b"), _unit("c")
    da = ContentAddressedDelta.from_units([a])
    db = ContentAddressedDelta.from_units([b])
    dc = ContentAddressedDelta.from_units([c])
    assert da.join(db).merge_keys == db.join(da).merge_keys
    assert da.join(db).join(dc).merge_keys == da.join(db.join(dc)).merge_keys
    assert merge_deltas([dc, da, db]).merge_keys == da.join(db).join(dc).merge_keys


def test_merge_trace_hash_is_order_invariant_and_rejects_arrays():
    a, b = _unit("a"), _unit("b")
    h1 = merge_trace_hash(ContentAddressedDelta.from_units([a, b]), _trace)
    h2 = merge_trace_hash(ContentAddressedDelta.from_units([b, a]), _trace)
    assert h1 == h2

    def bad_trace(unit: _Unit) -> dict[str, object]:
        return {"bad": unit.versor}

    with pytest.raises(TypeError, match="trace-safe"):
        merge_trace_hash(ContentAddressedDelta.from_units([a]), bad_trace)
