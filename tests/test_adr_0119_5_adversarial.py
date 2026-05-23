"""ADR-0119.5 — adversarial generation invariants (ADR-0114a Obligation #8).

Pins six load-bearing invariants:

1. **Determinism.** ``generate_adversarial_cases()`` returns the same
   list across two calls.

2. **Minimum case count.** ≥ 30 cases across ≥ 8 families.

3. **Every case has a recognized expected outcome.** Outcomes are
   exactly ``"correct"`` or ``"refused"`` (never ``"wrong"`` — the
   load-bearing point is that the *runner* never produces ``wrong``
   on this suite).

4. **Zero misparse gate (ADR-0114a Obligation #8).** Running the suite
   through the lane runner produces ``wrong == 0``. A nonzero wrong
   means CORE silently confabulated on an adversarial input.

5. **In-grammar cases ARE solved correctly.** The ``subtle_in_grammar``
   family stays inside the parser grammar and the runner produces
   ``correct`` on every such case. Proves the gate isn't trivially
   satisfied by refusing everything.

6. **Out-of-grammar cases ARE refused.** Every case authored with
   ``expected_outcome == "refused"`` produces a ``refused`` outcome
   from the runner (or, in rare cases where the parser turns out to
   handle the input cleanly, ``correct`` — but never ``wrong``).
"""

from __future__ import annotations

from collections import Counter

import pytest

from evals.gsm8k_math.adversarial.generator import (
    AdversarialCase,
    FAMILY_REGISTRY,
    generate_adversarial_cases,
)
from evals.gsm8k_math.runner import run_lane


def test_generator_is_deterministic() -> None:
    a = generate_adversarial_cases()
    b = generate_adversarial_cases()
    assert len(a) == len(b)
    for ca, cb in zip(a, b):
        assert ca == cb


def test_minimum_case_count() -> None:
    cases = generate_adversarial_cases()
    assert len(cases) >= 30, (
        f"adversarial suite must have >= 30 cases per ADR-0119.5 brief; "
        f"got {len(cases)}"
    )
    families = {c.family for c in cases}
    assert len(families) >= 8, (
        f"suite must exercise >= 8 distinct families; got {len(families)}: "
        f"{sorted(families)}"
    )


def test_every_case_has_recognized_expected_outcome() -> None:
    for case in generate_adversarial_cases():
        assert case.expected_outcome in {"correct", "refused"}, (
            f"{case.case_id}: bad expected_outcome {case.expected_outcome!r}; "
            f"the suite must never declare 'wrong' as an expectation"
        )


def test_wrong_count_is_zero_across_suite() -> None:
    """ADR-0114a Obligation #8: misparse rate MUST be zero."""
    cases = generate_adversarial_cases()
    report = run_lane([c.as_runner_dict() for c in cases])
    wrong_details = [
        d for d in report.case_details if d["outcome"] == "wrong"
    ]
    assert report.metrics["wrong"] == 0, (
        f"adversarial suite produced {report.metrics['wrong']} wrong outcomes; "
        f"first 3 misparses: {wrong_details[:3]}"
    )
    assert report.metrics["wrong_count_is_zero"] is True


def test_in_grammar_cases_are_solved_correctly() -> None:
    """The subtle_in_grammar family stays inside grammar; runner must
    produce 'correct' on every such case. Prevents trivial gate-
    satisfaction by refusing everything."""
    cases = generate_adversarial_cases()
    in_grammar = [c for c in cases if c.family == "subtle_in_grammar"]
    assert len(in_grammar) >= 3, (
        "subtle_in_grammar family must have >= 3 cases (gate sanity)"
    )
    report = run_lane([c.as_runner_dict() for c in in_grammar])
    assert report.metrics["correct"] == len(in_grammar), (
        f"in-grammar family: {report.metrics['correct']}/{len(in_grammar)} correct; "
        f"adversarial gate would be trivially satisfied if these refused too"
    )


@pytest.mark.parametrize(
    "family_fn", FAMILY_REGISTRY, ids=lambda fn: fn.__name__
)
def test_family_outcomes_match_or_are_safe(family_fn) -> None:
    """For each family, the runner's outcomes either match the declared
    expectations OR are safer-than-expected (e.g. parser handles a case
    we labeled 'refused' cleanly → 'correct' is acceptable). The forbidden
    transition is expected→wrong."""
    family_cases: list[AdversarialCase] = family_fn()
    if not family_cases:
        return
    report = run_lane([c.as_runner_dict() for c in family_cases])
    for case, detail in zip(family_cases, report.case_details):
        got = detail["outcome"]
        assert got != "wrong", (
            f"{case.case_id} ({case.family}): expected "
            f"{case.expected_outcome!r} but got 'wrong' — CORE silently "
            f"misparsed an adversarial input. Reason: {detail.get('reason')}"
        )


def test_outcome_distribution_summary() -> None:
    """Sanity: at least one case in each outcome bucket (otherwise the
    suite isn't actually testing the discriminating power)."""
    cases = generate_adversarial_cases()
    report = run_lane([c.as_runner_dict() for c in cases])
    outcomes = Counter(d["outcome"] for d in report.case_details)
    assert outcomes["correct"] >= 1, (
        "adversarial suite produces no correct outcomes; gate is trivial"
    )
    assert outcomes["refused"] >= 10, (
        f"adversarial suite produces only {outcomes['refused']} refusals; "
        f"expected the bulk to refuse"
    )
    assert outcomes["wrong"] == 0
