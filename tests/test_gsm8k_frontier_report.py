"""Tests for the deterministic GSM8K frontier report analyzer (Inc 2 + Inc3 evidence).

Test classes:
- **Historical fixture:** committed ``report.json`` exact-count pin until rebaselined.
- **Live capability:** monotonic serving contract (wrong=0; correct may climb).
- **Frontier diagnostics:** bucketing, category extraction, deterministic analyzer output.

Score preservation and truth preservation are separate: frozen counts protect replay
of committed measurement artifacts; live tests must not block capability lift.
"""

from __future__ import annotations

import json
from pathlib import Path


from scripts.gsm8k_frontier_report import (
    analyze_report,
    render_markdown,
)
from tests.gsm8k_train_sample_baseline import assert_monotonic_serving_counts

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REPORT = _REPO_ROOT / "evals/gsm8k_math/train_sample/v1/report.json"


def test_committed_frontier_fixture_is_6_44_0_until_rebaselined():
    """Historical artifact: committed report.json stays at 6/44/0 until rebaselined.

    Inc2 used this file to surface rate_with_currency no-injection (3 cases).
    Inc3 (#799) changed live code but did not rebaseline report.json — this test
    preserves the historical frontier pin for replayability of Inc2 evidence.
    """
    assert _REPORT.exists(), "report.json must be present for frontier measurement"

    summary = analyze_report(_REPORT)

    # Top-level shape
    assert "counts" in summary
    assert "recognized_no_injection_by_category" in summary
    assert isinstance(summary["counts"], dict)
    assert isinstance(summary["recognized_no_injection_by_category"], dict)

    c = summary["counts"]
    assert c["correct"] == 6
    assert c["refused"] == 44
    assert c.get("wrong", 0) == 0
    assert c.get("recognized_no_injection", 0) > 0

    # Historical Inc-2 target: rate_with_currency visible in pinned no-injection frontier
    no_inj = summary["recognized_no_injection_by_category"]
    assert "rate_with_currency" in no_inj
    assert no_inj["rate_with_currency"] == 3

    # Determinism: re-running produces byte-identical structure (keys sorted)
    summary2 = analyze_report(_REPORT)
    assert json.dumps(summary, sort_keys=True) == json.dumps(summary2, sort_keys=True)


