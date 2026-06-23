"""Read-only generalization audit evidence projections for Workbench.

Generalization benchmark data is audit/test-only. This module deliberately models
aggregate report metadata only. It must not expose raw prompt/question/answer
content, sealed item payloads, or direct patch suggestions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ChecksumStatus = Literal["verified", "missing", "mismatch", "unknown"]
ReportKind = Literal["committed_pin", "ephemeral_local", "rebaseline_candidate", "unknown"]

FORBIDDEN_RAW_ITEM_KEYS = frozenset(
    {
        "prompt",
        "question",
        "answer",
        "gold_answer",
        "raw_item",
        "raw_items",
        "items",
        "examples",
        "sealed_items",
    }
)


@dataclass(frozen=True, slots=True)
class GeneralizationManifestSummary:
    dataset: str
    manifest_path: str
    split_names: list[str]
    license: str | None
    checksum_status: ChecksumStatus
    sealed_splits: list[str]
    policy_version: str


@dataclass(frozen=True, slots=True)
class GeneralizationCacheStatus:
    dataset: str
    cache_path: str
    present: bool
    verified: bool
    reason: str | None


@dataclass(frozen=True, slots=True)
class GeneralizationAuditReportView:
    policy_version: str
    dataset: str
    split: str
    n_items: int
    correct: int
    wrong: int
    refused: int
    unsupported: int
    candidate_attempts: int
    binding_failures: int
    replay_refusals: int
    sealed_trace_dispositions: list[tuple[str, int]] = field(default_factory=list)
    dominant_residual_kinds: list[tuple[str, int]] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    source_path: str | None = None
    source_digest: str | None = None
    report_kind: ReportKind = "unknown"
    audit_only: bool = True
    raw_items_exposed: bool = False


def contains_forbidden_raw_item_keys(payload: Any) -> bool:
    """Return True if a payload contains raw/sealed item keys anywhere."""

    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) in FORBIDDEN_RAW_ITEM_KEYS:
                return True
            if contains_forbidden_raw_item_keys(value):
                return True
    elif isinstance(payload, list):
        return any(contains_forbidden_raw_item_keys(item) for item in payload)
    return False


def _count_pairs(value: Any) -> list[tuple[str, int]]:
    if not isinstance(value, dict):
        return []
    pairs: list[tuple[str, int]] = []
    for key, count in sorted(value.items(), key=lambda item: str(item[0])):
        try:
            pairs.append((str(key), int(count)))
        except (TypeError, ValueError):
            continue
    return pairs


def generalization_report_view_from_payload(
    payload: dict[str, Any],
    *,
    source_path: str | None = None,
    source_digest: str | None = None,
    report_kind: ReportKind = "unknown",
) -> GeneralizationAuditReportView:
    """Project an aggregate audit report into a Workbench-safe view.

    This function is intentionally aggregate-only. It rejects payloads that carry
    obvious raw/sealed item fields so the Workbench cannot accidentally render
    benchmark examples or answers.
    """

    if contains_forbidden_raw_item_keys(payload):
        raise ValueError("generalization report payload exposes raw item fields")

    return GeneralizationAuditReportView(
        policy_version=str(payload.get("policy_version") or "unknown"),
        dataset=str(payload.get("dataset") or "unknown"),
        split=str(payload.get("split") or "unknown"),
        n_items=int(payload.get("n_items") or 0),
        correct=int(payload.get("correct") or 0),
        wrong=int(payload.get("wrong") or 0),
        refused=int(payload.get("refused") or 0),
        unsupported=int(payload.get("unsupported") or 0),
        candidate_attempts=int(payload.get("candidate_attempts") or 0),
        binding_failures=int(payload.get("binding_failures") or 0),
        replay_refusals=int(payload.get("replay_refusals") or 0),
        sealed_trace_dispositions=_count_pairs(payload.get("sealed_trace_dispositions")),
        dominant_residual_kinds=_count_pairs(payload.get("dominant_residual_kinds")),
        reason_codes=[str(code) for code in payload.get("reason_codes") or []],
        source_path=source_path,
        source_digest=source_digest,
        report_kind=report_kind,
        audit_only=True,
        raw_items_exposed=False,
    )


def generalization_audit_banner() -> str:
    return (
        "Audit-only. No raw sealed items are exposed here. Benchmark failures are "
        "diagnosis signals, not direct mutation targets."
    )
