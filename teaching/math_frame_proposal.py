"""ADR-0168 / ADR-0168.1 — MathFrameClaimProposal adapter.

Defines the math-domain proposal type carrying FrameClaim evidence pointers.
Mirror of :mod:`teaching.math_contemplation_proposal` for the frame
admissibility sub-type.

Per ADR-0168.1 §"Evidence floor", a :class:`MathFrameClaimProposal` is
eligible only if every evidence pointer declares ``source="math_audit"``.
Audit evidence MUST NEVER be laundered as ``source="corpus"`` — that would
falsely impersonate ADR-0057's cognition corpus evidence floor.

Trust boundary: schema-only module. No filesystem I/O, no teaching-store
writes, no runtime pipeline hooks. All validation lives in
:func:`build_frame_claim_proposal` and :func:`build_evidence_pointer`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Final, Literal

from teaching.math_evidence import MathReaderRefusalEvidence


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

Polarity = Literal["affirms", "falsifies"]

_VALID_POLARITIES: Final[frozenset[str]] = frozenset({"affirms", "falsifies"})

# Mirrors SAFE_FRAME_CATEGORIES in :mod:`teaching.math_frame_ratification`.
# Held here as well so the proposal layer can reject illegal frame categories
# before the proposal is ever built — defense in depth at the schema boundary.
_ALLOWLISTED_FRAME_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "increment_frame",
        "decrement_frame",
        "transfer_frame",
        "remainder_frame",
    }
)

# Forbidden evidence source values.  ADR-0168.1 §"Evidence floor" requires
# math-audit evidence to carry ``source="math_audit"``.  Any cognition-style
# value reaching this module indicates evidence laundering — fail loudly.
_FORBIDDEN_EVIDENCE_SOURCES: Final[frozenset[str]] = frozenset({"corpus"})


# ---------------------------------------------------------------------------
# Evidence pointer
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MathReaderRefusalEvidencePointer:
    """One pointer to a math-domain refusal-row evidence record.

    Per ADR-0168.1, ``source`` is pinned to ``"math_audit"`` at construction.
    The factory :func:`build_evidence_pointer` is the only sanctioned way to
    create one — direct instantiation works but is discouraged because the
    factory ensures ``source`` cannot drift to a cognition value.
    """

    source: Literal["math_audit"]
    case_id: str
    sentence_index: int
    token_index: int
    missing_operator: str
    refusal_reason: str
    evidence_hash: str
    audit_row_digest: str


def _audit_row_digest(evidence: MathReaderRefusalEvidence) -> str:
    """SHA-256 over the evidence record's canonical bytes (excludes hash itself).

    Provides the replay anchor: identical evidence yields an identical
    digest across processes, runs, and reorderings.
    """

    return hashlib.sha256(evidence.to_canonical_bytes()).hexdigest()


def build_evidence_pointer(
    evidence: MathReaderRefusalEvidence,
) -> MathReaderRefusalEvidencePointer:
    """Build a math-audit evidence pointer from a refusal-row record.

    Pins ``source="math_audit"`` per ADR-0168.1 §"Evidence floor".
    """

    if evidence.missing_operator is None:
        raise ValueError(
            "MathFrameClaim evidence must declare a missing_operator; got None"
        )
    return MathReaderRefusalEvidencePointer(
        source="math_audit",
        case_id=evidence.case_id,
        sentence_index=evidence.sentence_index,
        token_index=evidence.token_index,
        missing_operator=evidence.missing_operator,
        refusal_reason=evidence.refusal_reason,
        evidence_hash=evidence.evidence_hash,
        audit_row_digest=_audit_row_digest(evidence),
    )


# ---------------------------------------------------------------------------
# Proposal
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MathFrameClaimProposal:
    """A reviewed assertion that ``surface_form`` participates in ``frame_category``.

    Per ADR-0168.1 the proposal carries:

    - canonical identity (proposal_id, claim_signature)
    - the structural claim (surface_form, frame_category, polarity)
    - math-domain evidence pointers (source="math_audit" only)
    - review state and operator note

    The proposal is *not* a runtime frame registry entry.  Operator
    acceptance does not auto-mutate the runtime — see
    :mod:`teaching.math_frame_ratification` for the explicit mutation
    boundary.
    """

    proposal_id: str
    claim_signature: str
    surface_form: str
    frame_category: str
    polarity: Polarity
    evidence: tuple[MathReaderRefusalEvidencePointer, ...]
    review_state: Literal["pending", "accepted", "rejected", "withdrawn"]
    operator_note: str = ""
    domain: Literal["math"] = "math"
    sub_type: Literal["frame"] = "frame"


def _serialise_pointer(p: MathReaderRefusalEvidencePointer) -> dict[str, Any]:
    return {
        "source": p.source,
        "case_id": p.case_id,
        "sentence_index": p.sentence_index,
        "token_index": p.token_index,
        "missing_operator": p.missing_operator,
        "refusal_reason": p.refusal_reason,
        "evidence_hash": p.evidence_hash,
        "audit_row_digest": p.audit_row_digest,
    }


def compute_claim_signature(
    *,
    surface_form: str,
    frame_category: str,
    polarity: str,
    evidence: tuple[MathReaderRefusalEvidencePointer, ...],
) -> str:
    """Deterministic canonical signature for a frame claim.

    Per ADR-0168 §"Replay obligations" #1, equivalent refusals must yield
    identical signatures.  We hash over:

    - normalized surface form (lower, stripped)
    - frame category (allowlisted string)
    - polarity
    - the sorted set of audit_row_digests from the evidence pointers
    """

    surface_norm = surface_form.lower().strip()
    digests = sorted(p.audit_row_digest for p in evidence)
    payload = json.dumps(
        {
            "surface_form": surface_norm,
            "frame_category": frame_category,
            "polarity": polarity,
            "audit_row_digests": digests,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compute_proposal_id(
    *,
    surface_form: str,
    frame_category: str,
    polarity: str,
    evidence: tuple[MathReaderRefusalEvidencePointer, ...],
) -> str:
    """Stable proposal_id from canonical identity (ADR-0168.1 §"Idempotency").

    ``sha256(domain | subtype | surface_form | frame_category | polarity |
    evidence_digest_set)`` — clock-time-independent and identity-stable.
    """

    surface_norm = surface_form.lower().strip()
    digests = sorted(p.audit_row_digest for p in evidence)
    payload = json.dumps(
        {
            "domain": "math",
            "sub_type": "frame",
            "surface_form": surface_norm,
            "frame_category": frame_category,
            "polarity": polarity,
            "audit_row_digests": digests,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_bytes(proposal: MathFrameClaimProposal) -> bytes:
    """Deterministic canonical bytes for replay / persistence.

    Excludes ``proposal_id`` (the hash function input) and ``review_state``
    (mutable transition surface).
    """

    payload: dict[str, Any] = {
        "domain": proposal.domain,
        "sub_type": proposal.sub_type,
        "claim_signature": proposal.claim_signature,
        "surface_form": proposal.surface_form,
        "frame_category": proposal.frame_category,
        "polarity": proposal.polarity,
        "evidence": sorted(
            (_serialise_pointer(p) for p in proposal.evidence),
            key=lambda d: d["audit_row_digest"],
        ),
        "operator_note": proposal.operator_note,
    }
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def build_frame_claim_proposal(
    *,
    surface_form: str,
    frame_category: str,
    polarity: str,
    evidence: tuple[MathReaderRefusalEvidencePointer, ...],
    operator_note: str = "",
    review_state: Literal["pending", "accepted", "rejected", "withdrawn"] = "pending",
) -> MathFrameClaimProposal:
    """Build a :class:`MathFrameClaimProposal` with all invariants enforced.

    Invariants (per ADR-0168 §"Decision" + ADR-0168.1 §"Evidence floor")

    1. ``surface_form`` non-empty after normalization.
    2. ``frame_category`` in the ADR-0168 allowlist (also enforced by the
       handler, but rejected here too for defense-in-depth).
    3. ``polarity in {"affirms", "falsifies"}``.
    4. ``len(evidence) >= 1`` — at least one audit/refusal evidence pointer.
    5. every evidence pointer carries ``source="math_audit"`` — corpus
       evidence is rejected as schema-illegal.
    6. proposal_id and claim_signature are derived deterministically.

    Raises ``ValueError`` on any violation; the caller must fix the inputs.
    """

    normalized = surface_form.lower().strip()
    if not normalized:
        raise ValueError(
            f"surface_form must be non-empty after normalization; got {surface_form!r}"
        )

    if frame_category not in _ALLOWLISTED_FRAME_CATEGORIES:
        raise ValueError(
            f"frame_category {frame_category!r} is not in the ADR-0168 allowlist "
            f"{sorted(_ALLOWLISTED_FRAME_CATEGORIES)!r}"
        )

    if polarity not in _VALID_POLARITIES:
        raise ValueError(
            f"polarity must be one of {sorted(_VALID_POLARITIES)!r}; got {polarity!r}"
        )

    if len(evidence) < 1:
        raise ValueError(
            "MathFrameClaimProposal requires at least one math-audit evidence pointer"
        )

    for idx, pointer in enumerate(evidence):
        if pointer.source != "math_audit":
            raise ValueError(
                f"evidence[{idx}].source must be 'math_audit'; got {pointer.source!r} — "
                "audit evidence MUST NOT be laundered as cognition corpus evidence "
                "(ADR-0168.1 §'Evidence floor')"
            )
        if pointer.source in _FORBIDDEN_EVIDENCE_SOURCES:
            raise ValueError(
                f"evidence[{idx}].source is forbidden: {pointer.source!r}"
            )

    claim_signature = compute_claim_signature(
        surface_form=normalized,
        frame_category=frame_category,
        polarity=polarity,
        evidence=evidence,
    )
    proposal_id = compute_proposal_id(
        surface_form=normalized,
        frame_category=frame_category,
        polarity=polarity,
        evidence=evidence,
    )

    return MathFrameClaimProposal(
        proposal_id=proposal_id,
        claim_signature=claim_signature,
        surface_form=normalized,
        frame_category=frame_category,
        polarity=polarity,  # type: ignore[arg-type]
        evidence=tuple(evidence),
        review_state=review_state,
        operator_note=operator_note,
    )


__all__ = [
    "MathFrameClaimProposal",
    "MathReaderRefusalEvidencePointer",
    "Polarity",
    "build_evidence_pointer",
    "build_frame_claim_proposal",
    "canonical_bytes",
    "compute_claim_signature",
    "compute_proposal_id",
]
