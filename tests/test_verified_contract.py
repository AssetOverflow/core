"""P1-A — tests for the VERIFIED contract.

The central, non-negotiable test is :func:`test_verified_contract_rejects_faithful_solve_of_wrong_read`:
a wrong semantic read that is arithmetically faithfully solved (back-substitutes,
boundary-clear) must NOT verify, because an independent read disagrees. Every other
test pins one obligation. The contract is contract-only — no producer, no serving.
"""

from __future__ import annotations

import ast
import pathlib
from dataclasses import replace

from core.epistemic_disclosure.disclosure_claim import DisclosureClaim
from core.epistemic_disclosure.disposition import (
    ServedDisposition,
    choose_served_disposition,
)
from core.epistemic_disclosure.limitation import LimitationAssessment
from core.epistemic_disclosure.verified_contract import (
    REASON_BOUNDARY_FIRED,
    REASON_CONTRADICTION_PRESENT,
    REASON_INCOMPLETE_PROOF,
    REASON_NO_BACK_SUBSTITUTION,
    REASON_READS_DISAGREE,
    REASON_READS_NOT_INDEPENDENT,
    REASON_UNRESOLVED_LIMITATION,
    VERIFICATION_OBLIGATION,
    VerificationProof,
    VerificationVerdict,
    disclosure_for_verification,
    evaluate_verification,
)
from core.epistemic_state import EpistemicState


def _valid_proof(**overrides) -> VerificationProof:
    """A proof that survives the full contract: two independent reads converging on one
    canonical structure, a faithful derivation that back-substitutes, no boundary, no
    contradiction. Override one field to construct each poison case."""
    base = dict(
        source_problem_digest="prob#1",
        primary_reader_lineage="reader_primary",
        independent_reader_lineage="reader_independent",
        primary_read_digest="canonical_structure_C",
        independent_read_digest="canonical_structure_C",
        derivation_digest="deriv#1",
        back_substitution_digest="backsub#1",
        boundary_clear=True,
        contradiction_clear=True,
    )
    base.update(overrides)
    return VerificationProof(**base)


# --- the positive case: the ONLY route to VERIFIED --------------------------------- #

def test_fully_valid_proof_verifies():
    result = evaluate_verification(_valid_proof(), limitation=None)
    assert result.verdict is VerificationVerdict.VERIFIED
    assert result.failed_checks == ()


# --- THE central hazard ------------------------------------------------------------ #

def test_verified_contract_rejects_faithful_solve_of_wrong_read():
    """A WRONG primary read, an arithmetically faithful solve over it (back-substitutes
    into the wrong structure, no boundary fires) — but the INDEPENDENT read sees the
    correct structure and disagrees. Must NOT verify. This is the gate that stops P1-B
    from degenerating into a 'second solver agrees' rubber stamp."""
    poison = _valid_proof(
        primary_read_digest="structure_from_WRONG_read",
        independent_read_digest="structure_from_CORRECT_read",  # the reads disagree
    )
    result = evaluate_verification(poison, limitation=None)
    assert result.verdict is VerificationVerdict.NOT_VERIFIED
    assert REASON_READS_DISAGREE in result.failed_checks


def test_verified_requires_independent_read_not_same_read_twice():
    same_read_twice = _valid_proof(
        primary_reader_lineage="reader_X",
        independent_reader_lineage="reader_X",  # same lineage → not independent
    )
    result = evaluate_verification(same_read_twice, limitation=None)
    assert result.verdict is VerificationVerdict.NOT_VERIFIED
    assert REASON_READS_NOT_INDEPENDENT in result.failed_checks


# --- each remaining obligation ----------------------------------------------------- #

def test_verified_requires_back_substitution():
    result = evaluate_verification(_valid_proof(back_substitution_digest=""), limitation=None)
    assert result.verdict is VerificationVerdict.NOT_VERIFIED
    assert REASON_NO_BACK_SUBSTITUTION in result.failed_checks


def test_verified_requires_boundary_clear():
    result = evaluate_verification(_valid_proof(boundary_clear=False), limitation=None)
    assert result.verdict is VerificationVerdict.NOT_VERIFIED
    assert REASON_BOUNDARY_FIRED in result.failed_checks


def test_contradiction_blocks_verification():
    result = evaluate_verification(_valid_proof(contradiction_clear=False), limitation=None)
    assert result.verdict is VerificationVerdict.NOT_VERIFIED
    assert REASON_CONTRADICTION_PRESENT in result.failed_checks


