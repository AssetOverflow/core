"""Read-only views over the calibrated-learning / serving-discipline loop.

ADR-0175. This is where "the engine earns the right to guess" becomes
inspectable. The workbench computes nothing the engine owns:

- per-class **reliability** is the engine's own one-sided Wilson
  ``conservative_floor`` (via ``ClassTally.reliability``), and the
  **license** verdicts come from ``core.reliability_gate.license_for`` —
  never re-implemented here;
- **serving counts** are read from the committed ``report.json`` artifacts;
  no lane is ever re-run.

Trust boundary: read-only over committed artifacts + engine-owned
derivation. No execution, no mutation, no license is ever changed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from core.reliability_gate import Action, Ceilings, ClassTally, license_for
from workbench.readers import (
    REPO_ROOT,
    EvidenceUnavailableError,
    _display_path,
    _read_json_object,
    _sha256_file,
)
from workbench.schemas import CalibrationClass, ServingMetrics

# The persisted per-class arena ledger (sealed practice, ADR-0175).
PRACTICE_REPORT = REPO_ROOT / "evals" / "gsm8k_math" / "practice" / "v1" / "report.json"

# Committed serving lanes — their counts are the live wrong=0 evidence.
SERVING_LANES: tuple[tuple[str, Path], ...] = (
    ("train_sample", REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "report.json"),
    ("holdout_dev", REPO_ROOT / "evals" / "gsm8k_math" / "holdout_dev" / "v1" / "report.json"),
)

_CEILINGS = Ceilings()


def _calibration_class(
    class_name: str,
    counts: Mapping[str, Any],
    *,
    source_path: str,
    source_digest: str,
) -> CalibrationClass:
    tally = ClassTally(
        class_name,
        correct=int(counts.get("correct", 0)),
        wrong=int(counts.get("wrong", 0)),
        refused=int(counts.get("refused", 0)),
    )
    propose = license_for(tally, Action.PROPOSE, _CEILINGS)
    serve = license_for(tally, Action.SERVE, _CEILINGS)
    return CalibrationClass(
        class_name=class_name,
        correct=tally.correct,
        wrong=tally.wrong,
        refused=tally.refused,
        committed=tally.committed,
        reliability_floor=round(tally.reliability, 9),
        coverage=round(tally.coverage, 9),
        propose_required=propose.required,
        propose_licensed=propose.licensed,
        serve_required=serve.required,
        serve_licensed=serve.licensed,
        source_path=source_path,
        source_digest=source_digest,
    )


def read_calibration_classes(report_path: Path = PRACTICE_REPORT) -> list[CalibrationClass]:
    """Per-class gold-tether view: what each class has earned, by the real gate."""
    if not report_path.exists():
        raise EvidenceUnavailableError(
            "calibration evidence unavailable: practice report.json is absent "
            "(run the sealed practice lane to populate the arena ledger)"
        )
    report = _read_json_object(report_path)
    per_class = report.get("per_class")
    if not isinstance(per_class, dict):
        raise EvidenceUnavailableError(
            "calibration evidence unavailable: report has no per_class ledger"
        )
    source_path = _display_path(report_path)
    source_digest = _sha256_file(report_path)
    rows = [
        _calibration_class(
            name,
            counts,
            source_path=source_path,
            source_digest=source_digest,
        )
        for name, counts in per_class.items()
        if isinstance(counts, dict)
    ]
    # Failures-first: un-licensed / lowest-reliability at the top; stable by name.
    rows.sort(
        key=lambda r: (r.serve_licensed, r.propose_licensed, r.reliability_floor, r.class_name)
    )
    return rows


def read_serving_metrics(lanes: Sequence[tuple[str, Path]] = SERVING_LANES) -> list[ServingMetrics]:
    """The live serving counts (correct / refused / wrong) from committed reports."""
    out: list[ServingMetrics] = []
    for lane, path in lanes:
        if not path.exists():
            continue
        report = _read_json_object(path)
        counts = report.get("counts") or {}
        correct = int(counts.get("correct", 0))
        refused = int(counts.get("refused", 0))
        wrong = int(counts.get("wrong", 0))
        out.append(
            ServingMetrics(
                lane=lane,
                correct=correct,
                refused=refused,
                wrong=wrong,
                sample_count=int(report.get("sample_count", correct + refused + wrong)),
                source_path=_display_path(path),
                source_digest=_sha256_file(path),
            )
        )
    if not out:
        raise EvidenceUnavailableError(
            "serving metrics unavailable: no committed report.json found"
        )
    return out
