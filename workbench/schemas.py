"""Typed response schemas for CORE Workbench v1.

The schemas are deliberately small UI-facing contracts. They do not expose raw
runtime internals unless an endpoint explicitly includes a diagnostic payload.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, TypeVar

T = TypeVar("T")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_data(value: Any) -> Any:
    if hasattr(value, "as_dict") and callable(value.as_dict):
        return value.as_dict()
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [_to_data(v) for v in value]
    if isinstance(value, tuple):
        return [_to_data(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_data(v) for k, v in value.items()}
    return value


def ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "generated_at": utc_now(), "data": _to_data(data)}


def error(code: str, message: str, *, detail: Any | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if detail is not None:
        payload["detail"] = _to_data(detail)
    return {"ok": False, "generated_at": utc_now(), "error": payload}


@dataclass(frozen=True, slots=True)
class RuntimeStatus:
    backend: str
    git_revision: str
    engine_state_present: bool
    checkpoint_revision: str
    revision_warning: bool
    active_session_id: str | None = None
    mutation_mode: Literal["read_only", "runtime_turn"] = "read_only"


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    artifact_id: str
    kind: str
    path: str
    digest: str | None = None
    created_at: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactDetail:
    artifact_id: str
    kind: str
    path: str
    digest: str | None
    created_at: str | None
    content_type: Literal["json", "jsonl", "text", "unknown"]
    content: Any


@dataclass(frozen=True, slots=True)
class ProposalSummary:
    proposal_id: str
    state: str
    source_kind: str
    replay_equivalent: bool | None
    created_at: str | None
    downstream_effect: Literal["unknown", "none", "observed"] = "unknown"


@dataclass(frozen=True, slots=True)
class ProposalDetail:
    proposal_id: str
    state: str
    source_kind: str
    replay_equivalent: bool | None
    created_at: str | None
    downstream_effect: Literal["unknown", "none", "observed"]
    proposed_chain: Any
    replay_evidence: Any
    source: Any
    evidence: list[Any] = field(default_factory=list)
    artifact_refs: list[ArtifactRef] = field(default_factory=list)
    suggested_cli: str | None = None


@dataclass(frozen=True, slots=True)
class EvalLaneSummary:
    lane: str
    versions: list[str]
    read_only: bool
    description: str | None = None


@dataclass(frozen=True, slots=True)
class EvalRunResult:
    lane: str
    version: str
    split: str
    passed: bool | None
    metrics: dict[str, Any]
    cases: list[Any]
    source_digest: str | None = None


@dataclass(frozen=True, slots=True)
class ReplayDivergence:
    path: str
    original: Any
    replay: Any
    severity: Literal["info", "warning", "failure"]


@dataclass(frozen=True, slots=True)
class ReplayComparison:
    artifact_id: str
    original_hash: str | None
    replay_hash: str | None
    equivalent: bool
    divergences: list[ReplayDivergence] = field(default_factory=list)
