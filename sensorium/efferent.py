"""Concrete efferent gate policy and trace-safe decision records."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sensorium.audio.checksum import sha256_array, sha256_json
from sensorium.protocol import CL41_DIM, AuthorityToken, EfferentVerdict


@dataclass(frozen=True, slots=True)
class EfferentEmissionTrace:
    """Trace-safe record of an efferent admission or refusal."""

    pack_id: str
    admitted: bool
    reason: str
    authority_sha256: str
    policy_sha256: str
    capability: str
    trace_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "pack_id": self.pack_id,
            "admitted": self.admitted,
            "reason": self.reason,
            "authority_sha256": self.authority_sha256,
            "policy_sha256": self.policy_sha256,
            "capability": self.capability,
            "trace_sha256": self.trace_sha256,
        }


@dataclass(frozen=True, slots=True)
class MotorActionIntent:
    """Hash-only semantic lowering of a motor versor into an action predicate."""

    pack_id: str
    predicate_id: str
    vector_sha256: str
    intent_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "pack_id": self.pack_id,
            "predicate_id": self.predicate_id,
            "vector_sha256": self.vector_sha256,
            "intent_sha256": self.intent_sha256,
        }


@dataclass(frozen=True, slots=True)
class ActionVerdictRecord:
    """One pre-decode verdict over a lowered motor intent."""

    intent_sha256: str
    verdict_type: str
    admitted: bool
    reason: str
    policy_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "intent_sha256": self.intent_sha256,
            "verdict_type": self.verdict_type,
            "admitted": self.admitted,
            "reason": self.reason,
            "policy_sha256": self.policy_sha256,
        }


@dataclass(frozen=True, slots=True)
class MotorVerdictTrace:
    """Trace-safe motor gate decision; no decoded payload or trajectory."""

    pack_id: str
    intent_sha256: str
    admitted: bool
    reason: str
    authority_sha256: str
    policy_sha256: str
    required_verdicts: tuple[str, ...]
    trace_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "pack_id": self.pack_id,
            "intent_sha256": self.intent_sha256,
            "admitted": self.admitted,
            "reason": self.reason,
            "authority_sha256": self.authority_sha256,
            "policy_sha256": self.policy_sha256,
            "required_verdicts": list(self.required_verdicts),
            "trace_sha256": self.trace_sha256,
        }


def lower_motor_action_intent(pack_id: str, mv: np.ndarray) -> MotorActionIntent:
    """Lower a motor versor to a semantic predicate, not an actuator command."""
    vec = np.asarray(mv, dtype=np.float32)
    if vec.shape != (CL41_DIM,):
        raise ValueError(f"invalid motor vector shape: {vec.shape}")
    vector_sha256 = sha256_array(vec)
    predicate_id = f"motor.intent.{vector_sha256[:16]}"
    payload = {
        "kind": "MotorActionIntent",
        "pack_id": pack_id,
        "predicate_id": predicate_id,
        "vector_sha256": vector_sha256,
    }
    return MotorActionIntent(
        pack_id=pack_id,
        predicate_id=predicate_id,
        vector_sha256=vector_sha256,
        intent_sha256=sha256_json(payload),
    )


@dataclass(frozen=True, slots=True)
class DefaultEfferentGate:
    """Capability-scoped efferent gate.

    Admission requires a valid ``(32,)`` vector and one of:
    ``decode:<pack_id>``, ``decode:*``, or ``*`` in the authority token.
    """

    policy_id: str = "default-efferent-v1"

    @property
    def policy_sha256(self) -> str:
        return sha256_json({
            "policy_id": self.policy_id,
            "required_capability": "decode:<pack_id>",
            "wildcards": ["decode:*", "*"],
            "shape": [CL41_DIM],
        })

    @property
    def enforces_action_verdicts(self) -> bool:
        """Capability/shape pre-filter only — does NOT lower the decoded action
        into the safety/ethics pack verdicts required by ADR-0198 §3. The
        registry refuses actuating emission through this gate unless an explicit
        sandbox opt-in is set. A future §3 verdict-enforcing gate returns True.
        """
        return False

    def admit(
        self,
        pack_id: str,
        mv: np.ndarray,
        authority: AuthorityToken,
    ) -> EfferentVerdict:
        vec = np.asarray(mv, dtype=np.float32)
        if vec.shape != (CL41_DIM,):
            return EfferentVerdict(
                admitted=False,
                reason=f"invalid efferent vector shape: {vec.shape}",
                authority_sha256=authority.authority_sha256,
                policy_sha256=self.policy_sha256,
            )
        required = f"decode:{pack_id}"
        caps = set(authority.capabilities)
        admitted = required in caps or "decode:*" in caps or "*" in caps
        return EfferentVerdict(
            admitted=admitted,
            reason="admitted" if admitted else f"missing capability: {required}",
            authority_sha256=authority.authority_sha256,
            policy_sha256=self.policy_sha256,
        )

    def trace(
        self,
        pack_id: str,
        authority: AuthorityToken,
        verdict: EfferentVerdict,
    ) -> EfferentEmissionTrace:
        capability = f"decode:{pack_id}"
        payload = {
            "kind": "EfferentEmissionTrace",
            "pack_id": pack_id,
            "admitted": verdict.admitted,
            "reason": verdict.reason,
            "authority_sha256": authority.authority_sha256,
            "policy_sha256": verdict.policy_sha256,
            "capability": capability,
        }
        return EfferentEmissionTrace(
            pack_id=pack_id,
            admitted=verdict.admitted,
            reason=verdict.reason,
            authority_sha256=authority.authority_sha256,
            policy_sha256=verdict.policy_sha256,
            capability=capability,
            trace_sha256=sha256_json(payload),
        )


@dataclass(frozen=True, slots=True)
class VerdictEnforcingEfferentGate:
    """ADR-0198 §3 gate: authority plus explicit action verdict coverage."""

    action_verdicts: tuple[ActionVerdictRecord, ...] = ()
    policy_id: str = "verdict-enforcing-efferent-v1"
    required_verdicts: tuple[str, ...] = ("safety", "ethics", "tool_scope")

    @property
    def enforces_action_verdicts(self) -> bool:
        return True

    @property
    def policy_sha256(self) -> str:
        return sha256_json({
            "policy_id": self.policy_id,
            "required_verdicts": list(self.required_verdicts),
            "action_verdicts": [
                verdict.as_dict()
                for verdict in sorted(
                    self.action_verdicts,
                    key=lambda v: (v.intent_sha256, v.verdict_type, v.policy_sha256),
                )
            ],
        })

    def _verdict_index(self) -> dict[tuple[str, str], ActionVerdictRecord]:
        return {
            (verdict.intent_sha256, verdict.verdict_type): verdict
            for verdict in self.action_verdicts
        }

    def admit(
        self,
        pack_id: str,
        mv: np.ndarray,
        authority: AuthorityToken,
    ) -> EfferentVerdict:
        vec = np.asarray(mv, dtype=np.float32)
        if vec.shape != (CL41_DIM,):
            return EfferentVerdict(
                admitted=False,
                reason=f"invalid efferent vector shape: {vec.shape}",
                authority_sha256=authority.authority_sha256,
                policy_sha256=self.policy_sha256,
            )
        required = f"decode:{pack_id}"
        caps = set(authority.capabilities)
        if required not in caps and "decode:*" not in caps and "*" not in caps:
            return EfferentVerdict(
                admitted=False,
                reason=f"missing capability: {required}",
                authority_sha256=authority.authority_sha256,
                policy_sha256=self.policy_sha256,
            )
        intent = lower_motor_action_intent(pack_id, vec)
        verdicts = self._verdict_index()
        for verdict_type in self.required_verdicts:
            record = verdicts.get((intent.intent_sha256, verdict_type))
            if record is None:
                return EfferentVerdict(
                    admitted=False,
                    reason=f"missing action verdict coverage: {verdict_type}",
                    authority_sha256=authority.authority_sha256,
                    policy_sha256=self.policy_sha256,
                )
            if not record.admitted:
                return EfferentVerdict(
                    admitted=False,
                    reason=f"action verdict refused: {verdict_type}: {record.reason}",
                    authority_sha256=authority.authority_sha256,
                    policy_sha256=self.policy_sha256,
                )
        return EfferentVerdict(
            admitted=True,
            reason="admitted",
            authority_sha256=authority.authority_sha256,
            policy_sha256=self.policy_sha256,
        )

    def trace(
        self,
        pack_id: str,
        mv: np.ndarray,
        authority: AuthorityToken,
        verdict: EfferentVerdict,
    ) -> MotorVerdictTrace:
        intent = lower_motor_action_intent(pack_id, mv)
        payload = {
            "kind": "MotorVerdictTrace",
            "pack_id": pack_id,
            "intent_sha256": intent.intent_sha256,
            "admitted": verdict.admitted,
            "reason": verdict.reason,
            "authority_sha256": authority.authority_sha256,
            "policy_sha256": verdict.policy_sha256,
            "required_verdicts": list(self.required_verdicts),
        }
        return MotorVerdictTrace(
            pack_id=pack_id,
            intent_sha256=intent.intent_sha256,
            admitted=verdict.admitted,
            reason=verdict.reason,
            authority_sha256=authority.authority_sha256,
            policy_sha256=verdict.policy_sha256,
            required_verdicts=tuple(self.required_verdicts),
            trace_sha256=sha256_json(payload),
        )


__all__ = [
    "ActionVerdictRecord",
    "DefaultEfferentGate",
    "EfferentEmissionTrace",
    "MotorActionIntent",
    "MotorVerdictTrace",
    "VerdictEnforcingEfferentGate",
    "lower_motor_action_intent",
]
