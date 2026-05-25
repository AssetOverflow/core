"""CORE Trace Protocol v0 package."""

from .canonical import canonical_bytes, canonical_hash, canonicalize
from .envelope import CtpEnvelope
from .events import (
    evidence_observed,
    invariant_checked,
    learning_proposal_created,
    tool_invocation_completed,
    tool_invocation_requested,
    turn_completed,
    turn_refused,
    turn_requested,
    verdict_assigned,
)
from .jsonl import JsonlEventReader, JsonlEventSink, envelope_from_dict
from .replay import ReplayViolation, verify_chain, verify_event
from .types import CtpActor, CtpEpistemic, CtpInvariant, CtpPayload, CtpProof, CtpStateRef

__all__ = [
    "CtpActor",
    "CtpEnvelope",
    "CtpEpistemic",
    "CtpInvariant",
    "CtpPayload",
    "CtpProof",
    "CtpStateRef",
    "JsonlEventReader",
    "JsonlEventSink",
    "ReplayViolation",
    "canonical_bytes",
    "canonical_hash",
    "canonicalize",
    "envelope_from_dict",
    "evidence_observed",
    "invariant_checked",
    "learning_proposal_created",
    "tool_invocation_completed",
    "tool_invocation_requested",
    "turn_completed",
    "turn_refused",
    "turn_requested",
    "verdict_assigned",
    "verify_chain",
    "verify_event",
]
