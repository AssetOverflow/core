"""Phase 2 — finite-entity grounding compiler (deductive-logic runway PR-1/PR-2).

Proves the first comprehension compiler lowers a typed finite-entity problem into
the propositional regime deterministically and refusal-first, and that the lowered
form is decided identically by the ROBDD engine AND the independent truth-table
oracle (INV-25: the committed gold is reproduced by a procedure sharing no code
with the engine).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.deductive_logic.grounding import (
    MALFORMED_CASE,
    UNKNOWN_ENTITY,
    UNSAFE_RULE,
    UNSAFE_SYMBOL,
    UNSUPPORTED_PREDICATE_ARITY,
    GroundingError,
    atom,
    lower_case,
    slug,
)
from evals.deductive_logic.oracle import oracle_entailment
from generate.proof_chain.entail import evaluate_entailment

_FIXTURE = Path(__file__).resolve().parents[1] / "evals" / "deductive_logic" / "finite_entity" / "v1" / "cases.jsonl"


def _load_fixture() -> list[dict]:
    return [json.loads(line) for line in _FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()]


# --- lowering correctness -----------------------------------------------------


def test_atom_lowering_is_deterministic_and_canonical() -> None:
    assert atom("Furry", "Cat") == "furry__cat"
    assert atom("furry", "cat") == atom("Furry", " CAT ")  # case/space-insensitive
    assert atom("needs_food", "cat") == "needs_food__cat"


def test_unsafe_symbols_and_separator_ambiguity_reject() -> None:
    for bad in ("fur__ry", "9lives", "", "has-claws", "a b", "tïger"):
        with pytest.raises(GroundingError) as exc:
            slug(bad)
        assert exc.value.reason == UNSAFE_SYMBOL


def test_fact_lowering_including_negative_facts() -> None:
    case = {
        "entities": ["cat"],
        "facts": [
            {"predicate": "furry", "entity": "cat", "polarity": True},
            {"predicate": "aquatic", "entity": "cat", "polarity": False},
        ],
        "query": {"predicate": "furry", "entity": "cat", "polarity": True},
    }
    gp = lower_case(case)
    assert "furry__cat" in gp.premises
    assert "~aquatic__cat" in gp.premises


def test_unary_universal_rule_expands_over_all_entities() -> None:
    case = {
        "entities": ["cat", "dog", "fish"],
        "facts": [],
        "rules": [{"if": [{"predicate": "furry", "var": "x", "polarity": True}],
                   "then": {"predicate": "mammal", "var": "x", "polarity": True}}],
        "query": {"predicate": "mammal", "entity": "cat", "polarity": True},
    }
    gp = lower_case(case)
    grounded = [p for p in gp.premises if "->" in p]
    assert len(grounded) == 3  # one per entity
    assert any("furry__cat" in p and "mammal__cat" in p for p in grounded)
    assert any("furry__dog" in p and "mammal__dog" in p for p in grounded)
    assert any("furry__fish" in p and "mammal__fish" in p for p in grounded)


def test_conjunctive_rule_body_lowers_to_conjunction() -> None:
    case = {
        "entities": ["t"],
        "facts": [],
        "rules": [{"if": [{"predicate": "red", "var": "x", "polarity": True},
                          {"predicate": "round", "var": "x", "polarity": True}],
                   "then": {"predicate": "apple", "var": "x", "polarity": True}}],
        "query": {"predicate": "apple", "entity": "t", "polarity": True},
    }
    gp = lower_case(case)
    rule = next(p for p in gp.premises if "->" in p)
    assert "red__t" in rule and "round__t" in rule and "&" in rule and "apple__t" in rule


# --- refusal boundary (typed reasons) ----------------------------------------


def test_unknown_entity_query_refuses() -> None:
    case = {"entities": ["cat"], "facts": [],
            "query": {"predicate": "furry", "entity": "mouse", "polarity": True}}
    with pytest.raises(GroundingError) as exc:
        lower_case(case)
    assert exc.value.reason == UNKNOWN_ENTITY


def test_unknown_entity_in_fact_refuses() -> None:
    case = {"entities": ["cat"],
            "facts": [{"predicate": "furry", "entity": "mouse", "polarity": True}],
            "query": {"predicate": "furry", "entity": "cat", "polarity": True}}
    with pytest.raises(GroundingError) as exc:
        lower_case(case)
    assert exc.value.reason == UNKNOWN_ENTITY


def test_binary_relation_refuses_as_unsupported_arity() -> None:
    # a relation carries a second argument key -> not unary -> refuse
    case = {"entities": ["a", "b"],
            "facts": [{"predicate": "loves", "entity": "a", "object": "b", "polarity": True}],
            "query": {"predicate": "loves", "entity": "a", "polarity": True}}
    with pytest.raises(GroundingError) as exc:
        lower_case(case)
    assert exc.value.reason == UNSUPPORTED_PREDICATE_ARITY


def test_unsafe_rule_unbound_head_var_refuses() -> None:
    """v1.5 supports multi-variable rules — but a rule whose HEAD variable is not
    bound in the body is non-range-restricted (unsafe) and still refuses. (Range-
    restricted multi-var rules like transitivity are exercised in
    test_deductive_logic_relational_grounding.py.)"""
    case = {"entities": ["a"],
            "rules": [{"if": [{"predicate": "p", "var": "x", "polarity": True}],
                       "then": {"predicate": "q", "var": "y", "polarity": True}}],
            "query": {"predicate": "p", "entity": "a", "polarity": True}}
    with pytest.raises(GroundingError) as exc:
        lower_case(case)
    assert exc.value.reason == UNSAFE_RULE


def test_empty_case_refuses() -> None:
    with pytest.raises(GroundingError) as exc:
        lower_case({})
    assert exc.value.reason in {"empty_case", MALFORMED_CASE}


# --- determinism + the lane gate (engine == oracle == committed gold) --------


def test_lowering_is_deterministic_across_replay() -> None:
    case = _load_fixture()[0]
    a = lower_case(case)
    b = lower_case(case)
    assert a == b


@pytest.mark.parametrize("case", _load_fixture(), ids=lambda c: c["id"])
def test_committed_gold_is_engine_and_independent_oracle_agreement(case: dict) -> None:
    """The lane gate: every committed finite-entity case is decided identically by
    the ROBDD engine AND the independent oracle, both equal to the committed gold."""
    gp = lower_case(case)
    engine = evaluate_entailment(gp.premises, gp.query).outcome.value
    oracle = oracle_entailment(gp.premises, gp.query)
    assert oracle == case["gold"], f"{case['id']}: independent oracle != committed gold"
    assert engine == case["gold"], f"{case['id']}: engine confabulated vs gold (wrong=0 breach)"


def test_fixture_has_nontrivial_signal() -> None:
    """Guard against a vacuous fixture: it must carry entailed/refuted cases, not
    only unknown/refused, or the lane proves nothing."""
    golds = {c["gold"] for c in _load_fixture()}
    assert "entailed" in golds and "refuted" in golds
