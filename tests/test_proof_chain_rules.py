"""ADR-0205 — modus_ponens + disagreement rule (phase 2.3).

The 24 adversarial corpus cases (GPT-5.5's independent oracle) transcribed for a
committed, reproducible cross-check against the real rule: 6 valid / 8 invalid /
10 disagreement. The disagreement cases are the wrong=0 guard — 007/010 in
particular pin the pooling semantics: pool ALL admissible MP derivations and
require a unique key. A filter-to-declared-conclusion-first rule would admit them
(admit-by-assertion); pool-first refuses. That test failing under filter-first is
the proof the soundness mechanism is load-bearing.
"""

from __future__ import annotations

import pytest

from generate.proof_chain import (
    CONCLUSION_DISAGREEMENT,
    CONCLUSION_MISMATCH,
    MISSING_IMPLICATION,
    MP_REASONS,
    Proof,
    ProofNode,
    UNESTABLISHED_ANTECEDENT,
    UNIQUE_CANONICAL_CONCLUSION,
    MPOutcome,
    evaluate_modus_ponens,
    evaluate_proof_conclusion,
)

# (id, premises, conclusion, expected_outcome, expected_reason)  — reasons are the
# CLOSED set; the corpus's finer labels collapse onto them (ADR-0205 §reason-set).
CASES = [
    # --- valid (admit) ---
    ("VALID-001", ("P", "P -> Q"), "Q", "admit", UNIQUE_CANONICAL_CONCLUSION),
    ("VALID-002", ("P_rains", "P_rains -> Q_ground_wet"), "Q_ground_wet", "admit", UNIQUE_CANONICAL_CONCLUSION),
    ("VALID-003", ("P and R", "(P and R) -> Q"), "Q", "admit", UNIQUE_CANONICAL_CONCLUSION),
    ("VALID-004", ("P_switch_on", "P_switch_on -> (Q_lamp_lit or R_alarm_on)"), "Q_lamp_lit or R_alarm_on", "admit", UNIQUE_CANONICAL_CONCLUSION),
    ("VALID-005", ("P", "P -> (Q -> R)"), "Q -> R", "admit", UNIQUE_CANONICAL_CONCLUSION),
    ("VALID-006", ("(P or Q) and not R", "((P or Q) and not R) -> S"), "S", "admit", UNIQUE_CANONICAL_CONCLUSION),
    # --- invalid (refuse, typed) ---
    ("INVALID-001", ("P", "P -> Q"), "R", "refuse", CONCLUSION_MISMATCH),
    ("INVALID-002", ("P",), "Q", "refuse", MISSING_IMPLICATION),
    ("INVALID-003", ("Q", "P -> Q"), "P", "refuse", UNESTABLISHED_ANTECEDENT),  # corpus: affirming_consequent
    ("INVALID-004", ("R", "P -> Q"), "Q", "refuse", UNESTABLISHED_ANTECEDENT),  # corpus: antecedent_mismatch
    ("INVALID-005", ("P", "Q -> P"), "Q", "refuse", UNESTABLISHED_ANTECEDENT),  # corpus: implication_direction_mismatch
    ("INVALID-006", ("P", "(P or R) -> Q"), "Q", "refuse", UNESTABLISHED_ANTECEDENT),  # corpus: antecedent_mismatch
    ("INVALID-007", ("P", "P -> (Q or R)"), "Q", "refuse", CONCLUSION_MISMATCH),
    ("INVALID-008", ("P -> Q",), "Q", "refuse", UNESTABLISHED_ANTECEDENT),  # corpus: missing_antecedent
    # --- disagreement (admit: collapse to one key; refuse: distinct keys) ---
    ("DISAGREE-001", ("A", "A -> C", "B", "B -> C"), "C", "admit", UNIQUE_CANONICAL_CONCLUSION),
    ("DISAGREE-002", ("A", "A -> (P and Q)", "B", "B -> (Q and P)"), "P and Q", "admit", UNIQUE_CANONICAL_CONCLUSION),
    ("DISAGREE-003", ("A", "A -> (Q -> R)", "B", "B -> (not Q or R)"), "Q -> R", "admit", UNIQUE_CANONICAL_CONCLUSION),
    ("DISAGREE-004", ("A", "A -> Q", "B", "B -> (Q and (R or not R))"), "Q", "admit", UNIQUE_CANONICAL_CONCLUSION),
    ("DISAGREE-005", ("A", "A -> (P and Q)", "B", "B -> (P or Q)"), "P and Q", "refuse", CONCLUSION_DISAGREEMENT),
    ("DISAGREE-006", ("A", "A -> Q_ground_wet", "B", "B -> Q_ground_damp"), "Q_ground_wet", "refuse", CONCLUSION_DISAGREEMENT),
    ("DISAGREE-007", ("A", "A -> (R or not R)", "B", "B -> Q"), "Q", "refuse", CONCLUSION_DISAGREEMENT),
    ("DISAGREE-008", ("A", "A -> Q", "B", "B -> not Q"), "Q", "refuse", CONCLUSION_DISAGREEMENT),
    ("DISAGREE-009", ("A", "A -> (P -> Q)", "B", "B -> (Q -> P)"), "P -> Q", "refuse", CONCLUSION_DISAGREEMENT),
    ("DISAGREE-010", ("A", "A -> Q", "B", "B -> (Q and R)"), "Q", "refuse", CONCLUSION_DISAGREEMENT),
]


