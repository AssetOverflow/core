from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.contemplation.schema import (
    ContemplationEvidenceRef,
    ContemplationFinding,
    FindingKind,
)


def _suite_iter(report: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    if "suites" in report:
        return tuple(s for s in report.get("suites", ()) if isinstance(s, dict))
    if "suite" in report:
        return (report,)
    return ()


def _case_iter(suite: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple(c for c in suite.get("cases", ()) if isinstance(c, dict))


def mine_frontier_compare_report(
    report_path: str | Path,
    *,
    substrate_hash: str,
) -> tuple[ContemplationFinding, ...]:
    """Convert failed frontier-compare cases into speculative findings.

    Read-only: this function only parses *report_path* and returns immutable
    findings.  It does not write reports, packs, teaching examples, or runtime
    state.
    """

    path = Path(report_path)
    report = json.loads(path.read_text(encoding="utf-8"))
    findings: list[ContemplationFinding] = []
    source_id = str(path)

    for suite in _suite_iter(report):
        suite_name = str(suite.get("suite", "unknown_suite"))
        for case in _case_iter(suite):
            if bool(case.get("passed", False)):
                continue
            case_id = str(case.get("case_id", "unknown_case"))
            prompt = str(case.get("prompt", ""))
            failures = tuple(str(f) for f in case.get("failures", ()) or ())
            evidence = ContemplationEvidenceRef(
                source_type="frontier_compare_report",
                source_id=source_id,
                pointer=f"suite={suite_name};case={case_id}",
                summary=", ".join(failures) if failures else "case failed",
            )
            findings.append(
                ContemplationFinding(
                    kind=FindingKind.BENCHMARK_CASE,
                    subject=f"{suite_name}/{case_id}",
                    predicate="failed_case",
                    object=prompt,
                    evidence_refs=(evidence,),
                    proposed_action=(
                        "Review this failed benchmark case; either repair the runtime/pack "
                        "behavior or promote the case into a focused regression/curriculum item."
                    ),
                    substrate_hash=substrate_hash,
                )
            )

    return tuple(findings)


__all__ = ["mine_frontier_compare_report"]
