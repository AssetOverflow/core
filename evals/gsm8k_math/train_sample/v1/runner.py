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

CLI flags:

    --use-reader    Activate the ADR-0164 Phase-1 comprehension reader for
                    question sentences (RuntimeConfig.comprehension_reader_questions
                    = True).  Default: False (flag-OFF, byte-identical to today).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from evals.gsm8k_math.runner import _score_one_candidate_graph

_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_REPORT_PATH = _HERE / "report.json"
_DELTA_PATH = _HERE / "reader_phase1_delta.json"
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


def build_report(
    cases: list[dict[str, Any]],
    use_reader: bool = False,
) -> dict[str, Any]:
    """Build the measurement report for the train-sample cases.

    Args:
        cases: Loaded case records from cases.jsonl.
        use_reader: When True, activates the ADR-0164 Phase-1 comprehension
            reader for question sentences via RuntimeConfig.comprehension_reader_questions.
            Default False preserves byte-identical behaviour with today.
    """
    config = None
    if use_reader:
        from core.config import RuntimeConfig
        config = RuntimeConfig(comprehension_reader_questions=True)

    per_case: list[dict[str, Any]] = []
    counts = {"correct": 0, "wrong": 0, "refused": 0}
    for raw in cases:
        outcome = _score_one_candidate_graph(_adapt(raw), config=config)
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
        "use_reader": use_reader,
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


def build_delta_report(
    baseline: dict[str, Any],
    reader_on: dict[str, Any],
) -> dict[str, Any]:
    """Compute per-case delta between flag-OFF and flag-ON reports.

    Returns a JSON-serialisable dict with:
        - summary counts
        - per-case attribution for every case that changed verdict
    """
    base_map = {p["case_id"]: p for p in baseline["per_case"]}
    on_map = {p["case_id"]: p for p in reader_on["per_case"]}
    changed: list[dict[str, Any]] = []
    for cid, on_case in on_map.items():
        base_case = base_map.get(cid, {})
        if base_case.get("verdict") != on_case["verdict"]:
            changed.append(
                {
                    "case_id": cid,
                    "prior_verdict": base_case.get("verdict"),
                    "prior_refusal_reason": base_case.get("reason"),
                    "new_verdict": on_case["verdict"],
                    "new_reason": on_case.get("reason"),
                }
            )
    bc = baseline["counts"]
    rc = reader_on["counts"]
    return {
        "schema_version": 1,
        "adr": "0164",
        "phase": 1,
        "baseline_off": {"correct": bc["correct"], "refused": bc["refused"], "wrong": bc["wrong"]},
        "reader_on": {"correct": rc["correct"], "refused": rc["refused"], "wrong": rc["wrong"]},
        "delta": {
            "correct": rc["correct"] - bc["correct"],
            "refused": rc["refused"] - bc["refused"],
            "wrong": rc["wrong"] - bc["wrong"],
        },
        "changed_cases": changed,
    }


def main() -> int:
    """Run the train-sample measurement.

    When ``--use-reader`` is passed, also generates a delta report at
    ``reader_phase1_delta.json`` comparing flag-OFF vs flag-ON results.
    """
    use_reader = "--use-reader" in sys.argv

    cases = _load_cases(_CASES_PATH)

    if use_reader:
        # Run baseline (flag OFF) first, then reader-on.
        baseline_report = build_report(cases, use_reader=False)
        reader_report = build_report(cases, use_reader=True)
        write_report(reader_report)
        delta = build_delta_report(baseline_report, reader_report)
        _DELTA_PATH.write_text(
            json.dumps(delta, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        report = reader_report
    else:
        report = build_report(cases, use_reader=False)
        write_report(report)

    return 0 if report["exit_criterion"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
