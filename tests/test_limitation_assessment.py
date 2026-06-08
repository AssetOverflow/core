"""P0-1 — exhaustive tests for the limitation-assessment consolidating view.

These prove the mapping is (a) TOTAL over the shipped failure-family registry,
(b) CONSISTENT with the registry flags, and (c) NON-VACUOUSLY correct on the
wrong=0-relevant cases: a hard boundary never becomes an answerable question, a
proposal stays a proposal, a contradiction reports, foreign text steps aside. Each
test would fail under a single mis-keyed mapping entry — none passes under a broken
impl (CLAUDE.md "Schema-Defined Proof Obligations").

Q1-B tests (added 2026-06-08) cover the typed ASK residue (``MissingSlot``,
``grounded_terms``) and the transitional carve-out (:data:`Q1B_ASK_CARVE_OUT`):
the limitation layer classifies ``missing_total_count`` / ``missing_weighted_total``
as ``ask_question`` while the shipped registry still flags them
``proposal_allowed = True`` so existing proposal consumers keep working until
Q1-C/Q1-D wires ASK delivery. The carve-out is named, enumerated, and explicit.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import get_args

import pytest

from core.comprehension_attempt.failure_family import REGISTRY, family_by_name
from core.comprehension_attempt.model import ComprehensionAttempt
from core.epistemic_disclosure.limitation import (
    Q1B_ASK_CARVE_OUT,
    LimitationKind,
    MissingSlot,
    ResolutionAction,
    _FAMILY_TO_LIMITATION,
    _FAMILY_TO_MISSING_SLOTS,
    assess_from_attempt,
    assess_from_family,
    terminal_for_action,
)
from core.epistemic_state import EpistemicState
from generate.binding_graph.model import SourceSpanLink
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

def test_proposal_allowed_iff_emit_proposal_with_q1b_ask_carveout():
    """INV-A (amended for Q1-B): the growth surfaces — and only those — propose,
    EXCEPT the Q1-B ASK carve-out (:data:`Q1B_ASK_CARVE_OUT`) which carries
    ``proposal_allowed = True`` in the REGISTRY (to keep the proposal pile populated
    until Q1-C/Q1-D wires ASK delivery) while being classified as ``ask_question`` in
    the limitation layer. Retire the carve-out once ASK is serving (then flip the
    REGISTRY flag and this test reverts to the pre-Q1B form)."""
    for family in REGISTRY:
        a = assess_from_family(family)
        if family.name in Q1B_ASK_CARVE_OUT:
            # Carve-out: registry still proposal_allowed, limitation says ask.
            assert family.proposal_allowed is True, family.name
            assert a.resolution_action == "ask_question", family.name
            assert a.limitation_kind == "missing_information", family.name
            continue
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


# --- Q1-B reclassification — disclosure layer (named, tested, never silent) ---------- #

def test_missing_total_count_limitation_is_ask_oriented():
    """Q1-B: ``missing_total_count`` is classified as ``missing_information`` /
    ``ask_question`` in the limitation layer — the user CAN state the total. This is
    the disclosure-spine's truthful classification; see
    :func:`test_registry_proposal_allowed_preserved_until_ask_delivery` for the
    transitional carve-out that keeps proposal emission alive until Q1-C/D."""
    family = family_by_name("missing_total_count")
    assert family is not None
    a = assess_from_family(family)
    assert a.limitation_kind == "missing_information"
    assert a.resolution_action == "ask_question"
    assert a.epistemic_state == EpistemicState.UNDETERMINED
    assert a.owner_organ == "r2"
    assert a.blocking_reason == "missing_total_count"


def test_missing_weighted_total_limitation_is_ask_oriented():
    """Q1-B: ``missing_weighted_total`` is classified as ``missing_information`` /
    ``ask_question`` in the limitation layer — the user CAN state the weighted
    total. Same carve-out story as ``missing_total_count``."""
    family = family_by_name("missing_weighted_total")
    assert family is not None
    a = assess_from_family(family)
    assert a.limitation_kind == "missing_information"
    assert a.resolution_action == "ask_question"
    assert a.epistemic_state == EpistemicState.UNDETERMINED
    assert a.owner_organ == "r2"
    assert a.blocking_reason == "missing_weighted_total"


def test_q1b_ask_carveout_is_explicit_and_enumerated():
    """The carve-out set is named, frozen, and contains exactly the two families
    Q1-B reclassifies — so its retirement (once ASK is serving) is a conscious,
    grep-discoverable act, not a silent re-key."""
    assert Q1B_ASK_CARVE_OUT == {"missing_total_count", "missing_weighted_total"}
    assert isinstance(Q1B_ASK_CARVE_OUT, frozenset)
    for name in Q1B_ASK_CARVE_OUT:
        assert family_by_name(name) is not None, name


# --- Q1-B carve-out — no signal loss before ASK delivery ----------------------------- #

def test_registry_proposal_allowed_preserved_until_ask_delivery():
    """The transitional carve-out's *operational* half: the shipped REGISTRY MUST
    still flag ``missing_total_count`` / ``missing_weighted_total`` as
    ``proposal_allowed = True`` so existing consumers
    (:mod:`core.comprehension_attempt.proposal`,
    :mod:`generate.contemplation.pass_manager`) keep emitting proposal-only artifacts
    to the pile. Until Q1-C/D wires ASK delivery to a served surface, flipping this
    flag would create a no-proposal/no-question dead zone (capability regression).
    Retirement: this test inverts once ASK is serving."""
    for name in Q1B_ASK_CARVE_OUT:
        family = family_by_name(name)
        assert family is not None, name
        assert family.proposal_allowed is True, (
            f"{name}: REGISTRY proposal_allowed flipped before ASK delivery — "
            f"would silently drop the proposal pile signal. See Q1B_ASK_CARVE_OUT."
        )
        assert family.must_remain_refused is False, name
        assert family.proposal_target == "r2_gold_fixture", name


def test_no_signal_loss_before_question_bus_is_serving():
    """End-to-end: the contemplation pass MUST still reach ``PROPOSAL_EMITTED`` for
    Q1-B-reclassified families until ASK delivery is wired. Proves the disclosure-
    layer reclassification did not silently drop proposal emission in the live
    contemplation pass — the no-regression guarantee made above."""
    from generate.contemplation.pass_manager import contemplate

    # The R2 fixture for the missing_total_count case is the same one
    # tests/test_r3_router_contemplation.py uses for its R3-not-blocking check.
    from evals.constraint_oracle.runner import _load_r2_gold

    fx = next(f for f in _load_r2_gold() if f["id"] == "r2-011-missing-total-count")
    result = contemplate(fx["text"])
    assert result.terminal == Terminal.PROPOSAL_EMITTED, (
        f"missing_total_count contemplation terminal={result.terminal} — Q1-B carve-out "
        f"breach: proposal emission lost before ASK delivery is wired."
    )
    assert result.family == "missing_total_count"


# --- Q1-B typed residue — MissingSlot + grounded_terms ------------------------------- #

def test_missing_slots_default_empty_for_non_ask_families():
    """Backward compatibility: ``assess_from_family`` returns empty residue (so
    existing P0-1 callers continue to work). Only :func:`assess_from_attempt` for
    an ask-mapped attempt populates residue."""
    for family in REGISTRY:
        a = assess_from_family(family)
        assert a.missing_slots == ()
        assert a.grounded_terms == ()


def test_missing_total_count_has_typed_missing_slot_residue():
    """Ask-mapped attempt for ``missing_total_count`` carries the family's typed
    slot (structural identifier — NOT renderable prose). ``grounded_terms`` is empty
    because today's :func:`classify_r2` leaves ``evidence = ()``; the wrong=0
    invariant (scoping §2) forbids fabricating renderable terms."""
    attempt = ComprehensionAttempt(
        organ="r2_constraints",
        outcome="setup_refused",
        refusal_reason="missing_total_count",
    )
    a = assess_from_attempt(attempt)
    assert a is not None
    assert a.resolution_action == "ask_question"
    assert a.missing_slots == (
        MissingSlot(
            slot_name="total_count",
            expected_unit_or_type="count_int",
            binding_target="collective_unit_total",
        ),
    )
    assert a.grounded_terms == ()


def test_missing_weighted_total_has_typed_missing_slot_residue():
    """Same shape as ``missing_total_count``, different slot."""
    attempt = ComprehensionAttempt(
        organ="r2_constraints",
        outcome="setup_refused",
        refusal_reason="missing_weighted_total",
    )
    a = assess_from_attempt(attempt)
    assert a is not None
    assert a.resolution_action == "ask_question"
    assert a.missing_slots == (
        MissingSlot(
            slot_name="weighted_total",
            expected_unit_or_type="measured_unit_int",
            binding_target="weighted_total_value",
        ),
    )
    assert a.grounded_terms == ()


def test_grounded_terms_populated_only_from_evidence_spans():
    """When the attempt carries evidence, ``grounded_terms`` reads verbatim text
    from those spans — never the family name, never the refusal reason. This is the
    grounded-rendering wrong=0 invariant in action."""
    spans = (
        SourceSpanLink(source_id="src", start=0, end=8, text="chickens"),
        SourceSpanLink(source_id="src", start=10, end=17, text="rabbits"),
    )
    attempt = ComprehensionAttempt(
        organ="r2_constraints",
        outcome="setup_refused",
        refusal_reason="missing_total_count",
        evidence=spans,
    )
    a = assess_from_attempt(attempt)
    assert a is not None
    assert a.resolution_action == "ask_question"
    assert a.grounded_terms == ("chickens", "rabbits")
    # And missing_slots is still populated from the family.
    assert len(a.missing_slots) == 1


def test_residue_empty_for_non_ask_attempts():
    """A refusal that classifies to ``refuse_known_boundary`` carries no residue
    even if it has evidence — only ask-mapped attempts get residue."""
    spans = (SourceSpanLink(source_id="src", start=0, end=5, text="dummy"),)
    attempt = ComprehensionAttempt(
        organ="r4_combined_rate",
        outcome="setup_refused",
        refusal_reason="cmb_non_positive_net_rate",
        evidence=spans,
    )
    a = assess_from_attempt(attempt)
    assert a is not None
    assert a.resolution_action == "refuse_known_boundary"
    assert a.missing_slots == ()
    assert a.grounded_terms == ()


def test_residue_never_contains_ungrounded_terms():
    """The hard wrong=0 invariant: nothing in ``grounded_terms`` may be invented
    from the family/reason. Across the registry, an attempt with no evidence yields
    no grounded terms, period."""
    for family in REGISTRY:
        if not family.refusal_reasons:
            continue
        reason = family.refusal_reasons[0]
        attempt = ComprehensionAttempt(
            organ="r2_constraints",
            outcome="setup_refused",
            refusal_reason=reason,
        )
        a = assess_from_attempt(attempt)
        if a is None:
            continue
        # Empty evidence ⇒ empty grounded_terms, full stop.
        assert a.grounded_terms == (), (family.name, reason)
        # Slot identifiers are structural — they may not appear verbatim in the
        # source text, so they never count as "grounded terms" here.
        for slot in a.missing_slots:
            assert slot.slot_name not in a.grounded_terms
            assert slot.binding_target not in a.grounded_terms


def test_missing_slot_keys_are_subset_of_ask_families():
    """``_FAMILY_TO_MISSING_SLOTS`` may only list ask-mapped families — slots are an
    ask-only artifact. Non-ask families with slots would be a category error."""
    for name in _FAMILY_TO_MISSING_SLOTS:
        family = family_by_name(name)
        assert family is not None, name
        kind, action = _FAMILY_TO_LIMITATION[name]
        assert action == "ask_question", (name, action)


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


# --- off-serving AST guard ----------------------------------------------------------- #

def test_limitation_module_is_off_serving():
    """The limitation module must import nothing from ``generate.derivation`` or
    ``core.reliability_gate`` — that is the discipline that lets the disclosure spine
    move without touching the sealed GSM8K serving metric. Enforced AST-side so a
    regression is caught at module-load time, not by metric drift."""
    forbidden = ("generate.derivation", "core.reliability_gate")
    path = (
        Path(__file__).resolve().parent.parent
        / "core" / "epistemic_disclosure" / "limitation.py"
    )
    tree = ast.parse(path.read_text())
    seen: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            seen.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            seen.append(node.module)
    for module in seen:
        for forbidden_prefix in forbidden:
            assert not (module == forbidden_prefix or module.startswith(forbidden_prefix + ".")), (
                f"off-serving breach: limitation.py imports {module!r}"
            )