def test_incomplete_proof_digest_blocks_verification():
    for field in ("source_problem_digest", "derivation_digest"):
        result = evaluate_verification(_valid_proof(**{field: ""}), limitation=None)
        assert result.verdict is VerificationVerdict.NOT_VERIFIED, field
        assert REASON_INCOMPLETE_PROOF in result.failed_checks, field


def test_verified_rejects_any_limitation_assessment():
    blocking = LimitationAssessment(
        limitation_kind="missing_information",
        resolution_action="ask_question",
        epistemic_state=EpistemicState.UNDETERMINED,
        owner_organ="r2",
        blocking_reason="cmb_underdetermined",
    )
    result = evaluate_verification(_valid_proof(), limitation=blocking)
    assert result.verdict is VerificationVerdict.NOT_VERIFIED
    assert REASON_UNRESOLVED_LIMITATION in result.failed_checks


# --- the obligations are LOAD-BEARING (schema-obligation discipline) ---------------- #

def test_canonical_obligation_is_fully_strict():
    assert VERIFICATION_OBLIGATION.requires_independent_read
    assert VERIFICATION_OBLIGATION.rejects_wrong_read_even_if_solved
    assert VERIFICATION_OBLIGATION.requires_back_substitution
    assert VERIFICATION_OBLIGATION.requires_boundary_clear


def test_relaxing_wrong_read_obligation_would_admit_the_poison():
    """Proves ``rejects_wrong_read_even_if_solved`` is load-bearing, not decoration: the
    canonical obligation catches the poison; relaxing exactly that one flag stops the
    check from firing (CLAUDE.md: a test must fail under the violation it guards)."""
    poison = _valid_proof(independent_read_digest="different_structure")
    canonical = evaluate_verification(poison, limitation=None)
    assert canonical.verdict is VerificationVerdict.NOT_VERIFIED
    assert REASON_READS_DISAGREE in canonical.failed_checks

    relaxed = replace(VERIFICATION_OBLIGATION, rejects_wrong_read_even_if_solved=False)
    relaxed_result = evaluate_verification(poison, limitation=None, obligation=relaxed)
    assert REASON_READS_DISAGREE not in relaxed_result.failed_checks


# --- the sanctioned route to the verified state/claim ------------------------------ #

def test_verified_claim_requires_epistemic_state_verified():
    verified = evaluate_verification(_valid_proof(), limitation=None)
    state, claim = disclosure_for_verification(verified)
    assert state is EpistemicState.VERIFIED
    assert claim is DisclosureClaim.VERIFIED


def test_not_verified_routes_to_safe_defaults():
    poison = evaluate_verification(_valid_proof(independent_read_digest="diff"), limitation=None)
    state, claim = disclosure_for_verification(poison)
    assert state is not EpistemicState.VERIFIED
    assert claim is not DisclosureClaim.VERIFIED
    assert (state, claim) == (EpistemicState.UNDETERMINED, DisclosureClaim.NONE)


# --- composition with the Phase-0 bus (the whole chain) ---------------------------- #

def test_verified_proof_routes_through_bus_to_disclose():
    """proof → contract → (VERIFIED state, VERIFIED claim) → P0-3 disposition = DISCLOSE."""
    result = evaluate_verification(_valid_proof(), limitation=None)
    state, claim = disclosure_for_verification(result)
    disp = choose_served_disposition(epistemic_state=state, limitation=None, disclosure_claim=claim)
    assert disp is ServedDisposition.DISCLOSE


def test_unverified_proof_never_discloses_through_bus():
    result = evaluate_verification(_valid_proof(independent_read_digest="diff"), limitation=None)
    state, claim = disclosure_for_verification(result)
    disp = choose_served_disposition(epistemic_state=state, limitation=None, disclosure_claim=claim)
    assert disp is not ServedDisposition.DISCLOSE
    assert disp is ServedDisposition.COMMIT


# --- hygiene ----------------------------------------------------------------------- #

def test_verified_contract_does_not_import_serving_or_verify():
    import core.epistemic_disclosure.verified_contract as mod

    module_path = mod.__file__
    assert module_path is not None
    src = pathlib.Path(module_path).read_text()
    mods = [n.module or "" for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom)]
    forbidden = [
        m for m in mods if "generate.derivation" in m or "reliability_gate" in m or m.endswith("verify")
    ]
    assert forbidden == []
