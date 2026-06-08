"""Deterministic review report over the scanned proposals (RPT-b).

A pure projection of the scan results into a summary: total pending, counts by failure_family,
counts by status, the malformed count, and the review-needed list. Deterministic given the sink
contents (no clock): counts are sorted, the review-needed list is sorted by content hash.

Time-based "oldest/newest" is intentionally **omitted**: the proposal artifacts are
content-addressed and carry no timestamp (the emitter is clock-free for idempotence), so an honest
temporal ordering is not available from the data — only from non-deterministic filesystem mtime,
which would make this report non-deterministic. A human can sort the sink by mtime if needed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from core.proposal_review.model import MalformedArtifact, PendingProposal


@dataclass(frozen=True, slots=True)
class ProposalReviewReport:
    """A deterministic snapshot of the review obligations in the proposal sink."""

    total: int
    by_family: dict[str, int]
    by_status: dict[str, int]
    malformed: int
    review_needed: tuple[str, ...]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "by_family": self.by_family,
            "by_status": self.by_status,
            "malformed": self.malformed,
            "review_needed": list(self.review_needed),
        }


def build_report(
    proposals: list[PendingProposal], malformed: list[MalformedArtifact]
) -> ProposalReviewReport:
    by_family: dict[str, int] = {}
    by_status: dict[str, int] = {}
    review_needed: list[str] = []
    for p in proposals:
        by_family[p.failure_family] = by_family.get(p.failure_family, 0) + 1
        by_status[p.status] = by_status.get(p.status, 0) + 1
        if p.requires_review:
            review_needed.append(p.content_hash)
    return ProposalReviewReport(
        total=len(proposals),
        by_family=dict(sorted(by_family.items())),
        by_status=dict(sorted(by_status.items())),
        malformed=len(malformed),
        review_needed=tuple(sorted(review_needed)),
    )


def report_json(report: ProposalReviewReport) -> str:
    """Deterministic JSON (sorted keys)."""
    return json.dumps(report.to_json_dict(), indent=2, sort_keys=True)


def report_text(report: ProposalReviewReport) -> str:
    """Human-readable summary."""
    lines = [
        f"comprehension-failure proposals: {report.total} pending · {report.malformed} malformed",
        "  by family:",
        *(f"    {fam}: {n}" for fam, n in report.by_family.items()),
        "  by status:",
        *(f"    {status}: {n}" for status, n in report.by_status.items()),
        f"  review-needed: {len(report.review_needed)}",
    ]
    return "\n".join(lines)


__all__ = ["ProposalReviewReport", "build_report", "report_json", "report_text"]
