"""Binary-relation + multi-variable grounding extension (deductive-logic runway #1).

Extends the finite-entity grounding from unary predicates / single-var rules to
binary relations and multi-variable universal rules, still by FINITE PROPOSITIONAL
grounding into the regime the ROBDD entailment operator + the independent truth-table
oracle both decide. wrong==0 stays structural: every committed case is checked
engine==oracle==(open-world) gold, and anything outside the regime refuses.

Two contracts this pins hard:
- **back-compat**: existing unary problems lower byte-identically (no panel regression);
- **the oracle-tractability ceiling**: the gold is O(2^atoms), so the grounding refuses
  above a pinned distinct-atom bound (GROUNDING_BOUND_EXCEEDED) rather than emit a
  problem the independent gold cannot decide.
"""

from __future__ import annotations

import random

import pytest

from evals.deductive_logic.grounding import (
    GROUNDING_BOUND_EXCEEDED,
    UNSAFE_RULE,
    UNSUPPORTED_PREDICATE_ARITY,
    UNSUPPORTED_QUANTIFIER,
    GroundingError,
    MAX_GROUND_ATOMS,
    atom_n,
    lower_case,
)
from evals.deductive_logic.oracle import oracle_entailment
from generate.proof_chain.entail import evaluate_entailment


def _decide(case: dict) -> tuple[str, str]:
    gp = lower_case(case)
    engine = evaluate_entailment(gp.premises, gp.query).outcome.value
    oracle = oracle_entailment(gp.premises, gp.query)
    return engine, oracle


# --- back-compat: unary lowers exactly as before ---------------------------


def test_unary_back_compat_entailed():
    case = {
        "entities": ["cat", "dog"],
        "facts": [{"predicate": "furry", "entity": "cat", "polarity": True}],
        "rules": [{"if": [{"predicate": "furry", "var": "x", "polarity": True}],
                   "then": {"predicate": "mammal", "var": "x", "polarity": True}}],
        "query": {"predicate": "mammal", "entity": "cat", "polarity": True},
    }
    gp = lower_case(case)
    # exact atom + clause strings the unary path produced before the extension
    assert gp.query == "mammal__cat"
    assert "furry__cat" in gp.premises
    assert "((furry__cat)) -> (mammal__cat)" in gp.premises
    assert "((furry__dog)) -> (mammal__dog)" in gp.premises
    engine, oracle = _decide(case)
    assert engine == oracle == "entailed"


# --- binary relations ------------------------------------------------------


def test_binary_atom_form():
    assert atom_n("loves", ["a", "b"]) == "loves__a__b"
    assert atom_n("furry", ["cat"]) == "furry__cat"  # arity-1 unchanged


def test_binary_fact_and_query():
    case = {
        "entities": ["alice", "bob"],
        "facts": [{"predicate": "loves", "args": [{"entity": "alice"}, {"entity": "bob"}],
                   "polarity": True}],
        "query": {"predicate": "loves", "args": [{"entity": "alice"}, {"entity": "bob"}],
                  "polarity": True},
    }
    engine, oracle = _decide(case)
    assert engine == oracle == "entailed"


def test_transitivity_entailed():
    """The canonical RuleTaker/ProofWriter shape: a 3-variable transitive rule."""
    case = {
        "entities": ["bear", "dog", "cat"],
        "facts": [
            {"predicate": "bigger", "args": [{"entity": "bear"}, {"entity": "dog"}], "polarity": True},
            {"predicate": "bigger", "args": [{"entity": "dog"}, {"entity": "cat"}], "polarity": True},
        ],
        "rules": [{
            "if": [
                {"predicate": "bigger", "args": [{"var": "x"}, {"var": "y"}], "polarity": True},
                {"predicate": "bigger", "args": [{"var": "y"}, {"var": "z"}], "polarity": True},
            ],
            "then": {"predicate": "bigger", "args": [{"var": "x"}, {"var": "z"}], "polarity": True},
        }],
        "query": {"predicate": "bigger", "args": [{"entity": "bear"}, {"entity": "cat"}], "polarity": True},
    }
    engine, oracle = _decide(case)
    assert engine == oracle == "entailed"


def test_transitivity_unknown_is_open_world():
    """The reverse direction is NOT derivable → unknown under OPEN-world entailment
    (NOT 'refuted' — this is exactly why CWA benchmark splits must refuse, not map here)."""
    case = {
        "entities": ["bear", "dog", "cat"],
        "facts": [
            {"predicate": "bigger", "args": [{"entity": "bear"}, {"entity": "dog"}], "polarity": True},
            {"predicate": "bigger", "args": [{"entity": "dog"}, {"entity": "cat"}], "polarity": True},
        ],
        "rules": [{
            "if": [
                {"predicate": "bigger", "args": [{"var": "x"}, {"var": "y"}], "polarity": True},
                {"predicate": "bigger", "args": [{"var": "y"}, {"var": "z"}], "polarity": True},
            ],
            "then": {"predicate": "bigger", "args": [{"var": "x"}, {"var": "z"}], "polarity": True},
        }],
        "query": {"predicate": "bigger", "args": [{"entity": "cat"}, {"entity": "bear"}], "polarity": True},
    }
    engine, oracle = _decide(case)
    assert engine == oracle == "unknown"


# --- regime refusals -------------------------------------------------------


