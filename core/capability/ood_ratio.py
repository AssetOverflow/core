"""ADR-0114a Obligation #2 — OOD surface variation ratio auditor.

Reads B3's public ``report.json`` (cases_correct / cases_total) and the
OOD lane's ``report.json``, computes

    ood_ratio = ood_accuracy / public_accuracy

and emits an ``OodRatioReport`` with an ``obligation_2_ratio_satisfied``
flag (gate: ratio ≥ 0.95, separate from the ``wrong == 0`` gate).

The auditor is pure and deterministic: same reports produce byte-equal
output.  It performs no I/O beyond reading the two JSON files and
writing the audit report.

Auditor pattern mirrors ``core/capability/pack_provenance.py``
(ADR-0114a.10) and ``evals/gsm8k_math/scoring/depth_curve.py``
(ADR-0114a.6).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_B3_REPORT: Path = (
    _REPO_ROOT / "evals" / "math_bounded_grammar" / "v1" / "report.json"
)
DEFAULT_OOD_REPORT: Path = (
    _REPO_ROOT / "evals" / "obligation_2_ood_ratio" / "v1" / "report.json"
)

# Gate threshold — changing this requires a new ADR.
OOD_RATIO_GATE: float = 0.95


class OodRatioError(Exception):
    """Raised when a required report cannot be read or is malformed."""


@dataclass(frozen=True, slots=True)
class OodRatioReport:
    """Aggregate obligation-#2 audit result."""

    lane_id: str
    public_cases_total: int
    public_cases_correct: int
    public_accuracy: float
    ood_cases_total: int
    ood_cases_correct: int
    ood_cases_wrong: int
    ood_accuracy: float
    ood_ratio: float
    obligation_2_ratio_satisfied: bool
    obligation_2_wrong_zero: bool
    obligation_2_passed: bool
    refusal_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "adr": "0114a.2",
            "schema_version": 1,
            "lane_id": self.lane_id,
            "public_cases_total": self.public_cases_total,
            "public_cases_correct": self.public_cases_correct,
            "public_accuracy": self.public_accuracy,
            "ood_cases_total": self.ood_cases_total,
            "ood_cases_correct": self.ood_cases_correct,
            "ood_cases_wrong": self.ood_cases_wrong,
            "ood_accuracy": self.ood_accuracy,
            "ood_ratio": self.ood_ratio,
            "obligation_2_ratio_satisfied": self.obligation_2_ratio_satisfied,
            "obligation_2_wrong_zero": self.obligation_2_wrong_zero,
            "obligation_2_passed": self.obligation_2_passed,
            "refusal_reason": self.refusal_reason,
        }


def _read_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise OodRatioError(f"report not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OodRatioError(f"invalid JSON in {path}: {exc}") from exc


def _refused_report(lane_id: str, reason: str) -> OodRatioReport:
    return OodRatioReport(
        lane_id=lane_id,
        public_cases_total=0,
        public_cases_correct=0,
        public_accuracy=0.0,
        ood_cases_total=0,
        ood_cases_correct=0,
        ood_cases_wrong=0,
        ood_accuracy=0.0,
        ood_ratio=0.0,
        obligation_2_ratio_satisfied=False,
        obligation_2_wrong_zero=False,
        obligation_2_passed=False,
        refusal_reason=reason,
    )


def evaluate_ood_ratio(
    *,
    lane_id: str = "B3_bounded_grammar",
    public_report_path: Path = DEFAULT_B3_REPORT,
    ood_report_path: Path = DEFAULT_OOD_REPORT,
) -> OodRatioReport:
    """Compute obligation-#2 OOD ratio for a lane.

    Reads the public B3 report and the OOD lane report, extracts
    accuracy figures, and checks both gates:

    1. ``ood_ratio >= 0.95`` — the ratio gate.
    2. ``ood_cases_wrong == 0`` — the wrong-zero gate.

    Both must hold for ``obligation_2_passed`` to be True.
    Refusal: public_accuracy == 0 (no baseline to compare against).
    """
    try:
        pub_data = _read_report(public_report_path)
    except OodRatioError as exc:
        return _refused_report(lane_id, str(exc))

    try:
        ood_data = _read_report(ood_report_path)
    except OodRatioError as exc:
        return _refused_report(lane_id, str(exc))

    pub_metrics = pub_data.get("metrics", {})
    pub_total = pub_metrics.get("cases_total", 0)
    pub_correct = pub_metrics.get("correct", 0)

    if not isinstance(pub_total, int) or not isinstance(pub_correct, int):
        return _refused_report(lane_id, "public report metrics missing or wrong type")

    if pub_total == 0:
        return _refused_report(lane_id, "public report has zero cases — no baseline")

    public_accuracy = pub_correct / pub_total

    if public_accuracy == 0.0:
        return _refused_report(
            lane_id, "public_accuracy is 0 — no meaningful baseline for ratio"
        )

    ood_metrics = ood_data.get("metrics", {})
    ood_total = ood_metrics.get("cases_total", 0)
    ood_correct = ood_metrics.get("correct", 0)
    ood_wrong = ood_metrics.get("wrong", 0)

    if not isinstance(ood_total, int) or not isinstance(ood_correct, int):
        return _refused_report(lane_id, "OOD report metrics missing or wrong type")

    if ood_total == 0:
        return _refused_report(lane_id, "OOD report has zero cases")

    ood_accuracy = ood_correct / ood_total
    ood_ratio = ood_accuracy / public_accuracy

    ratio_satisfied = ood_ratio >= OOD_RATIO_GATE
    wrong_zero = ood_wrong == 0
    passed = ratio_satisfied and wrong_zero

    refusal_reason = ""
    if not passed:
        parts = []
        if not ratio_satisfied:
            parts.append(
                f"ratio {ood_ratio:.4f} < gate {OOD_RATIO_GATE} "
                f"(ood_accuracy={ood_accuracy:.4f}, public_accuracy={public_accuracy:.4f})"
            )
        if not wrong_zero:
            parts.append(f"{ood_wrong} OOD case(s) wrong")
        refusal_reason = "; ".join(parts)

    return OodRatioReport(
        lane_id=lane_id,
        public_cases_total=pub_total,
        public_cases_correct=pub_correct,
        public_accuracy=public_accuracy,
        ood_cases_total=ood_total,
        ood_cases_correct=ood_correct,
        ood_cases_wrong=ood_wrong,
        ood_accuracy=ood_accuracy,
        ood_ratio=ood_ratio,
        obligation_2_ratio_satisfied=ratio_satisfied,
        obligation_2_wrong_zero=wrong_zero,
        obligation_2_passed=passed,
        refusal_reason=refusal_reason,
    )


def emit_ood_ratio_report(report: OodRatioReport, out_path: Path) -> None:
    """Write the deterministic obligation-#2 audit report."""
    out_path.write_text(
        json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
