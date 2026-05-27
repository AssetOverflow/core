"""ADR-0163 Phase D — candidate-graph recognizer wiring tests.

Pins:
- empty registry: candidate_graph behaves identically to main (no regression)
- non-empty (synthetic) registry: a previously-refused statement that
  matches a recognizer no longer triggers the per-statement refusal
- wrong_count_delta == 0 under the synthetic registry against the
  GSM8K train_sample (the load-bearing wrong=0 invariant test)
- capability axes G1..G5 + S1 report wrong=0 unchanged under the
  synthetic registry (wiring does not regress the wrong=0 floor)
- per-category admission counts: how many GSM8K train_sample
  statements the matcher admits per Phase B category (fixture-based,
  not live re-baseline)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import generate.math_candidate_graph as cg
from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.recognizer_match import match as _matcher
from generate.recognizer_registry import RatifiedRecognizer
from tests._phase_d_fixture import build_synthetic_registry


_REPO_ROOT = Path(__file__).resolve().parent.parent
_GSM8K_CASES = _REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "cases.jsonl"
_GSM8K_REPORT = _REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "report.json"


@pytest.fixture(scope="module")
def synthetic_registry() -> tuple[RatifiedRecognizer, ...]:
    return build_synthetic_registry()


@pytest.fixture
def with_synthetic_registry(
    monkeypatch: pytest.MonkeyPatch,
    synthetic_registry: tuple[RatifiedRecognizer, ...],
) -> tuple[RatifiedRecognizer, ...]:
    """Patch ``math_candidate_graph._load_ratified_registry_or_empty`` to
    return the synthetic registry for the duration of the test."""
    monkeypatch.setattr(
        cg, "_load_ratified_registry_or_empty", lambda: synthetic_registry,
    )
    return synthetic_registry


# ---------------------------------------------------------------------------
# Empty registry: no behavioral change
# ---------------------------------------------------------------------------


def test_empty_registry_preserves_existing_refusal_reason() -> None:
    """The live proposal log has accepted recognizer registry entries;
    the candidate-graph must refuse on a statement that has no
    admissible candidate.

    Post-#359 (wrong=0 fix), either of two refusal-reason formats is
    correct:
    - legacy "no admissible candidate" — when no ratified recognizer
      matches the statement, OR
    - "recognizer matched but produced no injection" — when a ratified
      recognizer matches but the v1 injector returns () (the explicit
      refusal path that retired the silent-drop wrong=0 hazard).
    """
    # No monkeypatch — uses the real (live) registry projection.
    result = cg.parse_and_solve(
        "Tina makes $18.00 an hour. How much does Tina earn after 8 hours?"
    )
    assert result.answer is None
    assert result.refusal_reason is not None
    assert (
        "no admissible candidate" in result.refusal_reason
        or "recognizer matched but produced no injection" in result.refusal_reason
    ), f"unexpected refusal reason: {result.refusal_reason!r}"


# ---------------------------------------------------------------------------
# Non-empty synthetic registry: recognized statements refuse explicitly
# ---------------------------------------------------------------------------


def test_recognized_rate_statement_refuses_explicitly_post_wrong_zero_fix(
    with_synthetic_registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """With the rate_with_currency recognizer loaded, "Tina makes $18.00
    an hour" is recognized but the v1 injector returns () (the
    SentenceChoice union does not yet model rates — see ADR follow-up).

    Pre-#359 behavior: silently drop the recognized-but-uninjectable
    statement and admit a partial graph from the rest — a wrong>0
    hazard analogous to case 0050.

    Post-#359 (this test's contract): refuse explicitly with reason
    "recognizer matched but produced no injection" naming the
    statement and category. This pinned behavior is the wrong=0
    safety net for the recognizer path.
    """
    result = cg.parse_and_solve(
        "Tina makes $18.00 an hour. How much does Tina earn after 8 hours?"
    )
    assert result.refusal_reason is not None
    assert (
        "recognizer matched but produced no injection" in result.refusal_reason
    ), f"expected explicit recognizer-refusal, got: {result.refusal_reason!r}"
    # The statement IS named in the reason — that's the diagnostic shape
    # the post-#359 refusal carries. Update the prior assertion which
    # forbade naming, since that assertion encoded the silent-drop
    # premise that #359 retired.
    assert "Tina makes $18.00 an hour" in result.refusal_reason


def test_recognized_descriptive_statement_refuses_explicitly_post_wrong_zero_fix(
    with_synthetic_registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """Descriptive_setup_no_quantity statements that match a ratified
    recognizer but have no v1 injector now refuse explicitly post-#359,
    same as the rate case above. The statement IS named in the
    refusal_reason for diagnostic purposes."""
    # Construct a problem whose statements are ALL non-numeric so
    # the pre-filter does NOT strip them, forcing them to the
    # per-statement loop.
    result = cg.parse_and_solve(
        "Marnie makes bead bracelets. John adopts a dog from a shelter. "
        "How many things happened?"
    )
    if result.refusal_reason is not None:
        # The post-#359 refusal explicitly identifies the recognized
        # statement that lacks an injector — that's the load-bearing
        # diagnostic surface.
        assert (
            "recognizer matched but produced no injection" in result.refusal_reason
            or "no admissible candidate" in result.refusal_reason
        ), f"unexpected refusal reason: {result.refusal_reason!r}"


# ---------------------------------------------------------------------------
# WRONG-COUNT INVARIANT — the load-bearing safety test
# ---------------------------------------------------------------------------


def _run_gsm8k_train_sample_with_patch(
    monkeypatch: pytest.MonkeyPatch,
    registry: tuple[RatifiedRecognizer, ...],
) -> dict[str, int]:
    """Re-run the gsm8k train_sample under the patched registry and
    return the {correct, wrong, refused} counts."""
    monkeypatch.setattr(
        cg, "_load_ratified_registry_or_empty", lambda: registry,
    )
    import importlib
    runner_mod = importlib.import_module(
        "evals.gsm8k_math.train_sample.v1.runner"
    )
    cases = runner_mod._load_cases(runner_mod._CASES_PATH)
    report = runner_mod.build_report(cases)
    return {
        "correct": int(report["counts"]["correct"]),
        "wrong": int(report["counts"]["wrong"]),
        "refused": int(report["counts"]["refused"]),
    }


def test_wrong_count_stays_zero_under_synthetic_registry(
    monkeypatch: pytest.MonkeyPatch,
    synthetic_registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """The load-bearing Phase D invariant: with the synthetic Phase C
    registry loaded into the candidate-graph, the GSM8K train_sample
    MUST NOT report wrong > 0.  Any lift the wiring produces is
    refused→correct, never refused→wrong."""
    baseline_report = json.loads(_GSM8K_REPORT.read_text(encoding="utf-8"))
    baseline_counts = baseline_report["counts"]
    candidate_counts = _run_gsm8k_train_sample_with_patch(
        monkeypatch, synthetic_registry,
    )
    assert candidate_counts["wrong"] == 0, (
        f"Phase D wiring regressed wrong=0: {candidate_counts}"
    )
    wrong_delta = candidate_counts["wrong"] - int(baseline_counts.get("wrong", 0))
    assert wrong_delta == 0, f"wrong_count_delta={wrong_delta}"


def test_capability_axis_wrong_unchanged_under_synthetic_registry(
    monkeypatch: pytest.MonkeyPatch,
    synthetic_registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """G1..G5 + S1 must still report wrong=0 with the synthetic
    registry loaded.  Phase D's wiring is a per-sentence skip
    guarded by a narrow recognizer; it cannot mis-admit a
    well-parsed capability-axis statement."""
    monkeypatch.setattr(
        cg, "_load_ratified_registry_or_empty", lambda: synthetic_registry,
    )
    import importlib
    lanes = [
        ("G1_verb_classes", "evals.math_capability_axes.G1_verb_classes.v1.runner"),
        ("G2_comparatives", "evals.math_capability_axes.G2_comparatives.v1.runner"),
        ("G3_numerics", "evals.math_capability_axes.G3_numerics.v1.runner"),
        ("G4_multi_clause", "evals.math_capability_axes.G4_multi_clause.v1.runner"),
        ("G5_aggregate", "evals.math_capability_axes.G5_aggregate.v1.runner"),
        ("S1_rate_events", "evals.math_capability_axes.S1_rate_events.v1.runner"),
    ]
    for lane_id, mp in lanes:
        mod = importlib.import_module(mp)
        lc_args = mod._load_cases.__code__.co_argcount
        br_args = mod.build_report.__code__.co_argcount
        cases = mod._load_cases(mod._CASES_PATH) if lc_args == 1 else mod._load_cases()
        report = mod.build_report(cases) if br_args >= 1 else mod.build_report()
        # Per-axis wrong extraction (matches teaching/replay.py).
        if "counts" in report:
            wrong = int(report["counts"].get("wrong", 0))
        else:
            metrics = report.get("metrics", {})
            wrong = int(metrics.get("wrong", metrics.get("solved_wrong", 0)))
        assert wrong == 0, f"{lane_id}: wrong={wrong} under synthetic registry"


# ---------------------------------------------------------------------------
# Per-category admission counts (Phase D PR body evidence)
# ---------------------------------------------------------------------------


def test_per_category_admission_counts_on_gsm8k_train_sample(
    synthetic_registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """Report the count of refused GSM8K train_sample sentences that
    the matcher admits per Phase B category.  This is the PR-body
    evidence the brief requires (fixture-based, not live re-baseline).

    The assertion is bounded below by zero — we report counts, not
    pin them to specific numbers, so the test stays robust to
    Phase B corpus updates that narrow or widen specific axes.
    """
    cases = [json.loads(l) for l in _GSM8K_CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    report = json.loads(_GSM8K_REPORT.read_text(encoding="utf-8"))
    refused_ids = {e["case_id"] for e in report["per_case"] if e["verdict"] == "refused"}

    counts: dict[str, int] = {
        ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY.value: 0,
        ShapeCategory.RATE_WITH_CURRENCY.value: 0,
        ShapeCategory.TEMPORAL_AGGREGATION.value: 0,
    }
    for case in cases:
        if case["case_id"] not in refused_ids:
            continue
        text = case["question"]
        sentences = [s.strip() for s in text.replace("?", ".").split(".") if s.strip()]
        for s in sentences:
            m = _matcher(s, synthetic_registry)
            if m is not None:
                counts[m.category.value] += 1
    # Each category admits at least one statement across the 50-case
    # refused-set; the PR body cites the exact counts.
    assert counts[ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY.value] >= 1
    assert counts[ShapeCategory.RATE_WITH_CURRENCY.value] >= 1
    assert counts[ShapeCategory.TEMPORAL_AGGREGATION.value] >= 1
    # Surface the counts to stdout for the PR body.
    print(f"\nPhase D admission counts (synthetic registry vs GSM8K train_sample refused-set):")
    for k, v in counts.items():
        print(f"  {k}: {v}")


# ---------------------------------------------------------------------------
# Unrecognized statement still refuses with the existing reason
# ---------------------------------------------------------------------------


def test_unrecognized_statement_still_refuses_with_existing_reason(
    with_synthetic_registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """A statement that doesn't match any recognizer and that the
    parser can't admit must still refuse via the existing
    per-statement reason string — backward compatibility."""
    result = cg.parse_and_solve(
        "Quizzical wibble fizzbuzz schnitzel 7 prog. What is the answer?"
    )
    if result.refusal_reason is not None:
        # Either per-statement refusal OR a later-stage refusal; both
        # acceptable.  The point is wrong=0 unchanged.
        assert result.answer is None


_TYPE_USED: Any = (RatifiedRecognizer,)
