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

from core.reasoning import evidence_from_entailment_trace
from evals.deductive_logic.generate import _make_case
from evals.deductive_logic.oracle import oracle_entailment
from evals.deductive_logic.runner import _ROOT, _load, build_report
from generate.logic_canonical import LogicBudgetError
from generate.proof_chain.entail import (
    INCONSISTENT_PREMISES,
    OUT_OF_REGIME_OR_MALFORMED,
    TAUTOLOGICAL_IMPLICATION,
    Entailment,
    evaluate_entailment,
    evaluate_entailment_with_trace,
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


def test_budget_error_refuses_typed(monkeypatch) -> None:
    def boom(_formula: str):
        raise LogicBudgetError("too many nodes")

    monkeypatch.setattr("generate.proof_chain.entail.canonicalize", boom)

    v = evaluate_entailment(("P",), "Q")
    assert v.outcome is Entailment.REFUSED
    assert v.reason == OUT_OF_REGIME_OR_MALFORMED


def test_entailment_trace_is_deterministic_evidence() -> None:
    t1 = evaluate_entailment_with_trace(("P", "P -> Q"), "Q")
    t2 = evaluate_entailment_with_trace(("P", "P -> Q"), "Q")

    assert t1.outcome is Entailment.ENTAILED
    assert t1.reason == TAUTOLOGICAL_IMPLICATION
    assert t1.premise_keys
    assert t1.conjunction_key is not None
    assert t1.query_key is not None
    assert t1.entailment_check_key == "T"
    assert t1.refutation_check_key is not None
    assert t1.canonical_json() == t2.canonical_json()
    assert "premise_keys" in t1.canonical_json()

    evidence = evidence_from_entailment_trace(t1)
    assert evidence.domain == "mathematics_logic"
    assert evidence.operator == "propositional_entailment"
    assert evidence.outcome == "entailed"
    assert evidence.commitment_key.startswith("entailment:entailed:")
    assert evidence.evidence_hash == evidence_from_entailment_trace(t2).evidence_hash


def test_refused_trace_preserves_available_canonical_evidence() -> None:
    trace = evaluate_entailment_with_trace(("P",), "P & & Q")

    assert trace.outcome is Entailment.REFUSED
    assert trace.reason == OUT_OF_REGIME_OR_MALFORMED
    assert trace.premise_keys
    assert trace.conjunction_key is not None
    assert trace.query_key is None
    assert trace.entailment_check_key is None
    assert trace.refutation_check_key is None


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
    assert report["counts"]["refused"] == 0
    assert report["all_cases_correct"] is True
    # the sizeable, honest signal: non-trivial deductions decided correctly
    cbg = report["correct_by_gold"]
    assert cbg.get("entailed", 0) >= 50
    assert cbg.get("refuted", 0) >= 50


def test_dev_lane_wrong_is_zero() -> None:
    report = build_report(_load(_ROOT / "dev" / "cases.jsonl"))
    assert report["n"] == 200
    assert report["counts"]["wrong"] == 0
    assert report["counts"]["refused"] == 0
    assert report["all_cases_correct"] is True


def test_external_mirror_lane_matches_independent_oracle() -> None:
    cases = _load(_ROOT / "external" / "v1" / "cases.jsonl")
    report = build_report(cases)
    assert report["n"] == 16
    assert report["all_cases_correct"] is True
    assert report["counts"] == {"correct": 16, "wrong": 0, "refused": 0}
    for case in cases:
        assert oracle_entailment(tuple(case["premises"]), case["query"]) == case["gold"]


def test_refusal_boundary_split_refuses_every_case() -> None:
    cases = _load(_ROOT / "refusal" / "v1" / "cases.jsonl")
    assert len(cases) == 4
    for case in cases:
        verdict = evaluate_entailment(tuple(case["premises"]), case["query"])
        assert case["gold"] == "refused"
        assert verdict.outcome is Entailment.REFUSED


def test_runner_treats_committed_refusal_as_capability_failure() -> None:
    report = build_report([
        {"id": "bad-refusal", "premises": ["P", "~P"], "query": "Q", "gold": "entailed"}
    ])
    assert report["counts"]["wrong"] == 0
    assert report["counts"]["refused"] == 1
    assert report["all_cases_correct"] is False
