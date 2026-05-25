from __future__ import annotations

from dataclasses import dataclass, field

from .canonical import canonical_hash, canonicalize
from .types import CtpActor, CtpEpistemic, CtpPayload, CtpProof, CtpStateRef

_ALLOWED_KINDS = {"command", "event", "observation", "proposal", "verdict", "proof", "snapshot"}
_ALLOWED_PAYLOAD_ENCODINGS = {"json.v1", "vmp.binary.v1", "opaque.ref.v1"}
_REQUIRED_TURN_FIELDS = {"core.turn.completed.v1", "core.turn.refused.v1"}


def _payload_canonical(payload: CtpPayload) -> dict:
    data = {
        "encoding": payload.encoding,
        "schema": payload.schema,
        "body": payload.body,
        "body_ref": payload.body_ref,
    }
    data["hash"] = payload.hash or canonical_hash(data)
    return canonicalize(data)


@dataclass(frozen=True)
class CtpEnvelope:
    ctp_version: str
    message_type: str
    kind: str
    actor: CtpActor
    payload: CtpPayload
    causation_id: str = ""
    correlation_id: str = ""
    sequence: int = 0
    state: CtpStateRef = field(default_factory=CtpStateRef)
    epistemic: CtpEpistemic | None = None
    proof: CtpProof = field(default_factory=CtpProof)
    message_id: str = ""

    def canonical(self, *, include_message_id: bool = True) -> dict:
        data = {
            "ctp_version": self.ctp_version,
            "message_type": self.message_type,
            "kind": self.kind,
            "causation_id": self.causation_id,
            "correlation_id": self.correlation_id,
            "sequence": self.sequence,
            "actor": self.actor,
            "state": self.state,
            "epistemic": self.epistemic,
            "proof": self.proof,
            "payload": _payload_canonical(self.payload),
        }
        if include_message_id:
            data["message_id"] = self.message_id or self.computed_message_id()
        return canonicalize(data)

    def computed_message_id(self) -> str:
        return canonical_hash(self.canonical(include_message_id=False))

    def with_computed_message_id(self) -> "CtpEnvelope":
        return CtpEnvelope(
            ctp_version=self.ctp_version,
            message_type=self.message_type,
            kind=self.kind,
            actor=self.actor,
            payload=self.payload,
            causation_id=self.causation_id,
            correlation_id=self.correlation_id,
            sequence=self.sequence,
            state=self.state,
            epistemic=self.epistemic,
            proof=self.proof,
            message_id=self.computed_message_id(),
        )

    def validate(self) -> None:
        if self.ctp_version != "0.1":
            raise ValueError(f"Unsupported CTP version: {self.ctp_version}")
        if self.kind not in _ALLOWED_KINDS:
            raise ValueError(f"Unsupported CTP kind: {self.kind}")
        if self.payload.encoding not in _ALLOWED_PAYLOAD_ENCODINGS:
            raise ValueError(f"Unsupported CTP payload encoding: {self.payload.encoding}")
        if self.sequence < 0:
            raise ValueError("CTP sequence must be non-negative")
        if self.message_id and self.message_id != self.computed_message_id():
            raise ValueError("CTP message_id does not match canonical content")
        if self.message_type in _REQUIRED_TURN_FIELDS:
            if self.epistemic is None:
                raise ValueError(f"{self.message_type} requires epistemic metadata")
            if not self.proof.trace_hash:
                raise ValueError(f"{self.message_type} requires proof.trace_hash")
        self.canonical()
