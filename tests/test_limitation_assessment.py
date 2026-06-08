"""P0-1 — exhaustive tests for the limitation-assessment consolidating view.

These prove the mapping is (a) TOTAL over the shipped failure-family registry,
(b) CONSISTENT with the registry flags, and (c) NON-VACUOUSLY correct on the
wrong=0-relevant cases: a hard boundary never becomes an answerable question, a
proposal stays a proposal, a contradiction reports, foreign text steps aside. Each
test would fail under a single mis-keyed mapping entry — none passes under a broken
impl (CLAUDE.md "Schema-Defined Proof Obligations").
"""

from __future__ import annotations

from typing import get_args

import pytest

from core.comprehension_attempt.failure_family import REGISTRY, family_by_name
from core.comprehension_attempt.model import ComprehensionAttempt
from core.epistemic_disclosure.limitation import (
    PENDING_Q1B_RECLASSIFICATION,
    LimitationKind,
    ResolutionAction,
    _FAMILY_TO_LIMITATION,
    assess_from_attempt,
    assess_from_family,
    terminal_for_action,
)
from core.epistemic_state import EpistemicState
from generate.contemplation.findings import Terminal

VALID_KINDS = frozenset(get_args(LimitationKind))
VALID_ACTIONS = frozenset(get_args(ResolutionAction))
REGISTRY_NAMES = frozenset(f.name for f in REGISTRY)


# --- totality + type validity -------------------------------------------------------- #

def test_mapping_is_total_over_registry():
    """Exactly the shipped families — no extra keys, no missing ones."""
    assert set(_FAMILY_TO_LIMITATION) == set(REGISTRY_NAMES)


def test_assess_from_family_produces_valid_typed_values():
    for family in REGISTRY:
        a = assess_from_family(family)
        assert a.limitation_kind in VALID_KINDS, family.name
        assert a.resolution_action in VALID_ACTIONS, family.name
        assert a.blocking_reason == family.name
        assert a.owner_organ == family.owner


# --- flag-consistency invariants ----------------------------------------------------- #

def test_proposal_allowed_iff_emit_proposal():
    """INV-A: the growth surfaces — and only those — propose."""
    for family in REGISTRY:
        a = assess_from_family(family)
        assert family.proposal_allowed == (a.resolution_action == "emit_proposal"), family.name


def test_emit_proposal_implies_capability_gap():
    for family in REGISTRY:
        a = assess_from_family(family)
        if a.resolution_action == "emit_proposal":
            assert a.limitation_kind == "capability_gap", family.name


def test_report_contradiction_iff_answer_key_contradiction():
    """INV-B: the answer-key verdict is the sole reporter."""
    reporters = [f.name for f in REGISTRY if assess_from_family(f).resolution_action == "report_contradiction"]
    assert reporters == ["answer_key_contradiction"]


def test_step_aside_iff_input_shape():
    """INV-C: only foreign-shape text steps aside."""
    for family in REGISTRY:
        a = assess_from_family(family)
        is_input_shape = family.name == "input_shape"
        assert (a.resolution_action == "step_aside") == is_input_shape, family.name
        if is_input_shape:
            assert a.limitation_kind == "input_shape"


def test_hard_boundary_never_asks():
    """INV-E (wrong=0-relevant): an impossible problem is never turned into a question."""
    for family in REGISTRY:
        a = assess_from_family(family)
        if a.limitation_kind == "hard_boundary":
            assert a.resolution_action == "refuse_known_boundary", family.name


def test_ask_question_only_for_resolvable_kinds():
    """INV-D: asking is licensed only for kinds a user answer could resolve."""
    askable = {"missing_information", "ambiguous_structure", "renderability_gap"}
    for family in REGISTRY:
        a = assess_from_family(family)
        if a.resolution_action == "ask_question":
            assert a.limitation_kind in askable, family.name


# --- non-vacuous, load-bearing specific mappings ------------------------------------- #

