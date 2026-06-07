"""Tests for the R2 constraint setup oracle (C2) — the ruler before reader capability.

The runner validates the gold's internal coherence; these tests pin that the validator is
NON-VACUOUS — each ``invalid`` branch fires loudly when its violation is introduced (the
schema-proof-obligation discipline: a gate is real only if a test would fail under the
violation it is written to catch). Also pins signature order-independence + constant folding.
"""

from __future__ import annotations

import copy
from typing import Any

from evals.constraint_oracle.runner import (
    READER_REASONS,
    SOLVER_REASONS,
    _load_r2_gold,
    gold_to_problem,
    run,
    validate_fixture,
)
from evals.constraint_oracle.signature import (
    canonical_constraint,
    constraint_setup_signature,
)
from generate.constraint_comprehension.expr import LinearConstraint, LinearExpr
from generate.constraint_comprehension.model import ConstraintProblem


def _solved_fixture() -> dict[str, Any]:
    return copy.deepcopy(next(f for f in _load_r2_gold() if f["expect"] == "solved"))


def test_run_validates_all_gold() -> None:
    r = run()
    assert r["invalid"] == 0
    assert r["valid"] == r["total"] == 13
    assert r["by_expect"] == {"solved": 7, "solver_refuses": 3, "reader_refuses": 3}


def test_gold_to_problem_roundtrips_bus() -> None:
    fx = next(f for f in _load_r2_gold() if f["id"] == "r2-001-buses")
    p = gold_to_problem(fx)
    assert {u.symbol for u in p.unknowns} == {"large_bus", "small_bus"}
    assert all(u.domain == "nonnegative_integer" for u in p.unknowns)
    assert p.query.symbol == "large_bus"
    assert len(p.constraints) == 2


def test_signature_is_order_independent() -> None:
    p = gold_to_problem(next(f for f in _load_r2_gold() if f["id"] == "r2-001-buses"))
    shuffled = ConstraintProblem(
        unknowns=tuple(reversed(p.unknowns)),
        facts=tuple(reversed(p.facts)),
        constraints=tuple(
            LinearConstraint(
                LinearExpr(tuple(reversed(c.lhs.terms)), c.lhs.constant), c.relation, c.rhs
            )
            for c in reversed(p.constraints)
        ),
        query=p.query,
    )
    assert constraint_setup_signature(shuffled) == constraint_setup_signature(p)


def test_canonical_constraint_folds_constant_and_merges_terms() -> None:
    # x + y + 0x + 5 = 11  canonicalizes to ((x,1),(y,1)), "eq", 6 — constant folded into the
    # rhs, the duplicate x merged, the zero-coefficient term dropped.
    c = LinearConstraint(LinearExpr((("x", 1), ("y", 1), ("x", 0)), 5), "eq", 11)
    assert canonical_constraint(c) == ((("x", 1), ("y", 1)), "eq", 6)


def test_reader_and_solver_reasons_in_gold_are_closed() -> None:
    for fx in _load_r2_gold():
        if fx["expect"] == "solver_refuses":
            assert fx["solver_reason"] in SOLVER_REASONS
        elif fx["expect"] == "reader_refuses":
            assert fx["reader_reason"] in READER_REASONS


# --- meaningful-fail: each invalid branch must fire under exactly its violation -------- #


def test_validator_rejects_incoherent_answer_key() -> None:
    fx = _solved_fixture()
    fx["answer"] = next(k for k in fx["options"] if fx["options"][k] != fx["gold"])
    assert validate_fixture(fx) == ("invalid", "answer_key_incoherent")


def test_validator_rejects_three_categories() -> None:
    fx = _solved_fixture()
    fx["unknowns"].append(
        {"symbol": "z", "entity": "z", "unit": fx["unknowns"][0]["unit"], "domain": "nonnegative_integer"}
    )
    assert validate_fixture(fx) == ("invalid", "v1_requires_exactly_two_distinct_categories")


def test_validator_rejects_constraint_referencing_unknown_symbol() -> None:
    fx = _solved_fixture()
    fx["constraints"][0]["terms"][0][0] = "ghost"
    assert validate_fixture(fx) == ("invalid", "constraint_references_unknown_symbol")


def test_validator_rejects_query_not_a_category() -> None:
    fx = _solved_fixture()
    fx["query"]["symbol"] = "ghost"
    assert validate_fixture(fx) == ("invalid", "query_target_not_a_category")


def test_validator_rejects_solved_without_int_gold() -> None:
    fx = _solved_fixture()
    fx["gold"] = None
    assert validate_fixture(fx) == ("invalid", "solved_needs_int_gold")


def test_validator_rejects_reader_refuse_carrying_gold() -> None:
    fx = copy.deepcopy(next(f for f in _load_r2_gold() if f["expect"] == "reader_refuses"))
    fx["gold"] = 4
    assert validate_fixture(fx) == ("invalid", "reader_refuses_has_gold")


def test_validator_rejects_unknown_solver_reason() -> None:
    fx = copy.deepcopy(next(f for f in _load_r2_gold() if f["expect"] == "solver_refuses"))
    fx["solver_reason"] = "made_up"
    assert validate_fixture(fx)[0] == "invalid"


def test_validator_rejects_unknown_expect() -> None:
    fx = _solved_fixture()
    fx["expect"] = "teleported"
    assert validate_fixture(fx)[0] == "invalid"
