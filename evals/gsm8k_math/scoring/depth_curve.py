"""ADR-0119.6 — GSM8K math depth-curve measurement harness.

Buckets the correct rate of a lane run by reasoning depth
(number of operations in the ground-truth graph).

Documented buckets per ADR-0119.6 contract:
``depth_1``, ``depth_2-3``, ``depth_4-5``, ``depth_6-8``.

Depth outside ``1..8`` raises :class:`DepthCurveError` rather than
silently creating a new bucket — the schema is documented and any
extension requires an explicit ADR amendment.

Missing case_id in the lane report also raises rather than silently
treating as ``refused`` — that would mask runner bugs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from evals.gsm8k_math.runner import LaneReport, run_lane


class DepthCurveError(ValueError):
    """Raised when a case's depth or outcome cannot be classified.

    Reasons:
        - depth ≥ 9 (out of documented bucket range)
        - depth == 0 (degenerate)
        - case_id present in input list but missing from lane_report
          (runner-output integrity violation)
    """


def compute_depth_curve(cases: list[dict[str, Any]], lane_report: LaneReport) -> dict[str, Any]:
    """Pure, deterministic function bucketizing cases by reasoning depth.

    Reads the case list and a LaneReport, buckets cases by reasoning depth,
    and returns a depth curve dictionary.
    """
    # Extract outcomes by case_id from the LaneReport
    outcomes = {detail["case_id"]: detail["outcome"] for detail in lane_report.case_details}

    # Initialize buckets with 0.0 rates (Obligation #6 empty bucket safety)
    bucket_keys = ["depth_1", "depth_2-3", "depth_4-5", "depth_6-8"]
    buckets: dict[str, dict[str, Any]] = {
        k: {"total": 0, "correct": 0, "rate": 0.0} for k in bucket_keys
    }

    # Extract depths of all cases
    case_depths = {}
    max_depth = 0
    for case in cases:
        case_id = case["id"]
        gt_graph = case.get("ground_truth_graph", {})
        if isinstance(gt_graph, dict):
            operations = gt_graph.get("operations", [])
        else:
            operations = getattr(gt_graph, "operations", [])
        depth = len(operations)
        case_depths[case_id] = depth
        if depth > max_depth:
            max_depth = depth

    # Initialize raw_curve mapping for depths 1 to max_depth
    raw_depths = {d: {"total": 0, "correct": 0} for d in range(1, max_depth + 1)}

    for case in cases:
        case_id = case["id"]
        depth = case_depths[case_id]

        # Missing case_id in lane_report is a runner-integrity violation,
        # not a silent refusal. Fail loud.
        if case_id not in outcomes:
            raise DepthCurveError(
                f"case_id {case_id!r} present in input but missing from "
                f"lane_report.case_details — runner-output integrity violation"
            )
        outcome = outcomes[case_id]

        is_correct = 1 if outcome == "correct" else 0

        # Resolve bucket key. Depth outside documented range raises rather
        # than silently extending the schema.
        if depth == 1:
            b_key = "depth_1"
        elif 2 <= depth <= 3:
            b_key = "depth_2-3"
        elif 4 <= depth <= 5:
            b_key = "depth_4-5"
        elif 6 <= depth <= 8:
            b_key = "depth_6-8"
        else:
            raise DepthCurveError(
                f"case {case_id!r} has depth {depth}, outside documented "
                f"range 1..8 (extending the bucket schema requires an ADR "
                f"amendment to ADR-0119.6)"
            )

        buckets[b_key]["total"] += 1
        buckets[b_key]["correct"] += is_correct

        raw_depths[depth]["total"] += 1
        raw_depths[depth]["correct"] += is_correct

    # Compute rates
    for k, v in buckets.items():
        if v["total"] > 0:
            v["rate"] = float(v["correct"] / v["total"])
        else:
            v["rate"] = 0.0

    raw_curve = []
    for d in sorted(raw_depths.keys()):
        v = raw_depths[d]
        rate = float(v["correct"] / v["total"]) if v["total"] > 0 else 0.0
        raw_curve.append({
            "depth": d,
            "total": v["total"],
            "correct": v["correct"],
            "rate": rate
        })

    return {
        "buckets": buckets,
        "max_depth": max_depth,
        "raw_curve": raw_curve
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GSM8K math lane and print depth curve.")
    parser.add_argument(
        "--split",
        choices=["dev", "public"],
        required=True,
        help="The corpus split to run against.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[3]
    if args.split == "dev":
        case_path = root / "evals/gsm8k_math/dev/cases.jsonl"
    else:
        case_path = root / "evals/gsm8k_math/public/v1/cases.jsonl"

    if not case_path.exists():
        print(f"Error: case file not found at {case_path}", file=sys.stderr)
        sys.exit(1)

    cases = []
    with open(case_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    # Run the lane runner to get the LaneReport
    lane_report = run_lane(cases)

    # Compute depth curve
    curve = compute_depth_curve(cases, lane_report)

    # Print the JSON output
    print(json.dumps(curve, indent=2))


if __name__ == "__main__":
    main()
