"""ADR-0167 W1-A — MathReaderRefusalEvidence schema + canonical-bytes.

Typed record wrapping an :class:`AuditRow` from the comprehension reader's
refusal taxonomy.  Every downstream Wave 2 brief (W2-A through W2-D)
type-imports :class:`MathReaderRefusalEvidence` and
:data:`SUB_TYPE_FOR_OPERATOR` from this module.

This module is a standalone schema — it does not mutate any teaching store,
pack, or runtime state.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Final, Literal

from generate.comprehension.audit import AuditRow

# ---------------------------------------------------------------------------
# Sub-type literal
# ---------------------------------------------------------------------------

SubType = Literal["lexical", "frame", "composition", "reference", "slot"]

SUB_TYPE_FOR_OPERATOR: Final[dict[str, SubType]] = {
    "lexicon_entry": "lexical",
    "compound_numeric_literal": "lexical",
    "compound_time_literal": "lexical",
    "pre_frame_filler_sentence": "frame",
    "multi_quantity_composition": "composition",
    "quantity_extraction": "composition",
    "pronoun_resolution": "reference",
    "question_frame_slot": "slot",
    "unit_binding": "slot",
    "fraction_percentage_literal": "lexical",  # provisional
    "multi_subject_sentence": "frame",
    "question_target_slot": "slot",
    "descriptive_frame_question": "slot",
}

# ---------------------------------------------------------------------------
# Canonical-bytes helpers (mirrors generate/comprehension/state.py pattern)
# ---------------------------------------------------------------------------


class _OmitSentinel:
    __slots__ = ()


_OMIT = _OmitSentinel()


def _canonical_value(obj: Any) -> Any:
    """Recursively convert to a canonical JSON-serialisable value.

    None → sentinel _OMIT (caller drops from dict).
    Tuples/lists → JSON arrays.  Dataclasses → sorted-key dicts.
    """
    if obj is None:
        return _OMIT
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (tuple, list)):
        return [_canonical_value(item) for item in obj]
    if hasattr(obj, "__dataclass_fields__"):
        out: dict[str, Any] = {}
        for key in sorted(obj.__dataclass_fields__.keys()):
            val = _canonical_value(getattr(obj, key))
            if val is not _OMIT:
                out[key] = val
        return out
    raise TypeError(
        f"_canonical_value: cannot serialise {type(obj).__name__}"
    )


def _to_canonical_bytes_for_evidence(
    evidence: MathReaderRefusalEvidence,
) -> bytes:
    """Produce deterministic canonical bytes, excluding evidence_hash itself."""
    out: dict[str, Any] = {}
    for key in sorted(evidence.__dataclass_fields__.keys()):
        if key == "evidence_hash":
            continue
        val = _canonical_value(getattr(evidence, key))
        if val is not _OMIT:
            out[key] = val
    return json.dumps(
        out,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Evidence record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MathReaderRefusalEvidence:
    """Typed record binding a comprehension-reader refusal to the teaching corridor.

    Construct via :func:`from_audit_row` — do not instantiate directly.
    """

    case_id: str
    sentence_index: int
    token_index: int
    refusal_reason: str
    missing_operator: str | None
    claim_signature: str
    evidence_hash: str
    audit_row: AuditRow
    sub_type: SubType

    def to_canonical_bytes(self) -> bytes:
        """Deterministic canonical bytes (evidence_hash excluded)."""
        return _to_canonical_bytes_for_evidence(self)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def from_audit_row(
    audit_row: AuditRow,
    sub_type: SubType,
    *,
    claim_signature: str = "",
) -> MathReaderRefusalEvidence:
    """Build a :class:`MathReaderRefusalEvidence` from an audit row.

    The ``evidence_hash`` is computed from the canonical bytes of all other
    fields.  ``claim_signature`` defaults to ``""`` in W1-A; W2-B fills it.
    """
    placeholder_hash = ""
    record = MathReaderRefusalEvidence(
        case_id=audit_row.case_id,
        sentence_index=audit_row.sentence_index,
        token_index=audit_row.token_index,
        refusal_reason=audit_row.refusal_reason,
        missing_operator=audit_row.missing_operator,
        claim_signature=claim_signature,
        evidence_hash=placeholder_hash,
        audit_row=audit_row,
        sub_type=sub_type,
    )
    canonical = record.to_canonical_bytes()
    real_hash = hashlib.sha256(canonical).hexdigest()
    object.__setattr__(record, "evidence_hash", real_hash)
    return record


__all__ = [
    "MathReaderRefusalEvidence",
    "SUB_TYPE_FOR_OPERATOR",
    "SubType",
    "from_audit_row",
]
