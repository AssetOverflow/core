from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.contemplation.schema import (
    ContemplationEvidenceRef,
    ContemplationFinding,
    FindingKind,
)


def mine_learning_arena_report(
    report_path: str | Path,
    *,
    substrate_hash: str,
    min_coverage: float = 0.25,
) -> tuple[ContemplationFinding, ...]:
    """Convert learning-arena report weaknesses into speculative findings.

    Read-only: parses ``report_path`` and returns immutable findings. It never
    writes packs, teaching examples, proposals, or runtime state.
    """
    path = Path(report_path)
    report = json.loads(path.read_text(encoding="utf-8"))
    source_id = str(path)
    findings: list[ContemplationFinding] = []

    for class_name, row in sorted(_per_class(report).items()):
        committed = int(row.get("committed", 0) or 0)
        coverage = float(row.get("coverage", 0.0) or 0.0)
        t2_verified = int(row.get("t2_verified", 0) or 0)
        if coverage < min_coverage:
            evidence = ContemplationEvidenceRef(
                source_type="learning_arena_report",
                source_id=source_id,
                pointer=f"class={class_name}",
                summary=f"coverage={coverage};committed={committed};min={min_coverage}",
            )
            findings.append(
                ContemplationFinding(
                    kind=FindingKind.COVERAGE_GAP,
                    subject=class_name,
                    predicate="weak_coverage",
                    object=None,
                    evidence_refs=(evidence,),
                    proposed_action=(
                        "Inspect refusal diagnoses for this capability class and add "
                        "practice or reviewed operators only where the missing piece is named."
                    ),
                    substrate_hash=substrate_hash,
                )
            )
        if committed > 0 and t2_verified == 0:
            evidence = ContemplationEvidenceRef(
                source_type="learning_arena_report",
                source_id=source_id,
                pointer=f"class={class_name}",
                summary=f"committed={committed};t2_verified=0",
            )
            findings.append(
                ContemplationFinding(
                    kind=FindingKind.UNPROVED_RELATION,
                    subject=class_name,
                    predicate="missing_tier2_evidence",
                    object=None,
                    evidence_refs=(evidence,),
                    proposed_action=(
                        "Add convergent self-verification evidence before promoting this "
                        "class beyond gold-scored practice."
                    ),
                    substrate_hash=substrate_hash,
                )
            )

    for record in report.get("elimination_records", ()) or ():
        if not isinstance(record, dict):
            continue
        case_id = str(record.get("case_id", "unknown_case"))
        class_name = str(record.get("class_name", "unknown_class"))
        evidence = ContemplationEvidenceRef(
            source_type="learning_arena_report",
            source_id=source_id,
            pointer=f"case={case_id}",
            summary=str(record.get("reason", "wrong attempt")),
        )
        findings.append(
            ContemplationFinding(
                kind=FindingKind.BENCHMARK_CASE,
                subject=f"{class_name}/{case_id}",
                predicate="wrong_attempt",
                object=str(record.get("gold", "")),
                evidence_refs=(evidence,),
                proposed_action=(
                    "Use this gold-caught wrong attempt as elimination evidence; do not "
                    "promote the class until the faulty derivation shape is pruned."
                ),
                substrate_hash=substrate_hash,
            )
        )

    return tuple(findings)


def _per_class(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = report.get("per_class", {})
    return {str(k): v for k, v in rows.items() if isinstance(v, dict)}


__all__ = ["mine_learning_arena_report"]
