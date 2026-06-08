"""Pure idle-use summary of the proposal sink (IT-a).

``idle_summary`` composes the landed read-only pieces — ``scan`` (RPT-a) + ``build_report``
(RPT-b) + ``dry_check`` (RPT-c) — into one small, JSON-safe value the runtime's ``idle_tick``
can surface (IT-b) without importing the reporter's internals. Pure read: no mutation, no clock.

The summary is deliberately primitives-only (no paths, no raw file content, no mutable dicts) so
it is trivially serializable if ``IdleTickResult`` is ever persisted. ``errors`` carries the
reason the sink is not ``safe`` — the dry-check violations here; IT-b additionally uses it to
record a captured reporter exception (``proposal_review_failed:<type>``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.proposal_review.report import build_report
from core.proposal_review.safety import dry_check
from core.proposal_review.scan import scan


@dataclass(frozen=True, slots=True)
class ProposalReviewIdleSummary:
    """A JSON-safe snapshot of the proposal sink for idle surfacing. ``safe`` is the dry-check
    verdict; ``errors`` is empty iff safe (or carries ``proposal_review_failed:<type>`` when the
    reporter itself raised, set by the runtime sub-pass)."""

    safe: bool
    total: int
    review_needed: int
    malformed: int
    by_family: tuple[tuple[str, int], ...]
    errors: tuple[str, ...] = ()


def idle_summary(root: Path | None = None) -> ProposalReviewIdleSummary:
    """Scan → report → dry-check the proposal sink into a JSON-safe idle summary. Pure read."""
    proposals, malformed = scan(root)
    report = build_report(proposals, malformed)
    verdict = dry_check(proposals, malformed, root=root)
    return ProposalReviewIdleSummary(
        safe=verdict.ok,
        total=report.total,
        review_needed=len(report.review_needed),
        malformed=report.malformed,
        by_family=tuple(report.by_family.items()),
        errors=verdict.violations,
    )


__all__ = ["ProposalReviewIdleSummary", "idle_summary"]
