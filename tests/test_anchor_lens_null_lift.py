"""Anchor-lens byte-identity null-lift invariant (ADR-0073b, Plan Phase L1.2).

The load-bearing L1.2 artifact.  Pins:

    anchor_lens_byte_identity_null_lift:
      anchor_lens_id=None  ≡  anchor_lens_id="default_unanchored_v1"

Runs the full public cognition lane two ways and asserts every case's
``surface``, ``grounding_source``, and ``trace_hash`` match
byte-for-byte.  At L1.2 the lens is loaded and stored on the runtime
but no composer consumes it; this invariant fails the moment any
later code path silently branches on the lens before L1.3 ratifies a
non-null lens.

Mirror of ``tests/test_register_null_lift.py`` for the anchor-lens
sibling.
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
    """anchor_lens_id=None — the in-memory unanchored sentinel."""
    return run_eval(cases, config=RuntimeConfig(anchor_lens_id=None))


@pytest.fixture(scope="module")
def report_unanchored(cases):
    """anchor_lens_id='default_unanchored_v1' — the ratified null pack."""
    return run_eval(
        cases, config=RuntimeConfig(anchor_lens_id="default_unanchored_v1"),
    )


def _by_id(report):
    return {c.case_id: c for c in report.cases}


def test_anchor_lens_none_runs_cognition_lane(report_none):
    """L1.2 baseline — None is the cognition lane's de facto input
    and any structural breakage shows up."""
    assert report_none.total > 0
    for case in report_none.cases:
        assert case.surface, f"case {case.case_id} produced empty surface"
        assert case.trace_hash, f"case {case.case_id} has empty trace_hash"


def test_anchor_lens_none_equiv_default_unanchored_surface(
    report_none, report_unanchored,
):
    """None ≡ default_unanchored_v1 — surface byte-identical across every case."""
    none_by_id = _by_id(report_none)
    unanchored_by_id = _by_id(report_unanchored)

    assert set(none_by_id) == set(unanchored_by_id), (
        "case set diverged between anchor-lens configurations: "
        f"None-only={set(none_by_id) - set(unanchored_by_id)}, "
        f"unanchored-only={set(unanchored_by_id) - set(none_by_id)}"
    )

    diffs: list[str] = []
    for case_id, a in none_by_id.items():
        b = unanchored_by_id[case_id]
        if a.surface != b.surface:
            diffs.append(
                f"{case_id}: surface diverged\n"
                f"  None       : {a.surface!r}\n"
                f"  unanchored : {b.surface!r}"
            )
    assert not diffs, (
        "anchor_lens_byte_identity_null_lift violated — surfaces "
        "diverged between None and default_unanchored_v1:\n\n"
        + "\n\n".join(diffs)
    )


def test_anchor_lens_none_equiv_default_unanchored_trace_hash(
    report_none, report_unanchored,
):
    """trace_hash invariant under {None, default_unanchored_v1}.

    L1.2 trace_hash MUST match — at L1.2 the lens does nothing, so
    the proposition is identical and so is its hash.  L1.3 will
    deliberately move trace_hash for non-null lenses (the opposite
    of register's invariant C); this null-lift assertion stays in
    force for ``default_unanchored_v1`` regardless.
    """
    diffs: list[str] = []
    none_by_id = _by_id(report_none)
    unanchored_by_id = _by_id(report_unanchored)
    for case_id, a in none_by_id.items():
        b = unanchored_by_id[case_id]
        if a.trace_hash != b.trace_hash:
            diffs.append(
                f"{case_id}: trace_hash diverged\n"
                f"  None       : {a.trace_hash}\n"
                f"  unanchored : {b.trace_hash}"
            )
    assert not diffs, (
        "anchor_lens_byte_identity_null_lift violated — trace_hash "
        "differs between None and default_unanchored_v1.  At L1.2 no "
        "composer consumes the lens, so any divergence is a regression "
        "in lens threading.\n\n"
        + "\n\n".join(diffs)
    )


def test_anchor_lens_aggregate_metrics_byte_identical(
    report_none, report_unanchored,
):
    """Aggregate metrics identical too (defensive check)."""
    assert report_none.total == report_unanchored.total
    assert report_none.intent_correct == report_unanchored.intent_correct
    assert report_none.terms_captured == report_unanchored.terms_captured
    assert report_none.terms_expected == report_unanchored.terms_expected
    assert report_none.surface_grounded == report_unanchored.surface_grounded
