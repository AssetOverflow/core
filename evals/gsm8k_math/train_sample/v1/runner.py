"""ADR-0126 P6 — train-sample exit-criterion runner.

Thin measurement harness around the canonical :mod:`evals.gsm8k_math.runner`
pipeline.  Loads PR #159's 50-case unsealed GSM8K train sample, replays
each case through the existing parser → solver → verifier path, and
emits a deterministic ``report.json`` with per-case verdicts.

Exit code reflects ADR-0126's gate:

    correct >= 10 AND wrong == 0  →  exit 0
    otherwise                     →  exit 1

The runner is measurement-only.  It does not touch the parser, the
sealed holdout, or any decryption surface (CLAUDE.md trust boundary).
``answer_numeric`` is grade-on-value-only — train-sample cases carry no
unit annotation, so ``expected_unit`` is normalized to ``""`` which
:func:`evals.gsm8k_math.runner._score_one` already treats as
"skip unit comparison".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from evals.gsm8k_math.runner import _score_one

_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_REPORT_PATH = _HERE / "report.json"
_SAMPLE_REL = "evals/gsm8k_math/train_sample/v1/cases.jsonl"
_EXPECTED_COUNT = 50
_CORRECT_MIN = 10
_WRONG_MAX = 0


def _load_cases(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    assert len(records) == _EXPECTED_COUNT, (
        f"train sample must contain exactly {_EXPECTED_COUNT} cases; "
        f"found {len(records)} at {path}"
    )
    return records


def _adapt(case: dict[str, Any]) -> dict[str, Any]:
    """Reshape a train-sample record into the runner's expected schema.

    Train sample uses ``case_id`` / ``question`` / ``answer_numeric``;
    the canonical runner expects ``id`` / ``problem`` / ``expected_answer``
    / ``expected_unit``.  An empty ``expected_unit`` tells the runner to
    grade on value only (cf. :func:`evals.gsm8k_math.runner._score_one`).
    """
    return {
        "id": case["case_id"],
        "problem": case["question"],
        "expected_answer": case["answer_numeric"],
        "expected_unit": "",
    }


def build_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    per_case: list[dict[str, str]] = []
    counts = {"correct": 0, "wrong": 0, "refused": 0}
    for raw in cases:
        outcome = _score_one(_adapt(raw))
        counts[outcome.outcome] += 1
        per_case.append(
            {
                "case_id": outcome.case_id,
                "verdict": outcome.outcome,
                "reason": outcome.reason,
            }
        )
    passed = counts["correct"] >= _CORRECT_MIN and counts["wrong"] <= _WRONG_MAX
    return {
        "schema_version": 1,
        "adr": "0126",
        "sample_path": _SAMPLE_REL,
        "sample_count": len(cases),
        "counts": counts,
        "exit_criterion": {
            "correct_min": _CORRECT_MIN,
            "wrong_max": _WRONG_MAX,
            "passed": passed,
        },
        "per_case": per_case,
    }


def write_report(report: dict[str, Any], path: Path = _REPORT_PATH) -> None:
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    cases = _load_cases(_CASES_PATH)
    report = build_report(cases)
    write_report(report)
    return 0 if report["exit_criterion"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
