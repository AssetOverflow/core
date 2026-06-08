"""Tests for the combined-rate CombinedRateProblem model + setup oracle (CMB-a).

Pins the model's two-explicit-rates + per-query-slot guards, the sum/difference effective-rate
derivation (and that a non-positive net rate is a SOLVER concern, not a malformed setup), the
canonical signature (sum commutative, difference ordered), and that the gold ruler is coherent +
non-vacuous (each validator branch fires under its violation). No reader yet (CMB-c).
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from evals.combined_rate_oracle.runner import (
    COMBINE_MODES,
    QUERIES,
    READER_REASONS,
    SOLVER_REASONS,
    _load_combined_rate_gold,
    gold_to_problem,
    run,
    validate_fixture,
)
from evals.combined_rate_oracle.signature import combined_rate_setup_signature
from generate.combined_rate_comprehension.model import CombinedRateProblem
from generate.combined_rate_comprehension.units import RateUnit

_ROOM_HOUR = RateUnit("room", "hour")


def _of(expect: str) -> dict:
    return copy.deepcopy(next(f for f in _load_combined_rate_gold() if f["expect"] == expect))


def _solved() -> dict:
    return copy.deepcopy(next(f for f in _load_combined_rate_gold() if f["expect"] == "solved"))


# --- gold validity --------------------------------------------------------------------- #


def test_run_validates_all_gold() -> None:
    r = run()
    assert r["invalid"] == 0 and r["valid"] == r["total"] == 18
    assert r["by_expect"] == {"solved": 6, "solver_refuses": 5, "reader_refuses": 7}


def test_solved_grid_covers_every_mode_query_cell() -> None:
    # The six solved fixtures are exactly the full combine_mode x query grid (2 x 3).
    solved = [f for f in _load_combined_rate_gold() if f["expect"] == "solved"]
    cells = {(f["combine_mode"], f["query"]) for f in solved}
    assert cells == {(m, q) for m in COMBINE_MODES for q in QUERIES}


def test_gold_to_problem_roundtrips() -> None:
    p = gold_to_problem(next(f for f in _load_combined_rate_gold() if f["id"] == "cmb-01-paint-sum-quantity"))
    assert (p.rate_a, p.rate_b, p.combine_mode) == (3, 2, "sum")
    assert p.time == 4 and p.quantity is None and p.query == "quantity"
    assert (p.quantity_unit, p.time_unit) == ("room", "hour")
    assert p.effective_rate == 5


def test_reasons_and_modes_in_gold_are_closed() -> None:
    for fx in _load_combined_rate_gold():
        if fx["expect"] == "solver_refuses":
            assert fx["solver_reason"] in SOLVER_REASONS
        elif fx["expect"] == "reader_refuses":
            assert fx["reader_reason"] in READER_REASONS
        else:  # solved
            assert fx["combine_mode"] in COMBINE_MODES and fx["query"] in QUERIES


# --- model guards ---------------------------------------------------------------------- #


def test_model_requires_two_explicit_rates() -> None:
    with pytest.raises(ValueError):
        CombinedRateProblem(None, 2, _ROOM_HOUR, "sum", 4, None, "quantity")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        CombinedRateProblem(3, None, _ROOM_HOUR, "sum", 4, None, "quantity")  # type: ignore[arg-type]


def test_model_query_slot_guard() -> None:
    # query=quantity: quantity must be the unknown, time the known.
    with pytest.raises(ValueError):  # zero unknowns (quantity also given)
        CombinedRateProblem(3, 2, _ROOM_HOUR, "sum", 4, 20, "quantity")
    with pytest.raises(ValueError):  # two unknowns (time also missing)
        CombinedRateProblem(3, 2, _ROOM_HOUR, "sum", None, None, "quantity")
    # query=time: time must be the unknown, quantity the known.
    with pytest.raises(ValueError):
        CombinedRateProblem(3, 2, _ROOM_HOUR, "sum", 4, None, "time")
    # query=effective_rate: neither time nor quantity may be present (over-specified).
    with pytest.raises(ValueError):
        CombinedRateProblem(3, 2, _ROOM_HOUR, "sum", 4, None, "effective_rate")


def test_model_rejects_unknown_combine_mode_and_query() -> None:
    with pytest.raises(ValueError):
        CombinedRateProblem(3, 2, _ROOM_HOUR, "average", 4, None, "quantity")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        CombinedRateProblem(3, 2, _ROOM_HOUR, "sum", 4, None, "rate")  # type: ignore[arg-type]


def test_effective_rate_derivation() -> None:
    assert CombinedRateProblem(3, 2, _ROOM_HOUR, "sum", 4, None, "quantity").effective_rate == 5
    assert CombinedRateProblem(9, 4, _ROOM_HOUR, "difference", 4, None, "quantity").effective_rate == 5


def test_non_positive_net_rate_is_a_well_formed_setup_not_a_model_error() -> None:
    # 4 - 4 = 0: the model MUST construct it (the solver, not the model, refuses non_positive_net_rate).
    p = CombinedRateProblem(4, 4, _ROOM_HOUR, "difference", 5, None, "quantity")
    assert p.effective_rate == 0


def test_model_rejects_non_positive_rates_and_known_slots() -> None:
    # Negative/zero INPUTS are nonsensical and must be unrepresentable (a non-positive NET rate is
    # the solver's call, but a non-positive rate magnitude or duration/quantity is a malformed setup)
    # — otherwise the solver could emit a negative answer (wrong=0 breach).
    with pytest.raises(ValueError):  # negative rate magnitude
        CombinedRateProblem(-3, 2, _ROOM_HOUR, "sum", 4, None, "quantity")
    with pytest.raises(ValueError):  # zero rate magnitude
        CombinedRateProblem(3, 0, _ROOM_HOUR, "sum", 4, None, "quantity")
    with pytest.raises(ValueError):  # negative known duration
        CombinedRateProblem(3, 2, _ROOM_HOUR, "sum", -3, None, "quantity")
    with pytest.raises(ValueError):  # negative known quantity
        CombinedRateProblem(3, 2, _ROOM_HOUR, "sum", None, -5, "time")
    with pytest.raises(ValueError):  # zero known duration
        CombinedRateProblem(3, 2, _ROOM_HOUR, "sum", 0, None, "quantity")


# --- signature ------------------------------------------------------------------------- #


def test_signature_is_deterministic_and_keyed() -> None:
    p = gold_to_problem(next(f for f in _load_combined_rate_gold() if f["id"] == "cmb-05-tank-difference-rate"))
    sig = combined_rate_setup_signature(p)
    assert sig == combined_rate_setup_signature(p)
    assert sig["query"] == "effective_rate" and sig["combine_mode"] == "difference"
    assert sig["rates"] == (9, 4) and sig["rate_unit"] == ("liter", "minute")


def test_signature_sum_is_commutative_but_difference_is_ordered() -> None:
    sum_ab = combined_rate_setup_signature(CombinedRateProblem(3, 2, _ROOM_HOUR, "sum", 4, None, "quantity"))
    sum_ba = combined_rate_setup_signature(CombinedRateProblem(2, 3, _ROOM_HOUR, "sum", 4, None, "quantity"))
    assert sum_ab == sum_ba and sum_ab["rates"] == (2, 3)  # sorted
    dif_ab = combined_rate_setup_signature(CombinedRateProblem(5, 2, _ROOM_HOUR, "difference", 6, None, "quantity"))
    dif_ba = combined_rate_setup_signature(CombinedRateProblem(2, 5, _ROOM_HOUR, "difference", 6, None, "quantity"))
    assert dif_ab != dif_ba and dif_ab["rates"] == (5, 2)  # order preserved (which is the drain matters)


# --- meaningful-fail: each invalid branch fires under exactly its violation ------------- #


def test_validator_rejects_incoherent_answer_key() -> None:
    fx = _solved()
    fx["answer"] = next(k for k in fx["options"] if fx["options"][k] != fx["gold"])
    assert validate_fixture(fx) == ("invalid", "answer_key_incoherent")


def test_validator_rejects_reader_refuse_carrying_gold() -> None:
    fx = _of("reader_refuses")
    fx["gold"] = 5
    assert validate_fixture(fx) == ("invalid", "reader_refuses_has_gold")


def test_validator_rejects_solver_refuse_carrying_gold() -> None:
    fx = _of("solver_refuses")
    fx["gold"] = 5
    assert validate_fixture(fx) == ("invalid", "solver_refuses_has_gold")


def test_validator_rejects_unknown_reasons() -> None:
    # Pin the FULL tuple (CLAUDE.md proof-obligation): a substitution returning a different invalid
    # reason must not pass silently.
    rr = _of("reader_refuses")
    rr["reader_reason"] = "made_up"
    assert validate_fixture(rr) == ("invalid", "unknown_reader_reason:'made_up'")
    sr = _of("solver_refuses")
    sr["solver_reason"] = "made_up"
    assert validate_fixture(sr) == ("invalid", "unknown_solver_reason:'made_up'")


def test_validator_rejects_unknown_expect() -> None:
    assert validate_fixture({"expect": "bogus"}) == ("invalid", "unknown_expect:'bogus'")


def test_validator_rejects_missing_or_unlabeled_answer() -> None:
    fx = _solved()
    fx["answer"] = "Z"  # label not in options
    assert validate_fixture(fx) == ("invalid", "missing_or_unlabeled_answer")


def test_validator_rejects_non_int_gold() -> None:
    fx = _solved()
    fx["gold"] = "twenty"
    assert validate_fixture(fx) == ("invalid", "solved_needs_int_gold")


# --- the canonical-outcome cross-check (H1/H2/G5): label/gold must match the arithmetic --------- #


def _solver_refuse_fixture(**over: object) -> dict:
    """A well-formed solver_refuses-shaped fixture (default: cmb-07b-like, eff=-3 -> refuses)."""
    base = {
        "id": "t", "expect": "solver_refuses", "solver_reason": "non_positive_net_rate",
        "rate_unit": {"numerator": "liter", "denominator": "minute"},
        "rate_a": 2, "rate_b": 5, "combine_mode": "difference",
        "time": 3, "time_unit": "minute", "quantity": None, "query": "quantity", "gold": None,
    }
    base.update(over)
    return base


def test_validator_rejects_solver_refuse_that_is_actually_solvable() -> None:
    # H1: positive net rate (5-2=3) mislabeled non_positive_net_rate.
    h1 = _solver_refuse_fixture(rate_a=5, rate_b=2)
    assert validate_fixture(h1) == ("invalid", "solver_refuses_is_actually_solvable")
    # H2: a quantity query (eff*time is always integral) mislabeled non_integer_solution.
    h2 = _solver_refuse_fixture(
        combine_mode="sum", rate_a=3, rate_b=2, solver_reason="non_integer_solution"
    )
    assert validate_fixture(h2) == ("invalid", "solver_refuses_is_actually_solvable")


def test_validator_rejects_solver_reason_mismatch() -> None:
    # Genuinely refuses, but for the WRONG reason: eff=-3 on a time query is non_positive, not non_integer.
    fx = _solver_refuse_fixture(query="time", time=None, quantity=12, solver_reason="non_integer_solution")
    assert validate_fixture(fx) == ("invalid", "solver_reason_mismatch:expected_non_positive_net_rate")


def test_validator_rejects_wrong_gold_even_with_coherent_answer_key() -> None:
    # G5: gold is internally answer-key-coherent but does not equal the canonical computed answer.
    fx = _solved()  # cmb-01: (3+2)*4 = 20
    fx["gold"] = 21
    fx["options"] = {**fx["options"], fx["answer"]: 21}  # keep options[answer] == gold
    assert validate_fixture(fx) == ("invalid", "gold_does_not_match_computed_answer")


def test_canonical_outcome_matrix() -> None:
    from evals.combined_rate_oracle.runner import _canonical_outcome

    def cro(ra, rb, mode, time, qty, query):
        return _canonical_outcome(CombinedRateProblem(ra, rb, _ROOM_HOUR, mode, time, qty, query))

    assert cro(3, 2, "sum", 4, None, "quantity") == ("solved", 20, None)
    assert cro(5, 2, "difference", 6, None, "quantity") == ("solved", 18, None)
    assert cro(3, 2, "sum", None, 20, "time") == ("solved", 4, None)
    assert cro(5, 2, "difference", None, 18, "time") == ("solved", 6, None)
    assert cro(9, 4, "difference", None, None, "effective_rate") == ("solved", 5, None)
    assert cro(6, 4, "sum", None, None, "effective_rate") == ("solved", 10, None)
    # refusals
    assert cro(4, 4, "difference", 5, None, "quantity") == ("refused", None, "non_positive_net_rate")
    assert cro(4, 4, "difference", None, 12, "time") == ("refused", None, "non_positive_net_rate")
    assert cro(3, 2, "sum", None, 12, "time") == ("refused", None, "non_integer_solution")
    # an effective_rate query is well-defined even when the net is non-positive (never refuses)
    assert cro(4, 4, "difference", None, None, "effective_rate") == ("solved", 0, None)


def test_validator_rejects_malformed_setup_missing_rate() -> None:
    fx = _solved()
    fx["rate_b"] = None  # only one explicit rate -> model __post_init__ raises
    assert validate_fixture(fx)[0] == "invalid"


def test_validator_rejects_unknown_combine_mode_in_gold() -> None:
    fx = _solved()
    fx["combine_mode"] = "average"  # not a real combine mode -> model raises -> malformed_setup
    outcome, reason = validate_fixture(fx)
    assert outcome == "invalid" and reason is not None and reason.startswith("malformed_setup")


# --- off-serving guarantee ------------------------------------------------------------- #


def test_combined_rate_organ_is_off_serving() -> None:
    # Check actual IMPORTS (via AST), not raw text — the docstrings legitimately *name* the
    # serving modules to assert disjointness, so a substring scan would false-positive.
    import ast

    import evals.combined_rate_oracle as oracle_pkg
    import generate.combined_rate_comprehension as organ_pkg

    forbidden = ("generate.derivation", "core.reliability_gate")
    for pkg in (organ_pkg, oracle_pkg):
        for py in Path(str(pkg.__file__)).resolve().parent.glob("*.py"):
            for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    assert not any(name.startswith(t) for t in forbidden), f"{py.name}: imports {name}"
