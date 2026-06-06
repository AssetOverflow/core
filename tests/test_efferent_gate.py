from __future__ import annotations

import numpy as np
import pytest

from pathlib import Path

from sensorium.efferent import (
    ActionVerdictRecord,
    DefaultEfferentGate,
    VerdictEnforcingEfferentGate,
    lower_motor_action_intent,
)
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
    # Exercises the capability pre-filter in isolation: the capability/shape
    # gate is not verdict-enforcing, so the sandbox opt-in is required here.
    reg = ModalityRegistry(efferent_gate=DefaultEfferentGate(), allow_unverified_efferent=True)
    reg.mount(_pack(decoder))

    with pytest.raises(EfferentRefusal, match="missing capability"):
        reg.decode("motor_test", _mv(), authority=_authority("decode:other"))
    assert decoder.calls == 0

    assert reg.decode("motor_test", _mv(), authority=_authority("decode:motor_test")) == "decoded"
    assert decoder.calls == 1


def test_registry_fails_closed_for_actuating_decode_through_capability_only_gate():
    """ADR-0198 §3 / §1.2 Gap B: a capability/shape gate must not authorize a
    real emission. With no sandbox opt-in the decode fails closed and the
    decoder never runs."""
    decoder = _Decoder()
    reg = ModalityRegistry(efferent_gate=DefaultEfferentGate())
    reg.mount(_pack(decoder))
    with pytest.raises(EfferentRefusal, match="action verdicts"):
        reg.decode("motor_test", _mv(), authority=_authority("decode:motor_test"))
    assert decoder.calls == 0


def test_registry_admits_decode_through_verdict_enforcing_gate():
    """A gate that enforces ADR-0198 §3 action verdicts needs no sandbox opt-in."""

    class _VerdictGate:
        enforces_action_verdicts = True

        def admit(self, pack_id: str, mv: np.ndarray, authority: AuthorityToken) -> EfferentVerdict:
            return EfferentVerdict(
                admitted=True,
                reason="admitted",
                authority_sha256=authority.authority_sha256,
                policy_sha256="verdict-test",
            )

    decoder = _Decoder()
    reg = ModalityRegistry(efferent_gate=_VerdictGate())
    reg.mount(_pack(decoder))
    assert reg.decode("motor_test", _mv(), authority=_authority("decode:motor_test")) == "decoded"
    assert decoder.calls == 1


def _admitted_records(intent_sha256: str) -> tuple[ActionVerdictRecord, ...]:
    return (
        ActionVerdictRecord(intent_sha256, "safety", True, "safe", "safety-policy"),
        ActionVerdictRecord(intent_sha256, "ethics", True, "ethical", "ethics-policy"),
        ActionVerdictRecord(intent_sha256, "tool_scope", True, "in scope", "tool-policy"),
    )


def test_adr_0216_motor_verdict_lowering_is_documented():
    root = Path(__file__).resolve().parents[1]
    adr = root / "docs" / "decisions" / "ADR-0216-motor-verdict-lowering.md"
    assert adr.exists()
    text = adr.read_text(encoding="utf-8")
    assert "MotorActionIntent" in text
    assert "VerdictEnforcingEfferentGate" in text
    assert "No physical motor decode is authorized" in text


def test_motor_action_intent_is_hash_only_and_stable():
    intent = lower_motor_action_intent("motor_test", _mv())
    same = lower_motor_action_intent("motor_test", _mv())
    payload = intent.as_dict()
    assert intent.intent_sha256 == same.intent_sha256
    assert intent.predicate_id.startswith("motor.intent.")
    assert "decoded" not in str(payload)
    assert "trajectory" not in str(payload)
    for value in payload.values():
        assert not isinstance(value, (np.ndarray, bytes, bytearray))


def test_verdict_enforcing_gate_refuses_missing_coverage_before_decoder():
    decoder = _Decoder()
    gate = VerdictEnforcingEfferentGate()
    reg = ModalityRegistry(efferent_gate=gate)
    reg.mount(_pack(decoder))
    with pytest.raises(EfferentRefusal, match="missing action verdict coverage"):
        reg.decode("motor_test", _mv(), authority=_authority("decode:motor_test"))
    assert decoder.calls == 0


def test_verdict_enforcing_gate_refuses_failed_verdict_before_decoder():
    decoder = _Decoder()
    intent = lower_motor_action_intent("motor_test", _mv())
    records = (
        ActionVerdictRecord(intent.intent_sha256, "safety", True, "safe", "safety-policy"),
        ActionVerdictRecord(intent.intent_sha256, "ethics", False, "ethical refusal", "ethics-policy"),
        ActionVerdictRecord(intent.intent_sha256, "tool_scope", True, "in scope", "tool-policy"),
    )
    reg = ModalityRegistry(efferent_gate=VerdictEnforcingEfferentGate(records))
    reg.mount(_pack(decoder))
    with pytest.raises(EfferentRefusal, match="action verdict refused: ethics"):
        reg.decode("motor_test", _mv(), authority=_authority("decode:motor_test"))
    assert decoder.calls == 0


def test_verdict_enforcing_gate_admits_only_with_authority_and_verdicts():
    decoder = _Decoder()
    intent = lower_motor_action_intent("motor_test", _mv())
    gate = VerdictEnforcingEfferentGate(_admitted_records(intent.intent_sha256))
    reg = ModalityRegistry(efferent_gate=gate)
    reg.mount(_pack(decoder))

    with pytest.raises(EfferentRefusal, match="missing capability"):
        reg.decode("motor_test", _mv(), authority=_authority("decode:other"))
    assert decoder.calls == 0

    assert reg.decode("motor_test", _mv(), authority=_authority("decode:motor_test")) == "decoded"
    assert decoder.calls == 1


def test_verdict_enforcing_trace_is_hash_only():
    intent = lower_motor_action_intent("motor_test", _mv())
    gate = VerdictEnforcingEfferentGate(_admitted_records(intent.intent_sha256))
    authority = _authority("decode:motor_test")
    verdict = gate.admit("motor_test", _mv(), authority)
    trace = gate.trace("motor_test", _mv(), authority, verdict).as_dict()
    assert trace["admitted"] is True
    assert trace["intent_sha256"] == intent.intent_sha256
    assert "decoded" not in str(trace)
    assert "trajectory" not in str(trace)
    assert "action_trace" not in str(trace)
    for value in trace.values():
        assert not isinstance(value, (np.ndarray, bytes, bytearray))