def test_live_serving_meets_monotonic_capability_contract():
    """Live train_sample: wrong=0 hard; counts monotonic; refusals carry reasons."""
    from evals.gsm8k_math.train_sample.v1.runner import build_report

    cases_path = _REPO_ROOT / "evals/gsm8k_math/train_sample/v1/cases.jsonl"
    cases = [
        json.loads(line)
        for line in cases_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = build_report(cases)

    assert_monotonic_serving_counts(report["counts"])

    refused_rows = [r for r in report["per_case"] if r.get("verdict") == "refused"]
    assert len(refused_rows) == report["counts"]["refused"]
    for row in refused_rows:
        assert row.get("reason"), f"refused case {row.get('case_id')} lacks reason"


def test_post_inc3_live_runner_has_zero_rate_no_injection():
    """Live train_sample scoring on current code: rate bucket no longer at injector."""
    import re
    from collections import Counter

    from evals.gsm8k_math.train_sample.v1.runner import build_report

    cases_path = _REPO_ROOT / "evals/gsm8k_math/train_sample/v1/cases.jsonl"
    cases = [
        json.loads(line)
        for line in cases_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = build_report(cases)

    assert_monotonic_serving_counts(report["counts"])

    cats: Counter[str] = Counter()
    for row in report["per_case"]:
        reason = row.get("reason", "")
        if "produced no injection" not in reason:
            continue
        m = re.search(r"category=(\w+)", reason)
        if m:
            cats[m.group(1)] += 1

    assert cats.get("rate_with_currency", 0) == 0


def test_post_gate_a1_live_runner_has_zero_comparative_no_injection():
    """Live train_sample: comparative_with_unit bucket closed at injector."""
    import re
    from collections import Counter

    from evals.gsm8k_math.train_sample.v1.runner import build_report
    from tests.gsm8k_train_sample_baseline import assert_monotonic_serving_counts

    cases_path = _REPO_ROOT / "evals/gsm8k_math/train_sample/v1/cases.jsonl"
    cases = [
        json.loads(line)
        for line in cases_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = build_report(cases)
    assert_monotonic_serving_counts(report["counts"])

    cats: Counter[str] = Counter()
    for row in report["per_case"]:
        reason = row.get("reason", "")
        if "produced no injection" not in reason:
            continue
        m = re.search(r"category=(\w+)", reason)
        if m:
            cats[m.group(1)] += 1

    assert cats.get("comparative_with_unit", 0) == 0


def test_classify_and_extract_category_logic():
    """Unit the internal classification on the exact reason strings the graph emits."""
    # We exercise via the public analyze path with a tiny synthetic report
    fake = {
        "per_case": [
            {
                "case_id": "c1",
                "verdict": "refused",
                "reason": "candidate_graph: recognizer matched but produced no injection for statement: 'Tina makes $18.00 an hour.' (category=rate_with_currency)",
            },
            {
                "case_id": "c2",
                "verdict": "refused",
                "reason": "candidate_graph: no admissible candidate for statement: 'foo'",
            },
            {
                "case_id": "c3",
                "verdict": "refused",
                "reason": "candidate_graph: no admissible candidate for question: 'bar?'",
            },
            {"case_id": "c4", "verdict": "correct", "reason": "fast-path"},
            {"case_id": "c5", "verdict": "refused", "reason": "some other refusal"},
        ],
        "sample_count": 5,
    }
    # Write temp and analyze (or monkey the path; for simplicity use temp file)
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        rp = Path(td) / "fake_report.json"
        rp.write_text(json.dumps(fake), encoding="utf-8")
        s = analyze_report(rp)

    # The script's _classify_reason and extraction on the exact fake reasons
    c = s["counts"]
    assert c["recognized_no_injection"] == 1
    assert s["recognized_no_injection_by_category"]["rate_with_currency"] == 1
    assert c["no_admissible_statement"] == 1
    assert c["no_admissible_question"] == 1
    assert c.get("fast_path_correct", 0) == 1 or c.get("graph_correct", 0) == 1
    # "some other refusal" lands in other_refused (or similar catch-all)
    # The catch-all for unclassified refusals may be "other_refused" or
    # omitted if count==0 in this particular fake; the important pins are
    # the rate extraction and the main refusal classes.
    assert c["correct"] == 1
    assert "rate_with_currency" in s["recognized_no_injection_by_category"]


def test_markdown_render_is_stable_and_mentions_rate():
    """Markdown output is deterministic and surfaces the rate frontier for humans."""
    fake = {
        "per_case": [
            {
                "case_id": "r1",
                "verdict": "refused",
                "reason": "candidate_graph: recognizer matched but produced no injection for statement: 'X' (category=rate_with_currency)",
            },
            {"case_id": "c1", "verdict": "correct", "reason": ""},
        ],
        "sample_count": 2,
        "exit_criterion": {"correct_min": 10, "passed": False, "wrong_max": 0},
    }
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        rp = Path(td) / "r.json"
        rp.write_text(json.dumps(fake), encoding="utf-8")
        summary = analyze_report(rp)
        md = render_markdown(summary)

    assert "recognized_no_injection by category (top frontier)" in md
    assert "rate_with_currency: 1" in md
    assert "correct: 1" in md
    # No timestamps or nondet text
    assert "202" not in md and "T" not in md.split("\n", 5)[-1]  # rough
    # Re-render identical
    assert render_markdown(summary) == md


def test_inc3_connector_makes_rate_no_injection_actionable():
    """Inc3 effect: supporting 'one' (and prior 'an'/'per') means rate_with_currency
    surfaces no longer contribute to recognized_no_injection bucket when injector
    succeeds. Use synthetic report to show the reclassification without mutating
    the pinned 6/44/0 artifact. rate bucket for no_inj goes to 0 for covered cases;
    refusal becomes generic (no_admissible etc)."""
    # Synthetic report where the rate stmt now injects (Inc3), so no "no injection"
    # for rate; instead a later generic refusal for the case.
    fake = {
        "per_case": [
            {
                "case_id": "r1",
                "verdict": "refused",
                "reason": "candidate_graph: no admissible candidate for statement: 'Alexa ... for one cup'",
            },
            {
                "case_id": "r2",
                "verdict": "refused",
                "reason": "candidate_graph: recognizer matched but produced no injection for statement: 'unsupported' (category=temporal_aggregation)",
            },
        ],
        "sample_count": 2,
    }
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        rp = Path(td) / "post_inc3_fake.json"
        rp.write_text(json.dumps(fake), encoding="utf-8")
        s = analyze_report(rp)
    no_inj = s["recognized_no_injection_by_category"]
    assert (
        "rate_with_currency" not in no_inj or no_inj.get("rate_with_currency", 0) == 0
    )
    assert s["counts"]["recognized_no_injection"] == 1  # only the unsupported temporal
    assert s["counts"].get("no_admissible_statement", 0) == 1
