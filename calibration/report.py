"""Calibration report generation."""

from __future__ import annotations

import json
from pathlib import Path

from calibration.tune import CalibrationResult


def write_report(result: CalibrationResult, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return p


def print_report(result: CalibrationResult) -> None:
    bl = result.baseline_report
    br = result.best_report
    print("=== Calibration Report ===")
    print(f"baseline: {result.baseline_params.as_dict()}")
    print(f"  intent_accuracy  : {bl.intent_accuracy:.1%}")
    print(f"  versor_closure   : {bl.versor_closure_rate:.1%}")
    print(f"  surface_ground   : {bl.surface_groundedness:.1%}")
    print(f"best    : {result.best_params.as_dict()}")
    print(f"  intent_accuracy  : {br.intent_accuracy:.1%}")
    print(f"  versor_closure   : {br.versor_closure_rate:.1%}")
    print(f"  surface_ground   : {br.surface_groundedness:.1%}")
    print(f"candidates evaluated: {len(result.candidates)}")
    print(f"candidates accepted : {sum(1 for c in result.candidates if c.accepted)}")
