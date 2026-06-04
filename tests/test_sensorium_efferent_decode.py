from __future__ import annotations

import numpy as np
import pytest

from sensorium.protocol import (
    AuthorityToken,
    EfferentRefusal,
    EfferentVerdict,
    Modality,
    ModalityPack,
    ModalityVocabulary,
)
from sensorium.registry import ModalityRegistry


class _Decoder:
    modality = Modality.MOTOR

    def __init__(self) -> None:
        self.calls = 0

    def decode(self, mv: np.ndarray) -> str:
        self.calls += 1
        return f"decoded:{float(mv[0]):.1f}"

    def decode_batch(self, mvs: np.ndarray) -> list[str]:
        self.calls += len(mvs)
        return [f"decoded:{float(mv[0]):.1f}" for mv in mvs]


class _Gate:
    def __init__(self, admitted: bool = True, deny_after: int | None = None) -> None:
        self.admitted = admitted
        self.deny_after = deny_after
        self.calls = 0

    def admit(self, pack_id: str, mv: np.ndarray, authority: AuthorityToken) -> EfferentVerdict:
        self.calls += 1
        admitted = self.admitted and (self.deny_after is None or self.calls <= self.deny_after)
        return EfferentVerdict(
            admitted=admitted,
            reason="ok" if admitted else "denied",
            authority_sha256=authority.authority_sha256,
            policy_sha256="test-policy",
        )


def _pack(decoder: _Decoder, *, engaged: bool = True) -> ModalityPack:
    return ModalityPack(
        pack_id="motor_test",
        modality_type=Modality.MOTOR,
        vocabulary=ModalityVocabulary(),
        grammar_scaffold=None,
        checksum_verified=True,
        decoder=decoder,
        gate_engaged=engaged,
    )


def _authority() -> AuthorityToken:
    return AuthorityToken("tester", ("decode:motor_test",), "test-revision")


def _mv() -> np.ndarray:
    out = np.zeros(32, dtype=np.float32)
    out[0] = 1.0
    return out


def test_decode_denies_by_default_before_decoder_runs():
    decoder = _Decoder()
    reg = ModalityRegistry()
    reg.mount(_pack(decoder))
    with pytest.raises(EfferentRefusal, match="no efferent gate"):
        reg.decode("motor_test", _mv(), authority=_authority())
    assert decoder.calls == 0


def test_decode_requires_admitting_gate_before_surface_decode():
    decoder = _Decoder()
    gate = _Gate(admitted=True)
    reg = ModalityRegistry(efferent_gate=gate)
    reg.mount(_pack(decoder))
    assert reg.decode("motor_test", _mv(), authority=_authority()) == "decoded:1.0"
    assert gate.calls == 1
    assert decoder.calls == 1


def test_decode_refusal_does_not_call_decoder():
    decoder = _Decoder()
    reg = ModalityRegistry(efferent_gate=_Gate(admitted=False))
    reg.mount(_pack(decoder))
    with pytest.raises(EfferentRefusal, match="denied"):
        reg.decode("motor_test", _mv(), authority=_authority())
    assert decoder.calls == 0


def test_decode_batch_admits_all_before_decoding_any_surface():
    decoder = _Decoder()
    gate = _Gate(admitted=True, deny_after=1)
    reg = ModalityRegistry(efferent_gate=gate)
    reg.mount(_pack(decoder))
    batch = np.stack([_mv(), _mv()])
    with pytest.raises(EfferentRefusal, match="denied"):
        reg.decode_batch("motor_test", batch, authority=_authority())
    assert gate.calls == 2
    assert decoder.calls == 0


def test_decode_validates_shape_and_closed_gate():
    decoder = _Decoder()
    reg = ModalityRegistry(efferent_gate=_Gate())
    reg.mount(_pack(decoder, engaged=False))
    with pytest.raises(RuntimeError, match="gate is not engaged"):
        reg.decode("motor_test", _mv(), authority=_authority())
    reg = ModalityRegistry(efferent_gate=_Gate())
    reg.mount(_pack(decoder))
    with pytest.raises(ValueError, match="expected"):
        reg.decode("motor_test", np.zeros(31, dtype=np.float32), authority=_authority())
