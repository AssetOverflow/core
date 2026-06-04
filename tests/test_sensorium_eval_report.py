from __future__ import annotations

import json

from evals.sensorium import build_sensorium_report


def test_sensorium_reports_are_deterministic_and_gate_closed():
    for modality in ("audio", "vision", "sensorimotor"):
        first = build_sensorium_report(modality)
        second = build_sensorium_report(modality)
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
        assert first["lane"] == "sensorium"
        assert first["modality"] == modality
        assert first["gate_engaged"] is False
        assert first["gate_closed"] is True
        assert first["total"] > 0
        assert first["failed"] == 0
        assert first["passed"] == first["total"]
