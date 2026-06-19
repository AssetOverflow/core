from scripts.gsm8k_problem_frame_adequacy import build_report


def test_adequacy_report_smoke_does_not_require_gold_answers() -> None:
    report = build_report([
        {
            "case_id": "diagnostic-1",
            "question": "There are 100 students. Half are girls. How many students are girls?",
        }
    ])
    assert report["case_count"] == 1
    assert report["counts"]["frame_built"] == 1
    assert "contract_runnable_count" in report["counts"]
    assert report["per_case"][0]["current_verdict"] is None
