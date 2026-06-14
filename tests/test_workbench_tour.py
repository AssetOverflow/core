"""D1/D2 guided determinism tour — honesty + drift guards.

The tour is authored narrative, so the load-bearing guarantee is that it cannot
drift from the real demos: every demo step binds to a registered demo, the
honesty cards come from the demo spec (never re-authored), and a phantom demo id
fails closed rather than becoming a dead link.
"""

from __future__ import annotations

import pytest

from workbench.readers import DEMO_SPECS
from workbench.tour import _build_tour, determinism_tour


def test_every_demo_step_binds_to_a_registered_demo() -> None:
    tour = determinism_tour()
    demo_ids = [step.demo_id for step in tour.steps if step.demo_id is not None]
    assert demo_ids, "tour should reference at least one real demo"
    for demo_id in demo_ids:
        assert demo_id in DEMO_SPECS


def test_honesty_cards_come_from_the_spec_not_re_authored() -> None:
    # If a tour step re-worded what a demo proves, this fails — the tour can
    # never claim more (or less) than the demo it points at.
    for step in determinism_tour().steps:
        if step.demo_id is None:
            continue
        spec = DEMO_SPECS[step.demo_id]
        assert step.what_this_proves == spec.what_this_proves
        assert step.what_this_does_not_prove == spec.what_this_does_not_prove
        assert step.demo_title == spec.title


def test_non_demo_steps_carry_no_demo_claims() -> None:
    for step in determinism_tour().steps:
        if step.kind == "demo":
            continue
        assert step.demo_id is None
        assert step.what_this_proves is None
        assert step.what_this_does_not_prove is None


def test_phantom_demo_fails_closed() -> None:
    with pytest.raises(KeyError, match="unknown demo"):
        _build_tour((("x", "demo", "h", "n", "no_such_demo", "/x"),))


def test_steps_are_ordered_and_thesis_is_present() -> None:
    tour = determinism_tour()
    assert tour.schema_version == "determinism_tour_v1"
    assert [step.order for step in tour.steps] == list(range(len(tour.steps)))
    # D2 provider-agnostic framing is present and explicit.
    assert "proposing model" in tour.thesis.lower() or "any model" in tour.thesis.lower()