@pytest.mark.parametrize(
    "name,kind,action",
    [
        ("cmb_non_positive_net", "hard_boundary", "refuse_known_boundary"),
        ("cmb_non_integer", "hard_boundary", "refuse_known_boundary"),
        ("cmb_underdetermined", "missing_information", "ask_question"),
        ("cmb_combine_ambiguous", "ambiguous_structure", "ask_question"),
        ("rate_underdetermined", "missing_information", "ask_question"),
        ("answer_key_contradiction", "contradiction", "report_contradiction"),
        ("input_shape", "input_shape", "step_aside"),
        ("cmb_unsupported_reciprocal", "capability_gap", "emit_proposal"),
        ("unsupported_system_size", "scope_boundary", "refuse_known_boundary"),
        ("admissibility_incompatible", "hard_boundary", "refuse_known_boundary"),
    ],
)
def test_specific_load_bearing_mappings(name, kind, action):
    family = family_by_name(name)
    assert family is not None, name
    a = assess_from_family(family)
    assert (a.limitation_kind, a.resolution_action) == (kind, action)


def test_pending_reclassification_is_currently_capability_gap():
    """Documents the DEFERRED Q1-B change. Today these propose; Q1-B will flip them to
    missing_information/ask. When that lands this test changes deliberately — it is the
    tripwire proving the reclassification was a conscious, tested act, not a silent re-key."""
    for name in PENDING_Q1B_RECLASSIFICATION:
        family = family_by_name(name)
        assert family is not None, name
        a = assess_from_family(family)
        assert (a.limitation_kind, a.resolution_action) == ("capability_gap", "emit_proposal"), name
    assert PENDING_Q1B_RECLASSIFICATION == {"missing_total_count", "missing_weighted_total"}


# --- the epistemic-state axis -------------------------------------------------------- #

def test_epistemic_state_axis():
    by_name = {f.name: assess_from_family(f) for f in REGISTRY}
    assert by_name["unsupported_system_size"].epistemic_state == EpistemicState.SCOPE_BOUNDARY
    assert by_name["answer_key_contradiction"].epistemic_state == EpistemicState.CONTRADICTED
    assert by_name["cmb_combine_ambiguous"].epistemic_state == EpistemicState.AMBIGUOUS
    assert by_name["cmb_underdetermined"].epistemic_state == EpistemicState.UNDETERMINED


# --- the consolidation proof: actions live on shipped terminals (except ask) --------- #

def test_actions_consolidate_onto_terminals_except_ask():
    """The proof of 'consolidating view, not a fourth taxonomy': every action maps to a
    shipped Terminal except ask_question (the one genuinely new action / Q1 tenant)."""
    for action in VALID_ACTIONS:
        terminal = terminal_for_action(action)
        if action == "ask_question":
            assert terminal is None
        else:
            assert isinstance(terminal, Terminal), action


def test_only_ask_question_is_new():
    new_actions = sorted(a for a in VALID_ACTIONS if terminal_for_action(a) is None)
    assert new_actions == ["ask_question"]


# --- attempt-level classification ---------------------------------------------------- #

def test_assess_attempt_refusal_underdetermined_asks():
    attempt = ComprehensionAttempt(
        organ="r4_combined_rate",
        outcome="setup_refused",
        refusal_reason="cmb_missing_second_rate",
    )
    a = assess_from_attempt(attempt)
    assert a is not None
    assert (a.limitation_kind, a.resolution_action) == ("missing_information", "ask_question")


def test_assess_attempt_hard_boundary_refuses_not_asks():
    attempt = ComprehensionAttempt(
        organ="r4_combined_rate",
        outcome="setup_refused",
        refusal_reason="cmb_non_positive_net_rate",
    )
    a = assess_from_attempt(attempt)
    assert a is not None
    assert a.resolution_action == "refuse_known_boundary"


def test_assess_attempt_contradiction_reports():
    attempt = ComprehensionAttempt(organ="r2_constraints", outcome="contradiction")
    a = assess_from_attempt(attempt)
    assert a is not None
    assert (a.limitation_kind, a.resolution_action) == ("contradiction", "report_contradiction")
    assert a.epistemic_state == EpistemicState.CONTRADICTED


def test_assess_attempt_solved_is_not_a_limitation():
    attempt = ComprehensionAttempt(organ="r1_quantitative", outcome="setup_correct")
    assert assess_from_attempt(attempt) is None


def test_assess_attempt_unclassified_reason_refuses_never_asks():
    """wrong=0-safe default: an unknown refusal reason refuses, never becomes a question."""
    attempt = ComprehensionAttempt(
        organ="r2_constraints",
        outcome="setup_refused",
        refusal_reason="some_unmapped_future_reason",
    )
    a = assess_from_attempt(attempt)
    assert a is not None
    assert a.resolution_action == "refuse_known_boundary"
    assert a.resolution_action != "ask_question"
