from __future__ import annotations

from pathlib import Path


def test_tabletop_lab_protocol_is_passive_and_trace_safe():
    root = Path(__file__).resolve().parents[1]
    doc = root / "docs" / "lab" / "tabletop_falsification_lab.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "Only passive, human-moved objects are allowed" in text
    assert "No CORE motor command path is mounted" in text
    assert "No raw camera frame, event stream, PCM, trajectory, or actuator trace enters" in text
    assert "Exact replay remains" in text
