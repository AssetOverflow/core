from __future__ import annotations

import json

from core.cli import main


def test_core_eval_sensorium_json_reports_selected_modality(capsys):
    assert main(["eval", "sensorium", "--modality", "sensorimotor", "--json"]) == 0
    out = capsys.readouterr().out
    report = json.loads(out)
    assert report["lane"] == "sensorium"
    assert report["modality"] == "sensorimotor"
    assert report["pack_id"] == "sensorimotor_core_v1"
    assert report["gate_closed"] is True
    assert report["failed"] == 0


def test_core_eval_sensorium_event_vision_json(capsys):
    assert main(["eval", "sensorium", "--modality", "event-vision", "--json"]) == 0
    out = capsys.readouterr().out
    report = json.loads(out)
    assert report["lane"] == "sensorium"
    assert report["modality"] == "event-vision"
    assert report["pack_id"] == "vision_event_core_v1"
    assert report["failed"] == 0


def test_core_eval_sensorium_text_summary(capsys):
    assert main(["eval", "sensorium", "--modality", "vision"]) == 0
    out = capsys.readouterr().out
    assert "lane           : sensorium" in out
    assert "modality       : vision" in out
    assert "gate_closed    : True" in out
    assert "failed         : 0" in out
