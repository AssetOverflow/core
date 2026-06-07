"""Unit tests for the R2 constraint IR (C1) — pure dataclasses, no behavior.

Pins the typed shape the gold/oracle (C2) and solver (C3) build on: unknowns with a
finite-integer domain, attribute coefficients, a canonical linear system, and a minimal
query. Frozen-ness is load-bearing (the immutability doctrine — the IR is value data); the
bus + chickens systems are pinned as IR so later slices can assert the reader reconstructs
exactly these.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from generate.constraint_comprehension import (
    AttributeFact,
    ConstraintProblem,
    ConstraintQuery,
    LinearConstraint,
    LinearExpr,
    Unknown,
)


def _bus_problem() -> ConstraintProblem:
    # 6 buses total; large holds 50, small holds 30; 260 students; ask large.
    return ConstraintProblem(
        unknowns=(
            Unknown("large_bus", "large bus", "bus", "nonnegative_integer"),
            Unknown("small_bus", "small bus", "bus", "nonnegative_integer"),
        ),
        facts=(
            AttributeFact("large_bus", "student", 50),
            AttributeFact("small_bus", "student", 30),
        ),
        constraints=(
            LinearConstraint(LinearExpr((("large_bus", 1), ("small_bus", 1))), "eq", 6),
            LinearConstraint(LinearExpr((("large_bus", 50), ("small_bus", 30))), "eq", 260),
        ),
        query=ConstraintQuery("large_bus", "bus"),
    )


def test_bus_problem_ir_shape() -> None:
    p = _bus_problem()
    assert tuple(u.symbol for u in p.unknowns) == ("large_bus", "small_bus")
    assert all(u.domain == "nonnegative_integer" for u in p.unknowns)
    assert p.constraints[0].relation == "eq" and p.constraints[0].rhs == 6
    assert p.constraints[1].lhs.terms == (("large_bus", 50), ("small_bus", 30))
    assert p.query == ConstraintQuery("large_bus", "bus")


def test_chickens_problem_ir_shape() -> None:
    # 18 animals; chickens 2 legs, cows 4 legs; 50 legs; ask chickens.
    p = ConstraintProblem(
        unknowns=(
            Unknown("chicken", "chicken", "animal", "nonnegative_integer"),
            Unknown("cow", "cow", "animal", "nonnegative_integer"),
        ),
        facts=(AttributeFact("chicken", "leg", 2), AttributeFact("cow", "leg", 4)),
        constraints=(
            LinearConstraint(LinearExpr((("chicken", 1), ("cow", 1))), "eq", 18),
            LinearConstraint(LinearExpr((("chicken", 2), ("cow", 4))), "eq", 50),
        ),
        query=ConstraintQuery("chicken", "animal"),
    )
    assert {f.measured_unit for f in p.facts} == {"leg"}
    assert p.constraints[1].lhs.terms == (("chicken", 2), ("cow", 4))


def test_linear_expr_constant_defaults_zero() -> None:
    assert LinearExpr((("x", 1),)).constant == 0


def test_constraint_source_span_defaults_none() -> None:
    # Gold-authored constraints carry no input span; the reader (C5+) populates it.
    assert LinearConstraint(LinearExpr((("x", 1),)), "eq", 3).source_span is None


@pytest.mark.parametrize(
    "obj",
    [
        Unknown("x", "x", "item", "integer"),
        AttributeFact("x", "leg", 2),
        ConstraintQuery("x", "item"),
        LinearExpr((("x", 1),)),
        LinearConstraint(LinearExpr((("x", 1),)), "eq", 1),
    ],
)
def test_ir_dataclasses_are_frozen(obj: Any) -> None:
    # Immutability doctrine: the IR is value data — mutation must raise, never silently alias.
    field = dataclasses.fields(obj)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(obj, field, getattr(obj, field))
