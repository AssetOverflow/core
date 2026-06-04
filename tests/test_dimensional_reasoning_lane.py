"""Dimensional-reasoning lane — the third diversity-panel domain.

Proves the binding-graph interlingua's unit algebra decides the dimension of a
unit operation identically to an independent dimensional oracle (sharing no code
with it), on every committed case — the same independent-gold discipline as the
deductive and finite-entity lanes, applied to a structurally distinct domain.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.dimensional.oracle import dimensional_result
from evals.dimensional.runner import decide

_FIXTURE = Path(__file__).resolve().parents[1] / "evals" / "dimensional" / "v1" / "cases.jsonl"


def _load() -> list[dict]:
    return [json.loads(line) for line in _FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.mark.parametrize("case", _load(), ids=lambda c: c["id"])
def test_interlingua_agrees_with_independent_oracle_and_gold(case: dict) -> None:
    """The lane gate: the interlingua's unit algebra (SUT) == the independent
    oracle == the committed gold, with wrong == 0 by construction."""
    oracle = dimensional_result(case["op"], case["left"], case["right"])
    sut = decide(case["op"], case["left"], case["right"])
    assert oracle == case["gold"], f"{case['id']}: independent oracle != committed gold"
    assert sut == case["gold"], f"{case['id']}: interlingua committed a wrong dimension (wrong=0 breach)"


def test_fixture_has_nontrivial_and_refusal_signal() -> None:
    """Guard against a vacuous fixture: it must carry composite dimensions AND a
    refusal, or the lane proves nothing."""
    golds = [c["gold"] for c in _load()]
    assert any("/" in g or "*" in g or "^" in g for g in golds), "no composite dimensions"
    assert "refused" in golds, "no refusal-boundary case"


def test_oracle_is_independent_of_the_sut() -> None:
    """The oracle must not IMPORT the interlingua it checks (AST, not substring —
    the docstring may name the SUT). Also enforced structurally by INV-25's
    registry; this is a fast local sanity check."""
    import ast
    import evals.dimensional.oracle as oracle_mod

    path = oracle_mod.__file__
    assert path is not None
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any(m.startswith("generate.binding_graph") for m in imported), (
        "oracle must share no code with the SUT (generate.binding_graph)"
    )


def test_dimensionless_and_distinct_units_same_dimension() -> None:
    # mile/hour and meter/second are different units, same dimension.
    assert decide("quotient", "mile", "hour") == decide("quotient", "meter", "second")
    assert decide("quotient", "foot", "foot") == "dimensionless"


def test_unknown_unit_refuses() -> None:
    assert decide("product", "gravitons", "second") == "refused"
    assert dimensional_result("product", "gravitons", "second") == "refused"
