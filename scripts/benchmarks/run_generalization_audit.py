#!/usr/bin/env python3
"""CLI script to run generalization audit (skeleton)."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

# Resolve repository root and add to sys.path to support imports
script_path = Path(__file__).resolve()
repo_root = script_path.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from evals.generalization.audit_runner import run_generalization_audit  # noqa: E402
from evals.generalization.item_schema import (  # noqa: E402
    GeneralizationAuditItem,
    GeneralizationAuditOutcome,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run generalization audit.")
    parser.add_argument(
        "--synthetic-smoke",
        action="store_true",
        help="Run a synthetic smoke audit.",
    )
    parser.add_argument("--dataset", type=str, help="Name of the dataset to audit.")
    parser.add_argument(
        "--split", type=str, default="test", help="Dataset split to audit."
    )
    parser.add_argument(
        "--json", action="store_true", help="Print report in deterministic JSON format."
    )

    args = parser.parse_args()

    if not args.synthetic_smoke and not args.dataset:
        print(
            "Error: Either --synthetic-smoke or --dataset <name> must be specified.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.dataset:
        # In PR-2, no real dataset adapters exist, so we fail with the required error code
        print("Error: dataset_adapter_unavailable", file=sys.stderr)
        sys.exit(1)

    if args.synthetic_smoke:
        # Generate synthetic items and run smoke audit
        items = (
            GeneralizationAuditItem(
                dataset="SYNTHETIC_SMOKE",
                split="test",
                item_id="item_1",
                prompt_ref="synthetic:smoke:item_1",
                answer_kind="numeric_text",
                metadata=(("difficulty", "easy"),),
            ),
            GeneralizationAuditItem(
                dataset="SYNTHETIC_SMOKE",
                split="test",
                item_id="item_2",
                prompt_ref="synthetic:smoke:item_2",
                answer_kind="numeric_text",
                metadata=(("difficulty", "medium"),),
            ),
            GeneralizationAuditItem(
                dataset="SYNTHETIC_SMOKE",
                split="test",
                item_id="item_3",
                prompt_ref="synthetic:smoke:item_3",
                answer_kind="numeric_text",
                metadata=(("difficulty", "hard"),),
            ),
        )

        def synthetic_evaluator(
            item: GeneralizationAuditItem,
        ) -> GeneralizationAuditOutcome:
            if item.item_id == "item_1":
                return GeneralizationAuditOutcome(
                    item_id=item.item_id,
                    disposition="correct",
                    residual_kinds=("none",),
                    candidate_attempt_count=1,
                    binding_failure_count=0,
                    replay_refusal_count=0,
                    sealed_trace_dispositions=("success",),
                    reason_codes=(),
                )
            elif item.item_id == "item_2":
                return GeneralizationAuditOutcome(
                    item_id=item.item_id,
                    disposition="wrong",
                    residual_kinds=("numeric_precision",),
                    candidate_attempt_count=2,
                    binding_failure_count=0,
                    replay_refusal_count=0,
                    sealed_trace_dispositions=("fail", "success"),
                    reason_codes=("wrong_value",),
                )
            else:
                return GeneralizationAuditOutcome(
                    item_id=item.item_id,
                    disposition="refused",
                    residual_kinds=(),
                    candidate_attempt_count=1,
                    binding_failure_count=1,
                    replay_refusal_count=1,
                    sealed_trace_dispositions=("refused",),
                    reason_codes=("safety_policy",),
                )

        try:
            report = run_generalization_audit(
                dataset="SYNTHETIC_SMOKE",
                split="test",
                items=items,
                evaluator=synthetic_evaluator,
            )
        except Exception as exc:
            print(f"Audit Failed: {exc}", file=sys.stderr)
            sys.exit(1)

        if args.json:
            print(json.dumps(asdict(report), indent=2, sort_keys=True))
        else:
            print(
                f"Generalization Audit Report (Policy: {report.policy_version})"
            )
            print("=" * 80)
            print(f"Dataset:                  {report.dataset}")
            print(f"Split:                    {report.split}")
            print(f"Total Items:              {report.n_items}")
            print(f"Correct:                  {report.correct}")
            print(f"Wrong:                    {report.wrong}")
            print(f"Refused:                  {report.refused}")
            print(f"Unsupported:              {report.unsupported}")
            print(f"Candidate Attempts:       {report.candidate_attempts}")
            print(f"Binding Failures:         {report.binding_failures}")
            print(f"Replay Refusals:          {report.replay_refusals}")
            print(f"Sealed Trace Dispositions: {report.sealed_trace_dispositions}")
            print(f"Dominant Residual Kinds:  {report.dominant_residual_kinds}")
            print(f"Reason Codes:             {', '.join(report.reason_codes)}")
            print("=" * 80)

        sys.exit(0)


if __name__ == "__main__":
    main()
