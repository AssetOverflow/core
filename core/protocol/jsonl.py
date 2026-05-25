from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from .envelope import CtpEnvelope
from .types import CtpActor, CtpEpistemic, CtpInvariant, CtpPayload, CtpProof, CtpStateRef


def _invariant_from_dict(data: dict) -> CtpInvariant:
    return CtpInvariant(**data)


def envelope_from_dict(data: dict) -> CtpEnvelope:
    proof = data.get("proof") or {}
    invariants = tuple(_invariant_from_dict(i) for i in proof.get("invariants", ()))
    env = CtpEnvelope(
        ctp_version=data["ctp_version"],
        message_type=data["message_type"],
        kind=data["kind"],
        actor=CtpActor(**data["actor"]),
        payload=CtpPayload(**data["payload"]),
        causation_id=data.get("causation_id", ""),
        correlation_id=data.get("correlation_id", ""),
        sequence=int(data.get("sequence", 0)),
        state=CtpStateRef(**(data.get("state") or {})),
        epistemic=(CtpEpistemic(**data["epistemic"]) if data.get("epistemic") else None),
        proof=CtpProof(
            trace_hash=proof.get("trace_hash", ""),
            replay_digest=proof.get("replay_digest", ""),
            admissibility_trace_hash=proof.get("admissibility_trace_hash", ""),
            operator_invocation=proof.get("operator_invocation", ""),
            versor_condition=proof.get("versor_condition"),
            refusal_reason=proof.get("refusal_reason", ""),
            invariants=invariants,
        ),
        message_id=data.get("message_id", ""),
    )
    env.validate()
    return env


class JsonlEventSink:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(self, event: CtpEnvelope) -> None:
        event.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.canonical(), ensure_ascii=False, sort_keys=True))
            fh.write("\n")


class JsonlEventReader:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def __iter__(self) -> Iterator[CtpEnvelope]:
        with self.path.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    yield envelope_from_dict(json.loads(stripped))
                except Exception as exc:  # pragma: no cover - preserves line context
                    raise ValueError(f"Invalid CTP JSONL event at line {line_no}: {exc}") from exc
