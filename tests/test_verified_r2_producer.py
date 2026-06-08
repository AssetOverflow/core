"""P1-B — tests for the gold-setup-backed OFF-SERVING R2 verification producer.

The producer is NOT a serving-time VERIFIED producer: it uses the eval-lane gold SETUP
(never the gold answer) as the independent read. These tests prove it constructs real
VerificationProof objects that survive the P1-A contract on real R2 problems, AND that a
wrong/divergent read never verifies (wrong=0 for the producer).
"""

from __future__ import annotations

import ast
import inspect
import pathlib

from core.epistemic_disclosure.disclosure_claim import DisclosureClaim
from core.epistemic_disclosure.verified_contract import (
    REASON_BOUNDARY_FIRED,
    REASON_READS_DISAGREE,
    VerificationVerdict,
    disclosure_for_verification,
)
from core.epistemic_state import EpistemicState
from evals.constraint_oracle.runner import _load_r2_gold, gold_to_problem
from evals.constraint_oracle.signature import constraint_setup_signature
from evals.constraint_oracle.verified_producer import (
    CONSTRAINT_GOLD_AUTHOR_LINEAGE,
    CONSTRAINT_READER_LINEAGE,
    verify_r2,
)
from generate.constraint_comprehension.model import ConstraintProblem
from generate.constraint_comprehension.reader import read_constraint_problem
from generate.meaning_graph.reader import Refusal


def _gold():
    return _load_r2_gold()


def _solved_record():
    return next(r for r in _gold() if r.get("expect") == "solved")


# --- the producer verifies real problems, and NEVER on a divergent read ------------- #

def test_integration_real_gold_verifies_some_and_never_on_divergence():
    records = _gold()
    assert records
    # 'reader_refuses' fixtures carry no setup fields (there is no canonical setup for a
    # problem the reader must refuse). The reader refuses first, so gold_setup is unused on
    # that path — a placeholder keeps the loop uniform.
    placeholder = gold_to_problem(_solved_record())
    verified = 0
    for rec in records:
        has_setup = "unknowns" in rec
        gold = gold_to_problem(rec) if has_setup else placeholder
        outcome = verify_r2(rec["text"], gold)
        primary = read_constraint_problem(rec["text"])

        if isinstance(primary, Refusal):
            assert outcome.proof is None, rec["id"]
            assert outcome.limitation is not None, rec["id"]
            assert outcome.result.verdict is VerificationVerdict.NOT_VERIFIED, rec["id"]
            continue

        if not has_setup:
            # reader unexpectedly read a reader_refuses case; it must still not verify
            assert outcome.result.verdict is VerificationVerdict.NOT_VERIFIED, rec["id"]
            continue

        reads_converge = (
            constraint_setup_signature(primary) == constraint_setup_signature(gold)
        )
        if outcome.result.verdict is VerificationVerdict.VERIFIED:
            verified += 1
            # wrong=0 for the producer: a VERIFIED proof must have converged reads, a real
            # back-substitution, and the routed verified state/claim.
            assert reads_converge, rec["id"]
            assert outcome.proof is not None and outcome.proof.back_substitution_digest != ""
            assert (outcome.epistemic_state, outcome.disclosure_claim) == (
                EpistemicState.VERIFIED,
                DisclosureClaim.VERIFIED,
            )
        elif not reads_converge:
            assert REASON_READS_DISAGREE in outcome.result.failed_checks, rec["id"]

    assert verified >= 1, "producer should verify at least one real R2 problem"


def test_all_solved_records_verify():
    """Every gold 'solved' record (reader reads it, solver solves it) produces a VERIFIED
    proof — the producer's positive headline on real problems."""
    solved = [r for r in _gold() if r.get("expect") == "solved"]
    assert solved
    for rec in solved:
        outcome = verify_r2(rec["text"], gold_to_problem(rec))
        assert outcome.result.verdict is VerificationVerdict.VERIFIED, rec["id"]
        assert outcome.disclosure_claim is DisclosureClaim.VERIFIED, rec["id"]


# --- the poison: a wrong / divergent independent read ------------------------------- #

