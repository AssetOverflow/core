"""Sprint 7 A2j owner-binding confusers."""

from __future__ import annotations

from generate.derivation.giveaway_target_residual import (
    resolve_promotable_giveaway_target_residual,
)
from generate.math_candidate_graph import parse_and_solve


def test_giveaway_unrelated_source_refuses() -> None:
    text = (
        "Martha has 20 apples. Jane got 5 apples from Sam, and James got 2 more "
        "than Jane. How many more apples would Martha need to give away to be left "
        "with only 4 of them?"
    )
    assert resolve_promotable_giveaway_target_residual(text) is None
    assert parse_and_solve(text).answer is None


def test_giveaway_comparative_must_reference_first_recipient() -> None:
    text = (
        "Martha has 20 apples. Jane got 5 apples from her, and James got 2 more "
        "than Bob. How many more apples would Martha need to give away to be left "
        "with only 4 of them?"
    )
    assert resolve_promotable_giveaway_target_residual(text) is None
    assert parse_and_solve(text).answer is None
