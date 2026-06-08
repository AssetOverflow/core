"""Tests for the deterministic multi-organ setup router (N3).

Pins that each problem routes to exactly the organ that owns it (R1 relational, R2 constraint),
that unreadable problems refuse, that no gold problem is read by both organs (no ambiguity), and
— the wrong=0 invariant — that every routed R2 setup matches the independent gold signature.
"""

from __future__ import annotations

from core.comprehension_attempt import route_setup
from core.comprehension_attempt.classify import _r2_signature
from evals.constraint_oracle.runner import _load_r2_gold, gold_to_problem
from evals.setup_oracle.runner import _load_r1_gold


def test_r2_well_formed_routes_to_r2_and_matches_gold_signature() -> None:
    for fx in _load_r2_gold():
        result = route_setup(fx["text"], case_id=fx["id"])
        if fx["expect"] in ("solved", "solver_refuses"):
            assert result.status == "routed", f"{fx['id']}: {result.status}"
            assert result.selected is not None and result.selected.organ == "r2_constraints"
            # wrong=0: the routed setup is byte-equal to the independent gold setup.
            assert result.selected.setup_signature == _r2_signature(gold_to_problem(fx)), fx["id"]
        else:  # reader_refuses
            assert result.status == "all_refused" and result.selected is None


def test_r1_admitted_routes_to_r1_refused_all_refused() -> None:
    routed = refused = 0
    for fx in _load_r1_gold():
        result = route_setup(fx["text"], case_id=fx["id"])
        if result.status == "routed":
            routed += 1
            assert result.selected.organ == "r1_quantitative", fx["id"]
        else:
            refused += 1
            assert result.status == "all_refused"
    assert routed == 7 and refused == 3


def test_no_gold_problem_is_ambiguous() -> None:
    # Each organ is exclusive on the gold corpora — no text is admitted by both.
    for fx in _load_r2_gold() + _load_r1_gold():
        assert route_setup(fx["text"]).status != "ambiguous", fx.get("id")


def test_router_never_selects_a_refusal() -> None:
    for fx in _load_r2_gold() + _load_r1_gold():
        result = route_setup(fx["text"])
        if result.selected is not None:
            assert result.selected.outcome == "setup_correct"
        assert len(result.attempts) == 3  # always one R1 + one R2 + one R3 attempt
