"""Brief D — coverage report aggregator for math eval lanes.

Reads the lane's ``report.json`` and emits a per-ShapeCategory
refusal histogram with optional delta-vs-committed-baseline. Pure
read; no side effects on lane state. Used by
``core teaching coverage``.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


_REASON_CATEGORY_RE: re.Pattern[str] = re.compile(r"\(category=([a-z_]+)\)")


@dataclass(frozen=True, slots=True)
class CoverageCounts:
    correct: int
    refused: int
    wrong: int

    def total(self) -> int:
        return self.correct + self.refused + self.wrong


@dataclass(frozen=True, slots=True)
class CoverageReport:
    lane: str
    split: str
    version: str
    counts: CoverageCounts
    refusal_taxonomy: Mapping[str, int]
    case_0050_verdict: str | None
    delta: Mapping[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "lane": self.lane,
            "split": self.split,
            "version": self.version,
            "counts": {
                "correct": self.counts.correct,
                "refused": self.counts.refused,
                "wrong": self.counts.wrong,
                "total": self.counts.total(),
            },
            "refusal_taxonomy": dict(self.refusal_taxonomy),
            "case_0050_verdict": self.case_0050_verdict,
            "delta": dict(self.delta),
        }


def _classify_refusal(reason: str) -> str:
    """Map a per-case refusal reason string to a stable category bucket.

    Matching is case-insensitive throughout — the raw runner output is
    consistently lowercase prose today, but normalizing once avoids
    drift if upstream casing changes.

    Buckets:
    - ``recognizer_empty_injection(<ShapeCategory>)`` — recognizer
      matched but the per-category injector returned empty
    - ``no_admissible_question`` — statement(s) admitted; question
      parser refused
    - ``no_admissible_statement`` — neither parser nor recognizer
      admitted any statement
    - ``unexpected_question_count`` — !=1 question sentence
    - ``other`` — any unmatched reason text
    """
    if not reason:
        return "other"
    lower = reason.lower()
    if "recognizer matched but produced no injection" in lower:
        m = _REASON_CATEGORY_RE.search(lower)
        cat = m.group(1) if m else "unknown"
        return f"recognizer_empty_injection({cat})"
    if "no admissible candidate for question" in lower:
        return "no_admissible_question"
    if "no admissible candidate for statement" in lower:
        return "no_admissible_statement"
    if "expected exactly one question sentence" in lower:
        return "unexpected_question_count"
    return "other"


def build_coverage_report(
    report_path: Path,
    *,
    lane: str,
    split: str,
    version: str,
    baseline_path: Path | None = None,
) -> CoverageReport:
    """Build a :class:`CoverageReport` from a runner-emitted report.json.

    Optional ``baseline_path`` enables a delta computation.
    """
    if not report_path.exists():
        raise FileNotFoundError(f"report.json not found at {report_path}")
    data = json.loads(report_path.read_text(encoding="utf-8"))
    counts_raw = data.get("counts") or {}
    counts = CoverageCounts(
        correct=int(counts_raw.get("correct", 0)),
        refused=int(counts_raw.get("refused", 0)),
        wrong=int(counts_raw.get("wrong", 0)),
    )

    per_case = data.get("per_case") or []
    taxonomy: dict[str, int] = {}
    case_0050_verdict: str | None = None
    for case in per_case:
        verdict = case.get("verdict")
        cid = case.get("case_id", "")
        if cid.endswith("-0050"):
            case_0050_verdict = verdict
        if verdict != "refused":
            continue
        bucket = _classify_refusal(case.get("reason") or "")
        taxonomy[bucket] = taxonomy.get(bucket, 0) + 1

    # Sort taxonomy by count desc, then alpha for stable output.
    sorted_taxonomy = dict(
        sorted(taxonomy.items(), key=lambda kv: (-kv[1], kv[0]))
    )

    delta: dict[str, int] = {}
    if baseline_path is not None and baseline_path.exists():
        try:
            base_data = json.loads(baseline_path.read_text(encoding="utf-8"))
            base_counts = base_data.get("counts") or {}
            delta = {
                "correct": counts.correct - int(base_counts.get("correct", 0)),
                "refused": counts.refused - int(base_counts.get("refused", 0)),
                "wrong": counts.wrong - int(base_counts.get("wrong", 0)),
            }
        except (json.JSONDecodeError, KeyError, TypeError):
            delta = {}

    return CoverageReport(
        lane=lane,
        split=split,
        version=version,
        counts=counts,
        refusal_taxonomy=sorted_taxonomy,
        case_0050_verdict=case_0050_verdict,
        delta=delta,
    )


def fetch_committed_baseline(
    report_relpath: str,
    repo_root: Path,
) -> Path | None:
    """Return a temp path containing HEAD's committed report.json, or None.

    Uses ``git show HEAD:<relpath>``. Falls back to None on any git
    error so the CLI doesn't depend on git availability.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"HEAD:{report_relpath}"],
            capture_output=True,
            check=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    if not result.stdout.strip():
        return None
    # Use the system temp dir with a unique filename to avoid:
    # (a) failures in non-git checkouts or worktrees where .git is a
    #     file pointing elsewhere
    # (b) concurrent-access collisions if two operators run
    #     ``core teaching coverage --delta`` simultaneously
    fd, tmp_path = tempfile.mkstemp(
        prefix="core_coverage_baseline_", suffix=".json"
    )
    try:
        with open(fd, "w", encoding="utf-8") as fh:
            fh.write(result.stdout)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        return None
    return Path(tmp_path)


__all__ = [
    "CoverageCounts",
    "CoverageReport",
    "build_coverage_report",
    "fetch_committed_baseline",
]
