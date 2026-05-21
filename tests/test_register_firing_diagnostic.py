"""Register marker-firing diagnostic script."""

from __future__ import annotations

import json

from generate.intent import IntentTag, classify_intent
from evals.register_diagnostics.run_firing_diagnostic import (
    REPRESENTATIVE_PROMPTS,
    build_report,
    main,
)


def test_representative_prompts_classify_to_declared_intents():
    for intent, prompts in REPRESENTATIVE_PROMPTS.items():
        assert len(prompts) == 3
        for prompt in prompts:
            assert classify_intent(prompt).tag is intent


def test_build_report_records_marker_engagement_for_register_subset():
    report = build_report(
        register_ids=("convivial_v1",),
        intents=(IntentTag.DEFINITION, IntentTag.CAUSE),
    )

    assert report["diagnostic"] == "register_marker_firing"
    assert report["registers"] == ["convivial_v1"]
    assert report["intents"] == ["DEFINITION", "CAUSE"]
    assert report["all_replayed_variants_match_runtime"] is True

    cells = report["matrix"]["convivial_v1"]["DEFINITION"]
    assert len(cells) == 3
    assert all("opening_fired" in cell for cell in cells)
    assert all("closing_fired" in cell for cell in cells)
    assert any(cell["opening_fired"] for cell in cells)

    summaries = {
        summary["intent"]: summary
        for summary in report["summaries"]
        if summary["register_id"] == "convivial_v1"
    }
    assert summaries["DEFINITION"]["openings"]["non_empty_size"] > 0
    assert summaries["DEFINITION"]["openings"]["fire_count"] > 0


def test_main_can_write_json_report(tmp_path):
    output = tmp_path / "register_firing.json"
    rc = main([
        "--register",
        "default_neutral_v1",
        "--intent",
        "DEFINITION",
        "--output",
        str(output),
    ])

    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["registers"] == ["default_neutral_v1"]
    assert payload["intents"] == ["DEFINITION"]
    assert payload["matrix"]["default_neutral_v1"]["DEFINITION"]
