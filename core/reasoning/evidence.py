"""Domain-neutral reasoning evidence and Tier-2 agreement checks.

This module is deliberately pure data plus deterministic serialization. It is
the shared evidence shape for proof, reconstruction, contemplation, and sealed
learning arenas; it does not authorize serving behavior by itself.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Final

TIER2_VERIFIED: Final[str] = "tier2_verified"
INSUFFICIENT_EVIDENCE: Final[str] = "insufficient_evidence"
DUPLICATE_STRUCTURAL_SIGNATURE: Final[str] = "duplicate_structural_signature"
COMMITMENT_DISAGREEMENT: Final[str] = "commitment_disagreement"
MISSING_COMMITMENT: Final[str] = "missing_commitment"

TIER2_REASONS: Final[frozenset[str]] = frozenset({
    TIER2_VERIFIED,
    INSUFFICIENT_EVIDENCE,
    DUPLICATE_STRUCTURAL_SIGNATURE,
    COMMITMENT_DISAGREEMENT,
    MISSING_COMMITMENT,
})


def _freeze_json_value(value: Any) -> Any:
    """Recursively freeze JSON-like payloads for immutable evidence storage."""
    if isinstance(value, Mapping):
        frozen = {str(k): _freeze_json_value(v) for k, v in value.items()}
        return MappingProxyType(frozen)
    if isinstance(value, list | tuple):
        return tuple(_freeze_json_value(v) for v in value)
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise TypeError(f"unsupported evidence payload value: {type(value).__name__}")


def _json_value(value: Any) -> Any:
    """Return a JSON-serializable copy of a frozen payload value."""
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(v) for v in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise TypeError(f"unsupported frozen evidence value: {type(value).__name__}")


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        _json_value(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


@dataclass(frozen=True, slots=True)
class OperatorEvidence:
    """Replayable evidence for one deterministic operator invocation."""

    domain: str
    operator: str
    outcome: str
    reason: str
    input_keys: tuple[str, ...]
    check_keys: tuple[str, ...]
    commitment_key: str
    structural_signature: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in (
            "domain",
            "operator",
            "outcome",
            "reason",
            "structural_signature",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"OperatorEvidence.{field_name} is required")
            object.__setattr__(self, field_name, value.strip())
        if not isinstance(self.commitment_key, str):
            raise ValueError("OperatorEvidence.commitment_key must be a string")
        object.__setattr__(self, "input_keys", tuple(str(k) for k in self.input_keys))
        object.__setattr__(self, "check_keys", tuple(str(k) for k in self.check_keys))
        object.__setattr__(self, "payload", _freeze_json_value(dict(self.payload)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "operator": self.operator,
            "outcome": self.outcome,
            "reason": self.reason,
            "input_keys": list(self.input_keys),
            "check_keys": list(self.check_keys),
            "commitment_key": self.commitment_key,
            "structural_signature": self.structural_signature,
            "payload": _json_value(self.payload),
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.as_dict())

    @property
    def evidence_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """Ordered collection of operator evidence with stable serialization."""

    evidences: tuple[OperatorEvidence, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidences", tuple(self.evidences))
        if not all(isinstance(ev, OperatorEvidence) for ev in self.evidences):
            raise ValueError("EvidenceBundle.evidences must contain OperatorEvidence")

    def as_dict(self) -> dict[str, Any]:
        return {"evidences": [ev.as_dict() for ev in self.evidences]}

    def canonical_json(self) -> str:
        return _canonical_json(self.as_dict())

    @property
    def evidence_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Tier2Verdict:
    """Result of a domain-neutral convergent self-verification check."""

    verified: bool
    reason: str
    commitment_key: str = ""
    evidence_hash: str = ""
    structural_signatures: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.reason not in TIER2_REASONS:
            raise ValueError(f"unknown Tier2Verdict.reason: {self.reason!r}")
        object.__setattr__(
            self,
            "structural_signatures",
            tuple(str(s) for s in self.structural_signatures),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "reason": self.reason,
            "commitment_key": self.commitment_key,
            "evidence_hash": self.evidence_hash,
            "structural_signatures": list(self.structural_signatures),
        }


def verify_tier2_agreement(
    evidences: tuple[OperatorEvidence, ...] | list[OperatorEvidence],
) -> Tier2Verdict:
    """Require two distinct structures converging on one non-empty commitment."""
    bundle = EvidenceBundle(tuple(evidences))
    if len(bundle.evidences) < 2:
        return Tier2Verdict(False, INSUFFICIENT_EVIDENCE)

    if any(not ev.commitment_key for ev in bundle.evidences):
        return Tier2Verdict(False, MISSING_COMMITMENT, evidence_hash=bundle.evidence_hash)

    signatures = tuple(ev.structural_signature for ev in bundle.evidences)
    if len(set(signatures)) < 2:
        return Tier2Verdict(
            False,
            DUPLICATE_STRUCTURAL_SIGNATURE,
            evidence_hash=bundle.evidence_hash,
            structural_signatures=tuple(sorted(set(signatures))),
        )

    commitments = Counter(ev.commitment_key for ev in bundle.evidences)
    shared = [key for key, count in commitments.items() if count >= 2]
    if len(shared) != 1 or len(commitments) != 1:
        return Tier2Verdict(
            False,
            COMMITMENT_DISAGREEMENT,
            evidence_hash=bundle.evidence_hash,
            structural_signatures=tuple(sorted(set(signatures))),
        )

    return Tier2Verdict(
        True,
        TIER2_VERIFIED,
        commitment_key=shared[0],
        evidence_hash=bundle.evidence_hash,
        structural_signatures=tuple(sorted(set(signatures))),
    )
