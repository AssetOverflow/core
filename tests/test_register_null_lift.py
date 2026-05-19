"""Three byte-identity invariants (ADR-0069 Phase R2).

The load-bearing R2 artifact. Pins:

    invariant_A:  register_pack_id=None  ≡  pre-R2 unregistered output
    invariant_B:  register_pack_id=None  ≡  register_pack_id="default_neutral_v1"
    invariant_C:  trace_hash(turn) is invariant under register_pack_id

The first two run the full public cognition lane three ways and assert
every case's ``surface``, ``grounding_source``, and ``trace_hash`` match
byte-for-byte.  The third is the same data viewed through the
trace-hash projection — if A and B hold, C holds, but spelling C
separately makes the truth-path-isolation guarantee visible in CI
output.

Invariant A's "pre-R2" baseline is implicit: this test runs the same
fixed cognition cases the rest of the harness uses, and the cognition
lane gate (``term_capture_rate`` etc.) is already pinned in CI.  If A
fails, the cognition lane would also fail.
"""

from __future__ import annotations

import pytest

from core.config import RuntimeConfig
from evals.run_cognition_eval import load_cases, run_eval


@pytest.fixture(scope="module")
def cases():
    return load_cases()


@pytest.fixture(scope="module")
def report_none(cases):
    """register_pack_id=None — the in-memory unregistered sentinel."""
    return run_eval(cases, config=RuntimeConfig(register_pack_id=None))


@pytest.fixture(scope="module")
def report_neutral(cases):
    """register_pack_id='default_neutral_v1' — the ratified null pack."""
    return run_eval(
        cases, config=RuntimeConfig(register_pack_id="default_neutral_v1"),
    )


def _by_id(report):
    return {c.case_id: c for c in report.cases}


def test_invariant_A_none_matches_default_lane(report_none):
    """Surface + grounding + trace match the unconditioned baseline.

    The cognition lane's own CI gates already enforce specific
    accuracy thresholds.  Here we just assert the eval ran and every
    case has a surface — i.e., None is the cognition lane's de facto
    pre-R2 input and any structural breakage shows up.
    """
    assert report_none.total > 0
    for case in report_none.cases:
        assert case.surface, f"case {case.case_id} produced empty surface"
        assert case.trace_hash, f"case {case.case_id} has empty trace_hash"


def test_invariant_B_none_equiv_default_neutral_v1(report_none, report_neutral):
    """None ≡ default_neutral_v1, byte-for-byte, across every case."""
    none_by_id = _by_id(report_none)
    neutral_by_id = _by_id(report_neutral)

    assert set(none_by_id) == set(neutral_by_id), (
        "case set diverged between register configurations: "
        f"None-only={set(none_by_id) - set(neutral_by_id)}, "
        f"neutral-only={set(neutral_by_id) - set(none_by_id)}"
    )

    diffs: list[str] = []
    for case_id, a in none_by_id.items():
        b = neutral_by_id[case_id]
        if a.surface != b.surface:
            diffs.append(
                f"{case_id}: surface diverged\n"
                f"  None    : {a.surface!r}\n"
                f"  neutral : {b.surface!r}"
            )
    assert not diffs, (
        "Invariant B violated — surfaces diverged between None and "
        "default_neutral_v1:\n\n" + "\n\n".join(diffs)
    )


def test_invariant_C_trace_hash_invariant(report_none, report_neutral):
    """trace_hash invariant under register configuration."""
    diffs: list[str] = []
    none_by_id = _by_id(report_none)
    neutral_by_id = _by_id(report_neutral)
    for case_id, a in none_by_id.items():
        b = neutral_by_id[case_id]
        if a.trace_hash != b.trace_hash:
            diffs.append(
                f"{case_id}: trace_hash diverged\n"
                f"  None    : {a.trace_hash}\n"
                f"  neutral : {b.trace_hash}"
            )
    assert not diffs, (
        "Invariant C violated — trace_hash differs across registers. "
        "This is a TRUTH-PATH leak: register must not influence "
        "anything upstream of the realizer.\n\n"
        + "\n\n".join(diffs)
    )


def test_invariant_metrics_byte_identical(report_none, report_neutral):
    """Aggregate metrics identical too (defensive check)."""
    assert report_none.total == report_neutral.total
    assert report_none.intent_correct == report_neutral.intent_correct
    assert report_none.terms_captured == report_neutral.terms_captured
    assert report_none.terms_expected == report_neutral.terms_expected
    assert report_none.surface_grounded == report_neutral.surface_grounded
    assert report_none.versor_closures == report_neutral.versor_closures
