"""ADR-0131.G.3 — Numeric-literals capability-axis lane tests.

Gate (must all pass for the lane to be considered green):
  - safety rail: ``solved_wrong == 0`` on the axis lane
  - safety rail: ``admitted_wrong == 0`` on the GSM8K probe (unchanged
    by this iteration — G.3 widens the candidate-graph parser, which
    the probe currently does not consult, so admission is not expected
    to move; the wrong-count invariant is what's gated)
  - axis-lane correctness: every ``solved_correct`` case in
    ``cases.jsonl`` passes end-to-end; every ``refused`` probe refuses
    with a typed reason at parser-or-solver layer
  - per-class diversity: at least one case per non-refusal class
  - replay determinism: ``report.json`` byte-equal across two runs
  - resolver-level invariants for the new literal shapes
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.math_capability_axes.G3_numerics.v1 import runner as axis_runner
from generate.math_candidate_parser import _resolve_value


_AXIS_DIR = Path(__file__).resolve().parent.parent / "evals" / "math_capability_axes" / "G3_numerics" / "v1"
_CASES_PATH = _AXIS_DIR / "cases.jsonl"

# Closed set of classes this iteration is responsible for. The lane
# refuses to silently grow the class taxonomy — adding a new class is
# an ADR-level scope change.
_KNOWN_POSITIVE_CLASSES = frozenset({
    "money_symbol_integer",
    "money_symbol_decimal",
    "money_word",
    "hyphenated_cardinal",
})
_KNOWN_REFUSAL_CLASSES = frozenset({
    "refuse_money_precision",
    "refuse_division_by_zero",
    "refuse_unknown_compound",
    "refuse_percentage",
})


def _load_cases() -> list[dict]:
    out = []
    for line in _CASES_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


# ---------------------------------------------------------------------------
# Resolver-level invariants (cheap, independent of the lane runner).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "token, expected_value, expected_unit_override",
    [
        ("$40", 4000, "cents"),
        ("$2.50", 250, "cents"),
        ("$18.00", 1800, "cents"),
        ("$0.99", 99, "cents"),
        ("twenty-five", 25, None),
        ("ninety-nine", 99, None),
        ("3/4", 0.75, None),
        ("5", 5, None),
        ("twelve", 12, None),
    ],
)
def test_resolve_value_admits_new_literals(token, expected_value, expected_unit_override):
    rv = _resolve_value(token)
    assert rv is not None, f"{token!r} should resolve"
    assert rv.value == expected_value
    assert rv.unit_override == expected_unit_override


@pytest.mark.parametrize(
    "token",
    [
        "$40.000",   # >2 decimals — money precision out of scope
        "$1.2345",
        "5/0",       # division-by-zero
        "five-and-a-half",  # unrecognized compound
        "gobbledy-gook",    # unrecognized compound
        "50%",       # percentage out of scope
        "some",      # indefinite quantifier
    ],
)
def test_resolve_value_refuses_out_of_scope(token):
    assert _resolve_value(token) is None, f"{token!r} should refuse"


# ---------------------------------------------------------------------------
# Dataset integrity invariants.
# ---------------------------------------------------------------------------

def test_dataset_case_ids_unique():
    cases = _load_cases()
    ids = [c["case_id"] for c in cases]
    assert len(ids) == len(set(ids)), "duplicate case_id"


def test_dataset_class_taxonomy_is_closed():
    cases = _load_cases()
    seen = {c["class"] for c in cases}
    allowed = _KNOWN_POSITIVE_CLASSES | _KNOWN_REFUSAL_CLASSES
    extra = seen - allowed
    assert not extra, f"unknown class(es) — extend ADR scope before adding: {extra}"


def test_dataset_every_positive_class_has_at_least_one_case():
    cases = _load_cases()
    by_class = {c["class"] for c in cases if c["expected_outcome"] == "solved_correct"}
    missing = _KNOWN_POSITIVE_CLASSES - by_class
    assert not missing, f"missing coverage for positive classes: {missing}"


def test_dataset_every_refusal_class_has_at_least_one_case():
    cases = _load_cases()
    by_class = {c["class"] for c in cases if c["expected_outcome"] == "refused"}
    missing = _KNOWN_REFUSAL_CLASSES - by_class
    assert not missing, f"missing coverage for refusal classes: {missing}"


# ---------------------------------------------------------------------------
# Lane-level invariants (run the full runner).
# ---------------------------------------------------------------------------

def test_axis_lane_safety_rail_no_wrong_answers():
    """ADR-0114a Obligation #4 — refusal-first; wrong-count must be 0."""
    report = axis_runner.build_report()
    assert report["metrics"]["solved_wrong"] == 0, (
        f"wrong != 0: {report['verdict_counts']}"
    )
    assert report["metrics"]["wrong_count_is_zero"] is True


def test_axis_lane_all_positive_cases_solved_correct():
    report = axis_runner.build_report()
    assert report["metrics"]["correct_rate_on_positive_cases"] == 1.0


def test_axis_lane_all_refusal_probes_refused_typed():
    report = axis_runner.build_report()
    refusal_cases = [c for c in report["per_case"] if c["expected_outcome"] == "refused"]
    for c in refusal_cases:
        assert c["actual_outcome"] == "refused", (
            f"{c['case_id']}: expected refused, got {c['actual_outcome']}"
        )
        assert c["reason"], f"{c['case_id']}: refusal must carry typed reason"


def test_axis_lane_overall_pass():
    report = axis_runner.build_report()
    assert report["metrics"]["overall_pass"] is True


# ---------------------------------------------------------------------------
# Replay determinism — load-bearing per ADR-0114a.
# ---------------------------------------------------------------------------

def test_axis_lane_report_replay_byte_equal():
    r1 = json.dumps(axis_runner.build_report(), indent=2, sort_keys=True)
    r2 = json.dumps(axis_runner.build_report(), indent=2, sort_keys=True)
    assert r1 == r2, "axis lane must be deterministic"


def test_committed_report_matches_fresh_run():
    """The committed ``report.json`` must equal a fresh run — keeps the
    artifact diff-able as load-bearing evidence per ADR-0131.G."""
    fresh = json.dumps(axis_runner.build_report(), indent=2, sort_keys=True) + "\n"
    committed = (_AXIS_DIR / "report.json").read_text(encoding="utf-8")
    assert fresh == committed, (
        "committed report.json is stale; run "
        "`python3 -m evals.math_capability_axes.G3_numerics.v1.runner` to refresh"
    )


# ---------------------------------------------------------------------------
# GSM8K-probe safety rail — must still hold (the non-negotiable gate).
# ---------------------------------------------------------------------------

def test_gsm8k_probe_safety_rail_unchanged():
    """ADR-0131.G's safety rail: ``admitted_wrong == 0`` on the GSM8K
    coverage probe is the load-bearing invariant every G.<n> iteration
    must preserve. G.3 widens the candidate-graph parser; this asserts
    that the probe (which runs through the legacy parser path) still
    refuses cleanly without confabulating.
    """
    from evals.gsm8k_math.train_sample.v1.run_coverage_probe import build_report
    probe_report = build_report()
    m = probe_report["metrics"]
    assert m["admitted_wrong"] == 0, (
        "GSM8K probe safety rail breached — admitted_wrong > 0"
    )
    assert m["safety_rail_intact"] is True
