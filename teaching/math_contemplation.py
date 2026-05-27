"""ADR-0167 W2-A / W2-B — Audit-to-evidence adapter + lexical claim signature.

W2-A deliverable: :func:`audit_to_evidence` and
:func:`audit_problem_to_evidence` convert :class:`AuditRow` sequences into
typed :class:`MathReaderRefusalEvidence` teaching-corridor records.

W2-B deliverable: For ``sub_type == "lexical"`` evidence, ``claim_signature``
is computed via :func:`lexical_claim_signature` and the ``evidence_hash`` is
recomputed to incorporate the signature.  All other sub_types leave
``claim_signature == ""``.

Pure module.  No filesystem writes, no network calls, no global mutation.
Deterministic: same inputs → byte-identical output across all reruns.
"""

from __future__ import annotations

from typing import Iterable

from generate.comprehension.audit import AuditRow, audit_problem
from teaching.math_claim_signature import lexical_claim_signature
from teaching.math_evidence import (
    MathReaderRefusalEvidence,
    SUB_TYPE_FOR_OPERATOR,
    from_audit_row,
)


def audit_to_evidence(
    audit_rows: Iterable[AuditRow],
) -> tuple[MathReaderRefusalEvidence, ...]:
    """Convert audit rows into typed teaching-corridor evidence records.

    Pure function.  Deterministic.  No filesystem, no network, no mutation.
    Sub-type assignment from :data:`teaching.math_evidence.SUB_TYPE_FOR_OPERATOR`.
    Skips rows with ``missing_operator=None`` (no sub_type → no candidate).

    For ``sub_type == "lexical"``, :func:`lexical_claim_signature` fills the
    ``claim_signature`` field and the ``evidence_hash`` incorporates it.
    For all other sub_types, ``claim_signature`` remains ``""`` (deferred).

    Input order is preserved.

    Parameters
    ----------
    audit_rows:
        Iterable of :class:`AuditRow` instances (e.g. from :func:`audit_problem`).

    Returns
    -------
    tuple[MathReaderRefusalEvidence, ...]
        One record per row whose ``missing_operator`` maps to a known sub_type.
    """
    results: list[MathReaderRefusalEvidence] = []
    for row in audit_rows:
        if row.missing_operator is None:
            continue
        sub_type = SUB_TYPE_FOR_OPERATOR.get(row.missing_operator)
        if sub_type is None:
            continue
        if sub_type == "lexical":
            sig = lexical_claim_signature(
                surface=row.token_text,
                refusal_detail=row.refusal_detail,
            )
        else:
            sig = ""
        evidence = from_audit_row(row, sub_type, claim_signature=sig)
        results.append(evidence)
    return tuple(results)


def audit_problem_to_evidence(
    problem_text: str,
    *,
    case_id: str,
) -> tuple[MathReaderRefusalEvidence, ...]:
    """Run the reader over *problem_text* and return evidence records.

    Convenience wrapper that calls :func:`audit_problem` and pipes the
    resulting :class:`AuditRow` list through :func:`audit_to_evidence`.
    Useful for tests and downstream pipeline work (W3-A).

    Parameters
    ----------
    problem_text:
        Raw GSM8K-style problem string.
    case_id:
        Identifier attached to every :class:`AuditRow` (e.g. ``"probe"``).

    Returns
    -------
    tuple[MathReaderRefusalEvidence, ...]
        Evidence records for any refusals encountered.  Empty tuple on full
        admission or if the text produced no sentences.
    """
    _result, rows = audit_problem(problem_text, case_id=case_id)
    return audit_to_evidence(rows)


__all__ = [
    "audit_to_evidence",
    "audit_problem_to_evidence",
]
