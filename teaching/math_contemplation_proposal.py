"""ADR-0172 Tier 1 / W1 — MathReaderRefusalShapeProposal schema.

Mirror of :class:`teaching.proposals.TeachingChainProposal` for the
math-domain contemplation corridor.  Each proposal carries:

- a :class:`~evals.refusal_taxonomy.shape_categories.ShapeCategory` drawn
  from the refusal taxonomy;
- ≥2 :class:`~teaching.math_evidence.MathReaderRefusalEvidence` pointers as
  evidence floor;
- a ``proposed_change_kind`` discriminating the structural change class;
- a ``wrong_zero_assertion`` (≥40 chars) pinning the non-regression claim;
- a ``reasoning_trace`` (W0 :class:`ReasoningTrace`) carrying the
  contemplation chain.

Trust boundary: schema-only module.  No filesystem I/O, no teaching-store
writes, no runtime pipeline hooks.  All validation is in :func:`build_proposal`.

W0 dependency: ``ReasoningTrace`` is imported under ``TYPE_CHECKING`` until
``teaching/math_reasoning_trace.py`` (A1 branch) merges.  At runtime the
field is accepted as an opaque object; ``build_proposal`` validates it is
not ``None`` and carries a non-empty ``trace_id`` attribute.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.comprehension.audit import AuditRow
from teaching.math_evidence import MathReaderRefusalEvidence
from teaching.math_reasoning_trace import ReasoningStep, ReasoningTrace, build_trace


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ChangeKind = Literal[
    "matcher_extension",
    "injector_sub_shape",
    "vocabulary_addition",
    "frame_reclassification",
]

_VALID_CHANGE_KINDS: frozenset[str] = frozenset({
    "matcher_extension",
    "injector_sub_shape",
    "vocabulary_addition",
    "frame_reclassification",
})

_WRONG_ZERO_MIN_LEN: int = 40


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MathReaderRefusalShapeProposal:
    """One proposed structural change for a math-reader refusal shape.

    Construct via :func:`build_proposal` — do not instantiate directly
    (proposal_id is content-derived and requires hash computation).

    Fields
    ------
    proposal_id:
        ``sha256(canonical_bytes(...)).hexdigest()`` over all other fields.
    domain:
        Always ``"math"`` — Literal pin enforced by :func:`build_proposal`.
    shape_category:
        A ratified :class:`ShapeCategory` enum member.
    structural_commonality:
        Human-readable description of the shared structural pattern among
        the evidence rows.
    evidence_pointers:
        ≥2 :class:`MathReaderRefusalEvidence` records; evidence floor mirrors
        ADR-0057's corpus-pointer requirement.
    proposed_change_kind:
        One of the four Tier-1 change classes.
    proposed_change_payload:
        JSON-serializable payload discriminated by ``proposed_change_kind``.
    wrong_zero_assertion:
        ≥40-char natural-language statement pinning the wrong=0 invariant.
    replay_equivalence_hash:
        ``sha256`` digest of the replay-equivalence gate output (mirrors
        :class:`teaching.proposals.ReplayEvidence` contract).
    reasoning_trace:
        W0 :class:`ReasoningTrace` carrying the contemplation derivation.
        Mandatory — ``None`` is rejected by :func:`build_proposal`.
    """

    proposal_id: str
    domain: Literal["math"]
    shape_category: ShapeCategory
    structural_commonality: str
    evidence_pointers: tuple[MathReaderRefusalEvidence, ...]
    proposed_change_kind: ChangeKind
    proposed_change_payload: object
    wrong_zero_assertion: str
    replay_equivalence_hash: str
    reasoning_trace: Any  # ReasoningTrace; symbolic until A1 merges


# ---------------------------------------------------------------------------
# Canonical-bytes serialization
# ---------------------------------------------------------------------------


def _serialise_evidence_pointer(ev: MathReaderRefusalEvidence) -> str:
    """Reduce an evidence record to its stable content hash."""
    return ev.evidence_hash


def _serialise_shape_category(sc: ShapeCategory) -> str:
    return sc.value


def _serialise_reasoning_trace(trace: Any) -> str:
    """Extract trace_id from any object that carries it."""
    trace_id = getattr(trace, "trace_id", None)
    if not isinstance(trace_id, str) or not trace_id:
        raise ValueError(
            "reasoning_trace must have a non-empty str trace_id attribute"
        )
    return trace_id


def canonical_bytes(proposal: MathReaderRefusalShapeProposal) -> bytes:
    """Return deterministic canonical bytes over all fields except proposal_id.

    Stable JSON (sorted keys, no whitespace, UTF-8).  evidence_pointers are
    reduced to their evidence_hash digests; reasoning_trace is reduced to its
    trace_id.  proposed_change_payload must be JSON-serializable (validated
    by :func:`build_proposal` before this function is called).
    """
    payload: dict[str, Any] = {
        "domain": proposal.domain,
        "evidence_pointers": sorted(
            _serialise_evidence_pointer(ev) for ev in proposal.evidence_pointers
        ),
        "proposed_change_kind": proposal.proposed_change_kind,
        "proposed_change_payload": proposal.proposed_change_payload,
        "reasoning_trace_id": _serialise_reasoning_trace(proposal.reasoning_trace),
        "replay_equivalence_hash": proposal.replay_equivalence_hash,
        "shape_category": _serialise_shape_category(proposal.shape_category),
        "structural_commonality": proposal.structural_commonality,
        "wrong_zero_assertion": proposal.wrong_zero_assertion,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_proposal_id(
    *,
    domain: Literal["math"],
    shape_category: ShapeCategory,
    structural_commonality: str,
    evidence_pointers: tuple[MathReaderRefusalEvidence, ...],
    proposed_change_kind: ChangeKind,
    proposed_change_payload: object,
    wrong_zero_assertion: str,
    replay_equivalence_hash: str,
    reasoning_trace: Any,
) -> str:
    """Hash all content fields to produce a stable proposal_id.

    Uses a temporary placeholder proposal_id so that :func:`canonical_bytes`
    can operate on a fully-formed dataclass without the chicken-and-egg
    problem of hashing the id field itself.
    """
    placeholder = MathReaderRefusalShapeProposal(
        proposal_id="",
        domain=domain,
        shape_category=shape_category,
        structural_commonality=structural_commonality,
        evidence_pointers=evidence_pointers,
        proposed_change_kind=proposed_change_kind,
        proposed_change_payload=proposed_change_payload,
        wrong_zero_assertion=wrong_zero_assertion,
        replay_equivalence_hash=replay_equivalence_hash,
        reasoning_trace=reasoning_trace,
    )
    raw = canonical_bytes(placeholder)
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_proposal(
    *,
    domain: Literal["math"] = "math",
    shape_category: ShapeCategory,
    structural_commonality: str,
    evidence_pointers: tuple[MathReaderRefusalEvidence, ...],
    proposed_change_kind: str,
    proposed_change_payload: object,
    wrong_zero_assertion: str,
    replay_equivalence_hash: str,
    reasoning_trace: Any,
) -> MathReaderRefusalShapeProposal:
    """Build a :class:`MathReaderRefusalShapeProposal` with all invariants enforced.

    Raises ``ValueError`` on any violation; the caller must fix the inputs.

    Invariants
    ----------
    1. ``domain`` must be ``"math"``.
    2. ``shape_category`` must be a :class:`ShapeCategory` enum member.
    3. ``len(evidence_pointers) >= 2`` (evidence floor).
    4. ``proposed_change_kind`` in :data:`_VALID_CHANGE_KINDS`.
    5. ``proposed_change_payload`` must be JSON-serializable.
    6. ``len(wrong_zero_assertion.strip()) >= _WRONG_ZERO_MIN_LEN``.
    7. ``reasoning_trace`` is not ``None`` and carries a non-empty ``trace_id``.
    """
    if domain != "math":
        raise ValueError(f"domain must be 'math'; got {domain!r}")

    if not isinstance(shape_category, ShapeCategory):
        raise ValueError(
            f"shape_category must be a ShapeCategory enum member; got {shape_category!r}"
        )

    if len(evidence_pointers) < 2:
        raise ValueError(
            f"evidence_pointers requires ≥2 entries; got {len(evidence_pointers)}"
        )

    if proposed_change_kind not in _VALID_CHANGE_KINDS:
        raise ValueError(
            f"proposed_change_kind {proposed_change_kind!r} is not a valid ChangeKind; "
            f"allowed: {sorted(_VALID_CHANGE_KINDS)}"
        )

    try:
        json.dumps(proposed_change_payload, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"proposed_change_payload is not JSON-serializable: {exc}"
        ) from exc

    if not wrong_zero_assertion or len(wrong_zero_assertion.strip()) < _WRONG_ZERO_MIN_LEN:
        raise ValueError(
            f"wrong_zero_assertion must be ≥{_WRONG_ZERO_MIN_LEN} chars (non-empty); "
            f"got {len(wrong_zero_assertion)!r}"
        )

    if reasoning_trace is None:
        raise ValueError("reasoning_trace is required and must not be None")

    # Validate trace_id accessibility (also validates the serialisation path).
    trace_id = getattr(reasoning_trace, "trace_id", None)
    if not isinstance(trace_id, str) or not trace_id:
        raise ValueError(
            "reasoning_trace must carry a non-empty str trace_id attribute"
        )

    resolved_kind: ChangeKind = proposed_change_kind  # type: ignore[assignment]

    pid = compute_proposal_id(
        domain=domain,
        shape_category=shape_category,
        structural_commonality=structural_commonality,
        evidence_pointers=evidence_pointers,
        proposed_change_kind=resolved_kind,
        proposed_change_payload=proposed_change_payload,
        wrong_zero_assertion=wrong_zero_assertion,
        replay_equivalence_hash=replay_equivalence_hash,
        reasoning_trace=reasoning_trace,
    )

    return MathReaderRefusalShapeProposal(
        proposal_id=pid,
        domain=domain,
        shape_category=shape_category,
        structural_commonality=structural_commonality,
        evidence_pointers=tuple(evidence_pointers),
        proposed_change_kind=resolved_kind,
        proposed_change_payload=proposed_change_payload,
        wrong_zero_assertion=wrong_zero_assertion,
        replay_equivalence_hash=replay_equivalence_hash,
        reasoning_trace=reasoning_trace,
    )


# ---------------------------------------------------------------------------
# Self-contained JSONL persistence serializer (ADR-0172 tightening follow-up #1)
# ---------------------------------------------------------------------------
#
# canonical_bytes() above is the content-hash function: it reduces
# evidence_pointers to evidence_hashes and reasoning_trace to its trace_id.
# That's the right shape for the proposal_id derivation but NOT for
# round-tripping through disk — a reader cannot reconstruct the full
# proposal from canonical bytes without re-running the decomposer.
#
# to_jsonl_record() / from_jsonl_record() are a SEPARATE persistence
# serializer that emits a self-contained record (proposal_id, full
# evidence_pointers, full reasoning_trace.steps) so the workbench can
# read proposals.jsonl without re-running decompose_audit().
#
# Determinism contract preserved: sort_keys=True, compact separators,
# no floats (rejected by reasoning_trace validators).


def _audit_row_to_dict(row: AuditRow) -> dict[str, Any]:
    return {
        "case_id": row.case_id,
        "sentence_index": row.sentence_index,
        "token_index": row.token_index,
        "token_text": row.token_text,
        "recognized_terms": list(row.recognized_terms),
        "skipped_frame": row.skipped_frame,
        "missing_operator": row.missing_operator,
        "refusal_reason": row.refusal_reason,
        "refusal_detail": row.refusal_detail,
    }


def _audit_row_from_dict(data: dict[str, Any]) -> AuditRow:
    return AuditRow(
        case_id=str(data["case_id"]),
        sentence_index=int(data["sentence_index"]),
        token_index=int(data["token_index"]),
        token_text=str(data["token_text"]),
        recognized_terms=tuple(data.get("recognized_terms") or ()),
        skipped_frame=data.get("skipped_frame"),
        missing_operator=data.get("missing_operator"),
        refusal_reason=str(data.get("refusal_reason", "")),
        refusal_detail=str(data.get("refusal_detail", "")),
    )


def _evidence_to_dict(ev: MathReaderRefusalEvidence) -> dict[str, Any]:
    return {
        "case_id": ev.case_id,
        "sentence_index": ev.sentence_index,
        "token_index": ev.token_index,
        "refusal_reason": ev.refusal_reason,
        "missing_operator": ev.missing_operator,
        "claim_signature": ev.claim_signature,
        "evidence_hash": ev.evidence_hash,
        "sub_type": ev.sub_type,
        "audit_row": _audit_row_to_dict(ev.audit_row),
    }


def _evidence_from_dict(data: dict[str, Any]) -> MathReaderRefusalEvidence:
    return MathReaderRefusalEvidence(
        case_id=str(data["case_id"]),
        sentence_index=int(data["sentence_index"]),
        token_index=int(data["token_index"]),
        refusal_reason=str(data["refusal_reason"]),
        missing_operator=data.get("missing_operator"),
        claim_signature=str(data.get("claim_signature", "")),
        evidence_hash=str(data["evidence_hash"]),
        audit_row=_audit_row_from_dict(data["audit_row"]),
        sub_type=data["sub_type"],
    )


def _step_to_dict(step: ReasoningStep) -> dict[str, Any]:
    return {
        "step_index": step.step_index,
        "step_kind": step.step_kind,
        "input_pointers": list(step.input_pointers),
        "claim": step.claim,
        "justification": step.justification,
        "output_payload": step.output_payload,
    }


def _step_from_dict(data: dict[str, Any]) -> ReasoningStep:
    return ReasoningStep(
        step_index=int(data["step_index"]),
        step_kind=data["step_kind"],
        input_pointers=tuple(str(p) for p in data.get("input_pointers", ())),
        claim=str(data.get("claim", "")),
        justification=str(data.get("justification", "")),
        output_payload=data.get("output_payload"),
    )


def to_jsonl_record(proposal: MathReaderRefusalShapeProposal) -> dict[str, Any]:
    """Return a self-contained dict representation suitable for JSONL persistence.

    Unlike :func:`canonical_bytes`, this record includes:
    - ``proposal_id`` (so consumers don't need to recompute it)
    - full ``evidence_pointers`` (nested dicts — not just hashes)
    - full ``reasoning_trace.steps`` (inline — not just trace_id)

    The output is JSON-serializable.  Encoding to bytes via
    ``json.dumps(record, sort_keys=True, separators=(",", ":"),
    ensure_ascii=False)`` produces deterministic byte-identical output
    across reruns.
    """
    trace = proposal.reasoning_trace
    return {
        "proposal_id": proposal.proposal_id,
        "domain": proposal.domain,
        "shape_category": proposal.shape_category.value,
        "structural_commonality": proposal.structural_commonality,
        "evidence_pointers": [
            _evidence_to_dict(ev) for ev in proposal.evidence_pointers
        ],
        "proposed_change_kind": proposal.proposed_change_kind,
        "proposed_change_payload": proposal.proposed_change_payload,
        "wrong_zero_assertion": proposal.wrong_zero_assertion,
        "replay_equivalence_hash": proposal.replay_equivalence_hash,
        "reasoning_trace": {
            "trace_id": trace.trace_id,
            "steps": [_step_to_dict(s) for s in trace.steps],
        },
    }


def from_jsonl_record(record: dict[str, Any]) -> MathReaderRefusalShapeProposal:
    """Reconstruct a proposal from a :func:`to_jsonl_record` dict.

    Goes through :func:`build_proposal` so all invariants are re-validated
    (evidence floor, change_kind allowlist, wrong_zero min-length, trace_id
    presence, JSON-serializable payload).  The reconstructed ``proposal_id``
    must match the persisted one — mismatch indicates tampering or schema
    drift and raises :class:`ValueError`.
    """
    evidence_records = tuple(
        _evidence_from_dict(d) for d in record.get("evidence_pointers", ())
    )
    steps = tuple(_step_from_dict(d) for d in record["reasoning_trace"]["steps"])
    trace = build_trace(steps)

    shape_category = ShapeCategory(record["shape_category"])

    proposal = build_proposal(
        domain=record.get("domain", "math"),
        shape_category=shape_category,
        structural_commonality=str(record["structural_commonality"]),
        evidence_pointers=evidence_records,
        proposed_change_kind=str(record["proposed_change_kind"]),
        proposed_change_payload=record.get("proposed_change_payload"),
        wrong_zero_assertion=str(record["wrong_zero_assertion"]),
        replay_equivalence_hash=str(record["replay_equivalence_hash"]),
        reasoning_trace=trace,
    )

    persisted_id = str(record.get("proposal_id", ""))
    if persisted_id and persisted_id != proposal.proposal_id:
        raise ValueError(
            "proposal_id mismatch on JSONL round-trip: persisted "
            f"{persisted_id!r} != recomputed {proposal.proposal_id!r}"
        )
    return proposal


__all__ = [
    "ChangeKind",
    "MathReaderRefusalShapeProposal",
    "build_proposal",
    "canonical_bytes",
    "compute_proposal_id",
    "from_jsonl_record",
    "to_jsonl_record",
]
