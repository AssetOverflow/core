"""Score holdouts split for each Phase 5.4–5.7 domain lane.

The `core eval` CLI only exposes dev/public splits.  Holdouts are
sealed-test infrastructure scored by direct runner invocation, which
is how `evals/english_fluency_ood/results/v1_holdouts_metrics.json`
was produced.

This script mirrors that pattern across the four new lanes, runs each
lane's holdouts in parallel via multiprocessing.Pool (one process per
lane), and writes `results/v1_holdouts_metrics.json` +
`results/v1_holdouts_details.json` per lane.

Run:
    .venv/bin/python scripts/score_phase5_holdouts.py
"""

from __future__ import annotations

import json
import multiprocessing as mp
from importlib import import_module
from pathlib import Path

LANES = [
    "elementary_mathematics_ood",
    "foundational_physics_ood",
    "foundational_biology_ood",
    "classical_literature_ood",
]


def _score_lane(lane: str) -> tuple[str, dict, int, int]:
    repo = Path(__file__).resolve().parent.parent
    cases_path = repo / "evals" / lane / "holdouts" / "v1" / "cases.jsonl"
    runner = import_module(f"evals.{lane}.runner")
    cases = [json.loads(line) for line in cases_path.read_text().splitlines() if line.strip()]
    report = runner.run_lane(cases)

    results_dir = repo / "evals" / lane / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "v1_holdouts_metrics.json").write_text(
        json.dumps(report.metrics, indent=2, sort_keys=True) + "\n"
    )
    (results_dir / "v1_holdouts_details.json").write_text(
        json.dumps(report.case_details, indent=2, sort_keys=True) + "\n"
    )
    return lane, report.metrics, report.metrics["passed"], report.metrics["total"]


if __name__ == "__main__":
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=min(len(LANES), 4)) as pool:
        for lane, metrics, passed, total in pool.map(_score_lane, LANES):
            acc = metrics["accuracy"] * 100
            print(f"{lane:38s}  {passed:3d}/{total:3d}  {acc:5.1f}%")
