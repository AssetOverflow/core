"""Tests for the R3 RateProblem model + rate setup oracle (R3b).

Pins the model's exactly-one-unknown guard and that the gold ruler is coherent + non-vacuous
(each validator branch fires under its violation).
"""

from __future__ import annotations

import copy

import pytest

from evals.rate_oracle.runner import (
    READER_REASONS,
    SOLVER_REASONS,
    _load_rate_gold,
    gold_to_problem,
    run,
    validate_fixture,
)
from evals.rate_oracle.signature import rate_setup_signature
from generate.rate_comprehension.model import RateProblem
from generate.rate_comprehension.units import RateUnit


def _solved() -> dict:
    return copy.deepcopy(next(f for f in _load_rate_gold() if f["expect"] == "solved"))


def test_run_validates_all_gold() -> None:
    r = run()
    assert r["invalid"] == 0 and r["valid"] == r["total"] == 13
    assert r["by_expect"] == {"solved": 7, "solver_refuses": 2, "reader_refuses": 4}


def test_gold_to_problem_roundtrips() -> None:
    p = gold_to_problem(next(f for f in _load_rate_gold() if f["id"] == "r3-01-distance"))
    assert p.rate == 60 and p.time == 3 and p.quantity is None and p.query == "quantity"
    assert (p.quantity_unit, p.time_unit) == ("mile", "hour")


def test_model_requires_exactly_one_unknown() -> None:
    with pytest.raises(ValueError):  # two unknowns
        RateProblem(RateUnit("mile", "hour"), None, None, 180, "rate")
    with pytest.raises(ValueError):  # zero unknowns
        RateProblem(RateUnit("mile", "hour"), 60, 3, 180, "quantity")
    with pytest.raises(ValueError):  # the named query is not the unknown
        RateProblem(RateUnit("mile", "hour"), 60, None, 180, "rate")


def test_signature_is_deterministic_and_keyed_by_role() -> None:
    p = gold_to_problem(next(f for f in _load_rate_gold() if f["id"] == "r3-05-speed"))
    sig = rate_setup_signature(p)
    assert sig == rate_setup_signature(p)
    assert sig["query"] == "rate" and sig["rate_unit"] == ("mile", "hour")
    assert dict(sig["knowns"]) == {"time": 3, "quantity": 180}


def test_reasons_in_gold_are_closed() -> None:
    for fx in _load_rate_gold():
        if fx["expect"] == "solver_refuses":
            assert fx["solver_reason"] in SOLVER_REASONS
        elif fx["expect"] == "reader_refuses":
            assert fx["reader_reason"] in READER_REASONS


# --- meaningful-fail: each invalid branch fires under exactly its violation ------------ #


def test_validator_rejects_incoherent_answer_key() -> None:
    fx = _solved()
    fx["answer"] = next(k for k in fx["options"] if fx["options"][k] != fx["gold"])
    assert validate_fixture(fx) == ("invalid", "answer_key_incoherent")


def test_validator_rejects_reader_refuse_carrying_gold() -> None:
    fx = copy.deepcopy(next(f for f in _load_rate_gold() if f["expect"] == "reader_refuses"))
    fx["gold"] = 5
    assert validate_fixture(fx) == ("invalid", "reader_refuses_has_gold")


def test_validator_rejects_unknown_reasons() -> None:
    rr = copy.deepcopy(next(f for f in _load_rate_gold() if f["expect"] == "reader_refuses"))
    rr["reader_reason"] = "made_up"
    assert validate_fixture(rr)[0] == "invalid"
    sr = copy.deepcopy(next(f for f in _load_rate_gold() if f["expect"] == "solver_refuses"))
    sr["solver_reason"] = "made_up"
    assert validate_fixture(sr)[0] == "invalid"


def test_validator_rejects_two_unknown_setup() -> None:
    fx = _solved()
    fx["time"] = None  # now both time and quantity unknown -> model __post_init__ raises
    assert validate_fixture(fx)[0] == "invalid"
