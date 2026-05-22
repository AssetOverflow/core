"""Runner for evals/reviewer_registry/ (ADR-0092).

Iterates over the case fixtures under ``cases/`` and asserts each one's
load outcome matches its declared expectation. Emits a deterministic
JSON report to ``results/v1_dev.json``.

Exit code is non-zero on any divergence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from core.capability.reviewers import (
    ReviewerRegistryError,
    load_reviewer_registry,
)


CASE_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "positive_primary.yaml": {
        "expected_outcome": "load_ok",
        "expected_reviewer_count": 1,
        "expected_reviewer_ids": ["shay-j"],
        "purpose": "single primary reviewer loads cleanly",
    },
    "positive_domain.yaml": {
        "expected_outcome": "load_ok",
        "expected_reviewer_count": 1,
        "expected_reviewer_ids": ["math-reviewer"],
        "purpose": "single domain reviewer loads cleanly",
    },
    "negative_empty.yaml": {
        "expected_outcome": "load_ok",
        "expected_reviewer_count": 0,
        "expected_reviewer_ids": [],
        "purpose": "empty registry loads but blocks reasoning-capable claims",
    },
    "negative_wrong_version.yaml": {
        "expected_outcome": "reject",
        "expected_error_substring": "schema_version",
        "purpose": "non-v1 schema rejected before any reviewer parsed",
    },
    "negative_domain_wildcard.yaml": {
        "expected_outcome": "reject",
        "expected_error_substring": "wildcard",
        "purpose": "domain reviewer claiming '*' rejected",
    },
    "negative_unknown_field.yaml": {
        "expected_outcome": "reject",
        "expected_error_substring": "unknown fields",
        "purpose": "unknown reviewer field rejected",
    },
}


def _evaluate_case(path: Path, expectation: dict[str, Any]) -> dict[str, Any]:
    actual: dict[str, Any] = {"case_id": path.name, "purpose": expectation["purpose"]}

    try:
        registry = load_reviewer_registry(path)
    except ReviewerRegistryError as exc:
        actual["actual_outcome"] = "reject"
        actual["actual_error"] = str(exc)
        actual["registry"] = None
    else:
        actual["actual_outcome"] = "load_ok"
        actual["actual_error"] = None
        actual["registry"] = {
            "schema_version": registry.schema_version,
            "reviewer_count": len(registry.reviewers),
            "reviewer_ids": sorted(r.reviewer_id for r in registry.reviewers),
        }

    if actual["actual_outcome"] != expectation["expected_outcome"]:
        actual["passed"] = False
        actual["divergence"] = (
            f"expected {expectation['expected_outcome']!r} got "
            f"{actual['actual_outcome']!r}"
        )
        return actual

    if expectation["expected_outcome"] == "load_ok":
        registry_data = actual["registry"]
        assert registry_data is not None  # narrowed by branch
        if registry_data["reviewer_count"] != expectation["expected_reviewer_count"]:
            actual["passed"] = False
            actual["divergence"] = (
                f"expected reviewer_count={expectation['expected_reviewer_count']} got "
                f"{registry_data['reviewer_count']}"
            )
            return actual
        if registry_data["reviewer_ids"] != expectation["expected_reviewer_ids"]:
            actual["passed"] = False
            actual["divergence"] = (
                f"expected reviewer_ids={expectation['expected_reviewer_ids']} got "
                f"{registry_data['reviewer_ids']}"
            )
            return actual
    else:
        actual_error = actual["actual_error"] or ""
        if expectation["expected_error_substring"] not in actual_error:
            actual["passed"] = False
            actual["divergence"] = (
                f"expected error to contain "
                f"{expectation['expected_error_substring']!r} got "
                f"{actual_error!r}"
            )
            return actual

    actual["passed"] = True
    actual["divergence"] = None
    return actual


def run(*, lane_dir: Path) -> dict[str, Any]:
    cases_dir = lane_dir / "cases"
    case_results: list[dict[str, Any]] = []
    for case_name in sorted(CASE_EXPECTATIONS.keys()):
        case_path = cases_dir / case_name
        if not case_path.exists():
            case_results.append(
                {
                    "case_id": case_name,
                    "passed": False,
                    "divergence": f"case fixture missing: {case_path}",
                }
            )
            continue
        case_results.append(_evaluate_case(case_path, CASE_EXPECTATIONS[case_name]))

    summary = {
        "lane": "reviewer_registry",
        "lane_version": "v1",
        "split": "dev",
        "adr": "ADR-0092",
        "invariant": "reviewer_registry_schema_v1",
        "total_cases": len(case_results),
        "passed_cases": sum(1 for r in case_results if r["passed"]),
        "failed_cases": sum(1 for r in case_results if not r["passed"]),
        "all_passed": all(r["passed"] for r in case_results),
        "cases": case_results,
    }
    return summary


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2).encode("utf-8") + b"\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="reviewer_registry lane runner")
    parser.add_argument(
        "--lane-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="lane root directory (defaults to this file's directory)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="path to write JSON report (defaults to <lane>/results/v1_dev.json)",
    )
    args = parser.parse_args(argv)

    summary = run(lane_dir=args.lane_dir)
    report_path = args.report or (args.lane_dir / "results" / "v1_dev.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload_bytes = _canonical_json(summary)
    report_path.write_bytes(payload_bytes)

    sha = hashlib.sha256(payload_bytes).hexdigest()
    print(f"report: {report_path}")
    print(f"sha256: {sha}")
    print(f"passed: {summary['passed_cases']}/{summary['total_cases']}")

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