@pytest.mark.parametrize("cid,premises,conclusion,outcome,reason", CASES, ids=[c[0] for c in CASES])
def test_corpus_case(cid, premises, conclusion, outcome, reason) -> None:
    v = evaluate_modus_ponens(premises, conclusion)
    assert v.outcome.value == outcome, cid
    assert v.reason == reason, cid
    assert v.reason in MP_REASONS


def test_admit_yields_the_canonical_conclusion_key() -> None:
    from generate.logic_canonical import canonicalize
    v = evaluate_modus_ponens(("P", "P -> Q"), "Q")
    assert v.outcome is MPOutcome.ADMIT
    assert v.conclusion_key == canonicalize("Q").canonical_key


# ---------------------------------------------------------------------------
# The pooling semantics — the wrong=0 mechanism. 007/010 MUST refuse: the premises
# admit deriving a second distinct key, so pool-first refuses. A filter-first rule
# (keep only derivations whose key == declared conclusion, then check uniqueness)
# would admit both — admit-by-assertion. These assertions fail under that mutation.
# ---------------------------------------------------------------------------


def test_pooling_refuses_unrelated_tautology_path() -> None:
    # 007: one path yields T (R or not R), the substantive path yields Q.
    v = evaluate_modus_ponens(("A", "A -> (R or not R)", "B", "B -> Q"), "Q")
    assert v.outcome is MPOutcome.REFUSE
    assert v.reason == CONCLUSION_DISAGREEMENT
    assert len(v.derived_keys) == 2  # T and key(Q) — distinct, pooled


def test_pooling_refuses_stronger_conclusion_path() -> None:
    # 010: paths yield Q and (Q and R) — distinct keys.
    v = evaluate_modus_ponens(("A", "A -> Q", "B", "B -> (Q and R)"), "Q")
    assert v.outcome is MPOutcome.REFUSE
    assert v.reason == CONCLUSION_DISAGREEMENT
    assert len(v.derived_keys) == 2


def test_equivalent_paths_collapse_not_disagree() -> None:
    # 003: Q->R and (not Q or R) are equivalent → one key → admit.
    v = evaluate_modus_ponens(("A", "A -> (Q -> R)", "B", "B -> (not Q or R)"), "Q -> R")
    assert v.outcome is MPOutcome.ADMIT
    assert len(v.derived_keys) == 1


# ---------------------------------------------------------------------------
# Wiring to the ADR-0204 Proof.
# ---------------------------------------------------------------------------


def test_evaluate_proof_conclusion_via_builder_shape() -> None:
    proof = Proof(
        nodes=(
            ProofNode("premise_0", "P", (), "premise"),
            ProofNode("premise_1", "P -> Q", (), "premise"),
            ProofNode("conclusion", "Q", ("premise_0", "premise_1"), "modus_ponens"),
        ),
        conclusion_id="conclusion",
    )
    v = evaluate_proof_conclusion(proof)
    assert v.outcome is MPOutcome.ADMIT
    assert v.reason == UNIQUE_CANONICAL_CONCLUSION
