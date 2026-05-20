from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.contemplation.schema import (
    ContemplationEvidenceRef,
    ContemplationFinding,
    FindingKind,
)


_MISSED = "missed_contradiction"
_FALSE_FLAG = "false_contradiction_flag"


def _case_iter(report: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple(c for c in report.get("cases", ()) if isinstance(c, dict))


def _failure_mode(case: dict[str, Any]) -> str | None:
    """Classify a failed contradiction-detection case.

    Returns the predicate for the emitted finding, or ``None`` if the
    case is not a failure worth flagging.
    """
    if bool(case.get("passed", True)):
        return None
    kind = str(case.get("kind", ""))
    if kind == "paired_contradiction":
        return _MISSED
    if kind == "paired_consistent":
        return _FALSE_FLAG
    return None


def _evidence_summary(case: dict[str, Any]) -> str:
    """Compact, deterministic one-line evidence summary.

    Captures the lane's quantitative signals so a reviewer can decide
    without re-running the lane.  Keys are sorted to keep the summary
    stable across runs.
    """
    keys = ("kind", "flagged", "contested", "versor_delta", "versor_spike")
    parts = [f"{k}={case[k]}" for k in keys if k in case]
    return ";".join(parts) if parts else "case failed"


def mine_contradiction_detection_report(
    report_path: str | Path,
    *,
    substrate_hash: str,
) -> tuple[ContemplationFinding, ...]:
    """Convert failed contradiction-detection cases into speculative findings.

    Two failure modes are surfaced as distinct predicates:

      - ``missed_contradiction`` — a ``paired_contradiction`` case
        the lane failed to flag (a real contradiction slipped through).
      - ``false_contradiction_flag`` — a ``paired_consistent`` case
        the lane wrongly flagged (the detector fired on consistent text).

    Both warrant operator attention but call for different repairs, so
    the predicate split is load-bearing — not cosmetic.

    Read-only: parses ``report_path`` and returns immutable findings.
    Never writes packs, teaching corpora, or runtime state.
    """
    path = Path(report_path)
    report = json.loads(path.read_text(encoding="utf-8"))
    findings: list[ContemplationFinding] = []
    source_id = str(path)
    lane = str(report.get("lane", "contradiction_detection"))

    for case in _case_iter(report):
        predicate = _failure_mode(case)
        if predicate is None:
            continue
        case_id = str(case.get("id", "unknown_case"))
        evidence = ContemplationEvidenceRef(
            source_type="contradiction_detection_report",
            source_id=source_id,
            pointer=f"lane={lane};case={case_id}",
            summary=_evidence_summary(case),
        )
        proposed_action = (
            "Inspect the paired-contradiction probe that slipped through; "
            "either tighten the detector's versor-delta threshold or add a "
            "focused regression for this case."
            if predicate == _MISSED
            else "Inspect the paired-consistent probe the detector wrongly "
            "flagged; either loosen the threshold or add a counter-example "
            "regression that pins the consistent reading."
        )
        findings.append(
            ContemplationFinding(
                kind=FindingKind.CONTRADICTION,
                subject=f"{lane}/{case_id}",
                predicate=predicate,
                object=None,
                evidence_refs=(evidence,),
                proposed_action=proposed_action,
                substrate_hash=substrate_hash,
            )
        )

    return tuple(findings)


__all__ = ["mine_contradiction_detection_report"]
