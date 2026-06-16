"""Score the text closed-world (CWA) FrameVerdict lane.

For each case: build a ``ClosedFrame``, run the production ``evaluate_frame_verdict``, and
compare its ``verdict`` to the hand-authored gold. ``wrong`` = verdict != gold; the gold is
cross-checked against the INDEPENDENT truth-table oracle (``oracle.oracle_frame_verdict``,
disjoint from the ROBDD) by the lane test. This is a measure-only lane: no runtime serving,
no ``determine`` path, no ``Determined``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from generate.frame_verdict import (
    ClosedFrame,
    FrameKind,
    FrameVerdict,
    WorldAssumption,
    evaluate_frame_verdict,
)

_CASES = Path(__file__).resolve().parent / "v1" / "cases.jsonl"


def _load(path: Path = _CASES) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _frame(case: dict[str, Any]) -> ClosedFrame:
    return ClosedFrame(
        frame_id=case["id"],
        frame_kind=FrameKind(case["frame_kind"]),
        world_assumption=WorldAssumption(case["world_assumption"]),
        propositions=tuple(case["propositions"]),
        closure_declared=bool(case["closure_declared"]),
        source="frame_verdict_text_cwa",
        provenance=(),
    )


def run(path: Path = _CASES) -> dict[str, Any]:
    cases = _load(path)
    correct = wrong = 0
    wrongs: list[dict[str, Any]] = []
    for case in cases:
        verdict = evaluate_frame_verdict(_frame(case), case["query"])
        assert isinstance(verdict, FrameVerdict)  # never a Determined — no open-world leak
        got = verdict.verdict.name
        if got == case["gold"]:
            correct += 1
        else:
            wrong += 1
            wrongs.append({"id": case["id"], "got": got, "gold": case["gold"]})
    return {
        "domain": "frame_verdict_text_cwa",
        "total": len(cases),
        "correct": correct,
        "wrong": wrong,
        "wrongs": wrongs,
        "counts": {"correct": correct, "wrong": wrong, "refused": 0},
    }


def main() -> int:
    report = run()
    print(json.dumps({k: v for k, v in report.items() if k != "wrongs"}, indent=2, sort_keys=True))
    if report["wrong"]:
        print("WRONG > 0 — text-CWA verdict disagrees with gold:", file=sys.stderr)
        print(json.dumps(report["wrongs"], indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
