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


def test_adequacy_reports_blockers_by_organ_and_combination() -> None:
    report = build_report([
        {
            "case_id": "diagnostic-0393",
            "question": (
                "Yvonne brings a box of chocolates to school. Half have nuts and half do not. "
                "The students eat 80% of the ones with nuts and eat half of the ones without nuts. "
                "If there are 28 chocolates left, how many chocolates were in the box?"
            ),
        }
    ])

    per_case = report["per_case"][0]
    assert "percent_partition" in per_case["blockers_by_organ"]
    blockers = per_case["blockers_by_organ"]["percent_partition"]
    assert "inverse_topology_unlicensed" in blockers
    assert "original_whole_unbound" in blockers
    assert "percent_partition" in report["blocker_combinations_by_organ"]
