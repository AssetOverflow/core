from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class CtpActor:
    kind: str
    id: str
    authority: str = "system"


@dataclass(frozen=True)
class CtpStateRef:
    runtime_config_hash: str = ""
    pack_set_hash: str = ""
    field_state_hash: str = ""
    backend: str = ""


@dataclass(frozen=True)
class CtpEpistemic:
    state: str
    grounding_source: str
    normative_clearance: Literal["CLEARED", "VIOLATED", "UNASSESSABLE", "SUPPRESSED"]


@dataclass(frozen=True)
class CtpInvariant:
    name: str
    status: Literal["passed", "failed", "unassessed"]
    value: int | float | str | bool | None = None
    threshold: int | float | str | bool | None = None
    detail: str = ""


@dataclass(frozen=True)
class CtpProof:
    trace_hash: str = ""
    replay_digest: str = ""
    admissibility_trace_hash: str = ""
    operator_invocation: str = ""
    versor_condition: float | None = None
    refusal_reason: str = ""
    invariants: tuple[CtpInvariant, ...] = ()


@dataclass(frozen=True)
class CtpPayload:
    encoding: str
    schema: str
    body: dict[str, Any] = field(default_factory=dict)
    body_ref: str = ""
    hash: str = ""
