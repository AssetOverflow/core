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
from typing import TYPE_CHECKING, Any, Literal

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from teaching.math_evidence import MathReaderRefusalEvidence

if TYPE_CHECKING:
    from teaching.math_reasoning_trace import ReasoningTrace


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


__all__ = [
    "ChangeKind",
    "MathReaderRefusalShapeProposal",
    "build_proposal",
    "canonical_bytes",
    "compute_proposal_id",
]