def test_arity_three_refuses():
    case = {
        "entities": ["a", "b", "c"],
        "facts": [{"predicate": "between",
                   "args": [{"entity": "a"}, {"entity": "b"}, {"entity": "c"}], "polarity": True}],
        "query": {"predicate": "between",
                  "args": [{"entity": "a"}, {"entity": "b"}, {"entity": "c"}], "polarity": True},
    }
    with pytest.raises(GroundingError) as exc:
        lower_case(case)
    assert exc.value.reason == UNSUPPORTED_PREDICATE_ARITY


def test_unsafe_rule_refuses():
    """A range-restricted multi-var rule (transitivity) is fine; an unsafe one — a
    head variable unbound in the body — refuses."""
    case = {
        "entities": ["a", "b"],
        "facts": [{"predicate": "p", "args": [{"entity": "a"}, {"entity": "b"}], "polarity": True}],
        "rules": [{
            "if": [{"predicate": "p", "args": [{"var": "x"}, {"var": "y"}], "polarity": True}],
            "then": {"predicate": "q", "args": [{"var": "x"}, {"var": "z"}], "polarity": True},  # z unbound
        }],
        "query": {"predicate": "q", "args": [{"entity": "a"}, {"entity": "b"}], "polarity": True},
    }
    with pytest.raises(GroundingError) as exc:
        lower_case(case)
    assert exc.value.reason == UNSAFE_RULE


def test_explicit_quantifier_refuses():
    case = {
        "entities": ["a"],
        "rules": [{"exists": True, "if": [{"predicate": "p", "var": "x", "polarity": True}],
                   "then": {"predicate": "q", "var": "x", "polarity": True}}],
        "query": {"predicate": "q", "entity": "a", "polarity": True},
    }
    with pytest.raises(GroundingError) as exc:
        lower_case(case)
    assert exc.value.reason == UNSUPPORTED_QUANTIFIER


def test_atom_bound_refuses_intractable_oracle():
    """A binary rule over 6 entities grounds to 36 binary atoms > the bound: refuse
    rather than hand the O(2^atoms) gold a problem it cannot decide."""
    ents = ["e0", "e1", "e2", "e3", "e4", "e5"]
    case = {
        "entities": ents,
        "facts": [{"predicate": "r", "args": [{"entity": "e0"}, {"entity": "e1"}], "polarity": True}],
        "rules": [{
            "if": [{"predicate": "r", "args": [{"var": "x"}, {"var": "y"}], "polarity": True},
                   {"predicate": "r", "args": [{"var": "y"}, {"var": "z"}], "polarity": True}],
            "then": {"predicate": "r", "args": [{"var": "x"}, {"var": "z"}], "polarity": True},
        }],
        "query": {"predicate": "r", "args": [{"entity": "e0"}, {"entity": "e5"}], "polarity": True},
    }
    with pytest.raises(GroundingError) as exc:
        lower_case(case)
    assert exc.value.reason == GROUNDING_BOUND_EXCEEDED


# --- held-out differential fuzz: engine == oracle on random binary problems --


def _random_binary_case(rng: random.Random) -> dict:
    # One binary predicate over 2-3 entities → <=9 atoms, so the O(2^atoms) gold
    # stays fast while still exercising binary facts + a multi-var transitive rule.
    ents = [f"e{i}" for i in range(rng.randint(2, 3))]
    facts = []
    for a in ents:
        for b in ents:
            if rng.random() < 0.4:
                facts.append({"predicate": "r", "args": [{"entity": a}, {"entity": b}],
                              "polarity": rng.random() < 0.85})
    rules = []
    if rng.random() < 0.75:
        rules.append({
            "if": [{"predicate": "r", "args": [{"var": "x"}, {"var": "y"}], "polarity": True},
                   {"predicate": "r", "args": [{"var": "y"}, {"var": "z"}], "polarity": True}],
            "then": {"predicate": "r", "args": [{"var": "x"}, {"var": "z"}], "polarity": True},
        })
    qa, qb = rng.choice(ents), rng.choice(ents)
    query = {"predicate": "r", "args": [{"entity": qa}, {"entity": qb}],
             "polarity": rng.random() < 0.85}
    return {"entities": ents, "facts": facts, "rules": rules, "query": query}


def test_held_out_fuzz_engine_equals_oracle():
    """wrong==0 on held-out (oracle-golded, never hand-authored) random binary problems.
    The independent truth-table oracle is the gold; the ROBDD engine must match it on
    every in-regime case. A single mismatch is a soundness breach."""
    rng = random.Random(20260604)
    decided = 0
    mismatches: list[str] = []
    for _ in range(400):
        case = _random_binary_case(rng)
        try:
            gp = lower_case(case)
        except GroundingError:
            continue  # out-of-regime / over-bound → refused, not scored
        engine = evaluate_entailment(gp.premises, gp.query).outcome.value
        oracle = oracle_entailment(gp.premises, gp.query)
        decided += 1
        if engine != oracle:
            mismatches.append(f"{engine}!={oracle} :: {gp.premises} |- {gp.query}")
    assert decided >= 50, f"too few in-regime cases ({decided}) — fuzz is near-vacuous"
    assert not mismatches, f"{len(mismatches)} engine/oracle mismatches; first: {mismatches[:3]}"
    assert MAX_GROUND_ATOMS <= 24  # the oracle stays tractable
