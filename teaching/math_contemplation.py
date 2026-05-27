"""ADR-0167 W2-A — audit-to-evidence adapter.

Pure deterministic conversion from comprehension audit rows into typed
``MathReaderRefusalEvidence`` records for the teaching corridor.
"""

from __future__ import annotations

from typing import Iterable

from generate.comprehension.audit import AuditRow, audit_problem
from teaching.math_evidence import (
    MathReaderRefusalEvidence,
    SUB_TYPE_FOR_OPERATOR,
    from_audit_row,
)


def audit_to_evidence(
    audit_rows: Iterable[AuditRow],
) -> tuple[MathReaderRefusalEvidence, ...]:
    """Convert audit rows into typed teaching-corridor evidence records.

    Pure function. Deterministic. No filesystem, no network, no mutation.
    Sub-type assignment from ``teaching.math_evidence.SUB_TYPE_FOR_OPERATOR``.
    Skips rows with ``missing_operator=None`` (no sub_type → no candidate).
    """
    out: list[MathReaderRefusalEvidence] = []
    for row in audit_rows:
        if row.missing_operator is None:
            continue
        sub_type = SUB_TYPE_FOR_OPERATOR[row.missing_operator]
        out.append(from_audit_row(row, sub_type, claim_signature=""))
    return tuple(out)


def audit_problem_to_evidence(
    problem_text: str,
    *,
    case_id: str,
) -> tuple[MathReaderRefusalEvidence, ...]:
    """Run reader audit on ``problem_text`` and return mapped evidence rows."""
    _result, rows = audit_problem(problem_text, case_id=case_id)
    return audit_to_evidence(rows)


__all__ = ["audit_problem_to_evidence", "audit_to_evidence"]
