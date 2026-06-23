"""Schemas for generalization audit items, outcomes, and reports."""

from __future__ import annotations

from dataclasses import dataclass

GENERALIZATION_AUDIT_RUNNER_POLICY_VERSION = "generalization_audit_runner.v1"


@dataclass(frozen=True, slots=True)
class GeneralizationAuditItem:
    """A normalized item representing a single benchmark problem instance for audit."""

    dataset: str
    split: str
    item_id: str
    prompt_ref: str
    answer_kind: str
    metadata: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class GeneralizationAuditOutcome:
    """The result of evaluating a single generalization audit item."""

    item_id: str
    disposition: str  # correct | wrong | refused | unsupported
    residual_kinds: tuple[str, ...]
    candidate_attempt_count: int
    binding_failure_count: int
    replay_refusal_count: int
    sealed_trace_dispositions: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GeneralizationAuditReport:
    """Aggregated report summarizing outcomes across a set of audit items."""

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
    sealed_trace_dispositions: tuple[tuple[str, int], ...]
    dominant_residual_kinds: tuple[tuple[str, int], ...]
    reason_codes: tuple[str, ...]
