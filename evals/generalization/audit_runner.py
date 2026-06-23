"""Generalization audit runner execution logic."""

from __future__ import annotations

from collections import Counter
from typing import Callable

from evals.generalization.item_schema import (
    GENERALIZATION_AUDIT_RUNNER_POLICY_VERSION,
    GeneralizationAuditItem,
    GeneralizationAuditOutcome,
    GeneralizationAuditReport,
)


def run_generalization_audit(
    *,
    dataset: str,
    split: str,
    items: tuple[GeneralizationAuditItem, ...],
    evaluator: Callable[[GeneralizationAuditItem], GeneralizationAuditOutcome],
) -> GeneralizationAuditReport:
    """Executes a generalization audit over a sequence of items using the provided evaluator.

    Args:
        dataset: Name of the dataset under audit.
        split: Name of the dataset split.
        items: Tuple of audit items. Refuses empty items (raises ValueError).
        evaluator: Injected evaluation function mapping an item to an outcome.

    Returns:
        An aggregated, deterministic GeneralizationAuditReport.
    """
    if not items:
        raise ValueError("Audit execution requires a non-empty sequence of items.")

    correct = 0
    wrong = 0
    refused = 0
    unsupported = 0
    candidate_attempts = 0
    binding_failures = 0
    replay_refusals = 0

    sealed_trace_counter: Counter[str] = Counter()
    residual_kind_counter: Counter[str] = Counter()
    reason_codes_set: set[str] = set()

    for item in items:
        try:
            outcome = evaluator(item)
        except Exception as exc:
            # Evaluator exceptions fail closed to refused outcome
            outcome = GeneralizationAuditOutcome(
                item_id=item.item_id,
                disposition="refused",
                residual_kinds=(),
                candidate_attempt_count=0,
                binding_failure_count=0,
                replay_refusal_count=0,
                sealed_trace_dispositions=(),
                reason_codes=("evaluator_exception", type(exc).__name__),
            )

        disp = outcome.disposition
        if disp == "correct":
            correct += 1
        elif disp == "wrong":
            wrong += 1
        elif disp == "refused":
            refused += 1
        elif disp == "unsupported":
            unsupported += 1
        else:
            refused += 1  # Fallback to refused for unrecognized dispositions

        candidate_attempts += outcome.candidate_attempt_count
        binding_failures += outcome.binding_failure_count
        replay_refusals += outcome.replay_refusal_count

        for d in outcome.sealed_trace_dispositions:
            sealed_trace_counter[d] += 1
        for r in outcome.residual_kinds:
            residual_kind_counter[r] += 1
        reason_codes_set.update(outcome.reason_codes)

    # Sort histograms descending by count, then alphabetically by key for determinism
    sorted_sealed_traces = tuple(
        sorted(sealed_trace_counter.items(), key=lambda x: (-x[1], x[0]))
    )
    sorted_residual_kinds = tuple(
        sorted(residual_kind_counter.items(), key=lambda x: (-x[1], x[0]))
    )

    return GeneralizationAuditReport(
        policy_version=GENERALIZATION_AUDIT_RUNNER_POLICY_VERSION,
        dataset=dataset,
        split=split,
        n_items=len(items),
        correct=correct,
        wrong=wrong,
        refused=refused,
        unsupported=unsupported,
        candidate_attempts=candidate_attempts,
        binding_failures=binding_failures,
        replay_refusals=replay_refusals,
        sealed_trace_dispositions=sorted_sealed_traces,
        dominant_residual_kinds=sorted_residual_kinds,
        reason_codes=tuple(sorted(reason_codes_set)),
    )
