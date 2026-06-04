"""ADR-0206 — propositional entailment operator + the deductive-logic lane.

Three obligations, each able to fail loudly under the violation it guards:

1. **Soundness on classic inference shapes** — hand-verified modus ponens, multi-hop
   chains, modus tollens, disjunctive/hypothetical syllogism, and a genuine
   ``unknown`` all decide correctly.
2. **Refusal-first boundary** — inconsistent premises, out-of-regime (quantified)
   and malformed input all return a typed ``REFUSED`` rather than a guess.
3. **wrong=0 vs an independent oracle** — a deterministic fuzz cross-checks the
   ROBDD engine against the brute-force truth-table oracle on fresh random
   problems; any disagreement is a real soundness bug and fails this test. Plus the
   committed held-out lane holds ``wrong == 0``.
"""

from __future__ import annotations

import random

import pytest

from evals.deductive_logic.generate import _make_case
from evals.deductive_logic.oracle import oracle_entailment
from evals.deductive_logic.runner import _ROOT, _load, build_report
from generate.proof_chain.entail import (
    INCONSISTENT_PREMISES,
    OUT_OF_REGIME_OR_MALFORMED,
    Entailment,
    evaluate_entailment,
)


# --- 1. classic inference shapes (hand-verified) ---------------------------

@pytest.mark.parametrize(
    "premises,query,expected",
    [
        # modus ponens
        (("P", "P -> Q"), "Q", Entailment.ENTAILED),
        # multi-hop chain: P, P->Q, Q->R  ⊨  R
        (("P", "P -> Q", "Q -> R"), "R", Entailment.ENTAILED),
        # modus tollens: P->Q, ~Q  ⊨  ~P
        (("P -> Q", "~Q"), "~P", Entailment.ENTAILED),
        # disjunctive syllogism: P|Q, ~P  ⊨  Q
        (("P | Q", "~P"), "Q", Entailment.ENTAILED),
        # hypothetical syllogism (the conclusion is itself an implication)
        (("P -> Q", "Q -> R"), "P -> R", Entailment.ENTAILED),
        # refutation: P, P->~Q  ⊨  ~Q  (so Q is REFUTED)
        (("P", "P -> ~Q"), "Q", Entailment.REFUTED),
        # genuinely undetermined: nothing forces Q either way
        (("P", "R -> Q"), "Q", Entailment.UNKNOWN),
        # conjunctive antecedent rule: A, B, (A & B)->C ⊨ C
        (("A", "B", "(A & B) -> C"), "C", Entailment.ENTAILED),
        # conjunctive rule with a missing conjunct: A, (A & B)->C ⊭ C
        (("A", "(A & B) -> C"), "C", Entailment.UNKNOWN),
    ],
)
def test_classic_inferences(premises, query, expected) -> None:
    assert evaluate_entailment(premises, query).outcome is expected


# --- 2. refusal-first boundary --------------------------------------------

def test_inconsistent_premises_refuse() -> None:
    v = evaluate_entailment(("P", "~P"), "Q")
    assert v.outcome is Entailment.REFUSED
    assert v.reason == INCONSISTENT_PREMISES


def test_quantified_input_refuses_out_of_regime() -> None:
    v = evaluate_entailment(("forall x. P",), "P")
    assert v.outcome is Entailment.REFUSED
    assert v.reason == OUT_OF_REGIME_OR_MALFORMED


def test_predicate_application_refuses() -> None:
    assert evaluate_entailment(("rough(x)",), "P").outcome is Entailment.REFUSED


def test_malformed_query_refuses() -> None:
    assert evaluate_entailment(("P",), "P & & Q").outcome is Entailment.REFUSED


# --- 3a. wrong=0 vs the independent oracle (deterministic fuzz) -------------

def test_engine_matches_independent_oracle_fuzz() -> None:
    """ROBDD engine vs brute-force truth-table oracle on 3000 fresh random cases.

    These are two independently-coded sound decision procedures. A single
    disagreement means one of them is wrong — the property the GSM8K composer
    could never establish. Deterministic seed for reproducibility."""
    rng = random.Random(424242)
    checked = disagreements = 0
    for i in range(3000):
        case = _make_case(rng, f"t-{i}")
        if case is None:
            # generator-discarded == oracle said inconsistent; engine must REFUSE too
            continue
        checked += 1
        got = evaluate_entailment(tuple(case["premises"]), case["query"]).outcome.value
        if got != case["gold"]:
            disagreements += 1
    assert checked > 1500, f"fuzz produced too few definite cases ({checked})"
    assert disagreements == 0, f"{disagreements} engine/oracle disagreements"


def test_engine_refuses_every_inconsistent_case() -> None:
    """The complement: when the oracle reports inconsistency, the engine must also
    refuse (never silently 'decide' from a contradiction)."""
    rng = random.Random(515151)
    seen_inconsistent = 0
    for _ in range(4000):
        k = rng.randint(2, 4)
        atoms = [chr(ord("a") + j) for j in range(k)]
        prem = [rng.choice([at, f"~{at}"]) for at in atoms] + [
            rng.choice([at, f"~{at}"]) for at in atoms
        ]
        query = rng.choice(atoms)
        if oracle_entailment(tuple(prem), query) == "refused":
            seen_inconsistent += 1
            assert evaluate_entailment(tuple(prem), query).outcome is Entailment.REFUSED
    assert seen_inconsistent > 0  # the test actually exercised the path


# --- 3b. committed held-out lane holds wrong=0 -----------------------------

def test_holdout_lane_wrong_is_zero() -> None:
    report = build_report(_load(_ROOT / "holdout" / "v1" / "cases.jsonl"))
    assert report["n"] == 500
    assert report["counts"]["wrong"] == 0
    # the sizeable, honest signal: non-trivial deductions decided correctly
    cbg = report["correct_by_gold"]
    assert cbg.get("entailed", 0) >= 50
    assert cbg.get("refuted", 0) >= 50


def test_dev_lane_wrong_is_zero() -> None:
    report = build_report(_load(_ROOT / "dev" / "cases.jsonl"))
    assert report["n"] == 200
    assert report["counts"]["wrong"] == 0
