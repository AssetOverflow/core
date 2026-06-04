from __future__ import annotations

import numpy as np
import pytest

from sensorium.efferent import DefaultEfferentGate
from sensorium.protocol import AuthorityToken, EfferentRefusal, Modality, ModalityPack, ModalityVocabulary
from sensorium.registry import ModalityRegistry


class _Decoder:
    modality = Modality.MOTOR

    def __init__(self) -> None:
        self.calls = 0

    def decode(self, mv: np.ndarray) -> str:
        self.calls += 1
        return "decoded"

    def decode_batch(self, mvs: np.ndarray) -> list[str]:
        self.calls += len(mvs)
        return ["decoded" for _ in range(len(mvs))]


def _mv() -> np.ndarray:
    out = np.zeros(32, dtype=np.float32)
    out[0] = 1.0
    return out


def _authority(*capabilities: str) -> AuthorityToken:
    return AuthorityToken(
        principal_id="test-principal",
        capabilities=tuple(capabilities),
        issued_at_revision="test-revision",
    )


def _pack(decoder: _Decoder) -> ModalityPack:
    return ModalityPack(
        pack_id="motor_test",
        modality_type=Modality.MOTOR,
        vocabulary=ModalityVocabulary(),
        grammar_scaffold=None,
        checksum_verified=True,
        decoder=decoder,
        gate_engaged=True,
    )


def test_default_efferent_gate_admits_exact_and_wildcard_capabilities():
    gate = DefaultEfferentGate()
    assert gate.admit("motor_test", _mv(), _authority("decode:motor_test")).admitted
    assert gate.admit("motor_test", _mv(), _authority("decode:*")).admitted
    assert gate.admit("motor_test", _mv(), _authority("*")).admitted


def test_default_efferent_gate_denies_missing_capability_and_bad_shape():
    gate = DefaultEfferentGate()
    denied = gate.admit("motor_test", _mv(), _authority("decode:other"))
    assert denied.admitted is False
    assert "missing capability" in denied.reason

    malformed = gate.admit("motor_test", np.zeros(31, dtype=np.float32), _authority("decode:motor_test"))
    assert malformed.admitted is False
    assert "invalid efferent vector shape" in malformed.reason


def test_default_efferent_trace_is_hash_only():
    gate = DefaultEfferentGate()
    authority = _authority("decode:motor_test")
    verdict = gate.admit("motor_test", _mv(), authority)
    trace = gate.trace("motor_test", authority, verdict).as_dict()
    assert trace["admitted"] is True
    assert trace["capability"] == "decode:motor_test"
    assert "mv" not in trace
    for value in trace.values():
        assert not isinstance(value, (np.ndarray, bytes, bytearray))


def test_registry_uses_default_efferent_gate_before_decoder():
    decoder = _Decoder()
    reg = ModalityRegistry(efferent_gate=DefaultEfferentGate())
    reg.mount(_pack(decoder))

    with pytest.raises(EfferentRefusal, match="missing capability"):
        reg.decode("motor_test", _mv(), authority=_authority("decode:other"))
    assert decoder.calls == 0

    assert reg.decode("motor_test", _mv(), authority=_authority("decode:motor_test")) == "decoded"
    assert decoder.calls == 1