def test_divergent_independent_read_is_reads_disagree():
    records = _gold()
    readable = next(
        r for r in records if not isinstance(read_constraint_problem(r["text"]), Refusal)
    )
    primary_sig = constraint_setup_signature(read_constraint_problem(readable["text"]))
    divergent_setup = next(
        gold_to_problem(r)
        for r in records
        if constraint_setup_signature(gold_to_problem(r)) != primary_sig
    )
    outcome = verify_r2(readable["text"], divergent_setup)
    assert outcome.result.verdict is VerificationVerdict.NOT_VERIFIED
    assert REASON_READS_DISAGREE in outcome.result.failed_checks
    assert outcome.disclosure_claim is not DisclosureClaim.VERIFIED


# --- reader refusal / solver boundary ----------------------------------------------- #

def test_reader_refusal_yields_no_proof_and_a_limitation():
    outcome = verify_r2("", gold_to_problem(_gold()[0]))  # empty text → reader refuses
    assert outcome.proof is None
    assert outcome.result.verdict is VerificationVerdict.NOT_VERIFIED
    assert outcome.limitation is not None
    assert outcome.epistemic_state is not EpistemicState.VERIFIED


def test_solver_boundary_records_do_not_verify():
    refusers = [r for r in _gold() if r.get("expect") == "solver_refuses"]
    assert refusers
    for rec in refusers:
        outcome = verify_r2(rec["text"], gold_to_problem(rec))
        assert outcome.result.verdict is VerificationVerdict.NOT_VERIFIED, rec["id"]
        if outcome.proof is not None:
            # reader matched gold but solver refused → boundary fired
            assert (
                REASON_BOUNDARY_FIRED in outcome.result.failed_checks
                or REASON_READS_DISAGREE in outcome.result.failed_checks
            ), rec["id"]


# --- the contract's independence + the sanctioned route ----------------------------- #

def test_lineages_are_distinct_and_named():
    assert CONSTRAINT_READER_LINEAGE != CONSTRAINT_GOLD_AUTHOR_LINEAGE
    assert CONSTRAINT_GOLD_AUTHOR_LINEAGE == "constraint_gold_author_v1"


def test_produced_proof_uses_distinct_lineages():
    rec = _solved_record()
    outcome = verify_r2(rec["text"], gold_to_problem(rec))
    assert outcome.proof is not None
    assert outcome.proof.primary_reader_lineage != outcome.proof.independent_reader_lineage


def test_verified_state_and_claim_route_only_through_the_contract_gate():
    rec = _solved_record()
    outcome = verify_r2(rec["text"], gold_to_problem(rec))
    assert outcome.result.verdict is VerificationVerdict.VERIFIED
    assert (outcome.epistemic_state, outcome.disclosure_claim) == disclosure_for_verification(
        outcome.result
    )


def test_all_proof_digests_populated_on_verified():
    rec = _solved_record()
    outcome = verify_r2(rec["text"], gold_to_problem(rec))
    p = outcome.proof
    assert p is not None
    for digest in (
        p.source_problem_digest,
        p.primary_read_digest,
        p.independent_read_digest,
        p.derivation_digest,
        p.back_substitution_digest,
    ):
        assert digest, "every replay-critical digest must be populated on a VERIFIED proof"


# --- the gold ANSWER can never enter the proof -------------------------------------- #

def test_gold_answer_cannot_enter_the_proof():
    """Structural: the producer takes only (text, ConstraintProblem), and ConstraintProblem
    carries no answer field — so the gold answer cannot be an input to verification."""
    params = list(inspect.signature(verify_r2).parameters)
    assert params == ["text", "gold_setup"]
    assert "answer" not in ConstraintProblem.__dataclass_fields__
    assert "gold" not in ConstraintProblem.__dataclass_fields__


# --- hygiene ------------------------------------------------------------------------ #

def test_producer_is_off_serving():
    import evals.constraint_oracle.verified_producer as mod

    module_path = mod.__file__
    assert module_path is not None
    src = pathlib.Path(module_path).read_text()
    mods = [n.module or "" for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom)]
    forbidden = [m for m in mods if "generate.derivation" in m or "reliability_gate" in m]
    assert forbidden == []
