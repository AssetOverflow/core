"""P0-3 — tests for the ServedDisposition mapping scaffold.

Mapping-only: no rendering, no bus, no serving. Tests assert the load-bearing rules,
the Phase-1 VERIFIED guard (a verified claim never discloses without the verified
state), limitation-dominates-claim, the explicit scope_boundary -> EXPLAIN choice,
and totality over both axes.
"""

from __future__ import annotations

import ast
import pathlib
from enum import Enum

import pytest

import core.epistemic_disclosure.disposition as disposition_module
from core.comprehension_attempt.failure_family import REGISTRY, family_by_name
from core.epistemic_disclosure.disclosure_claim import DisclosureClaim
from core.epistemic_disclosure.disposition import (
    ServedDisposition,
    choose_served_disposition,
)
from core.epistemic_disclosure.limitation import LimitationAssessment, assess_from_family
from core.epistemic_state import EpistemicState


def _disp_for_family(name, *, state=EpistemicState.UNDETERMINED, claim=DisclosureClaim.NONE):
    family = family_by_name(name)
    assert family is not None, name
    return choose_served_disposition(
        epistemic_state=state, limitation=assess_from_family(family), disclosure_claim=claim
    )


# --- serve branch (no blocking limitation) ----------------------------------------- #

def test_no_limitation_none_claim_commits():
    assert (
        choose_served_disposition(
            epistemic_state=EpistemicState.DECODED,
            limitation=None,
            disclosure_claim=DisclosureClaim.NONE,
        )
        is ServedDisposition.COMMIT
    )


def test_verified_state_and_claim_discloses():
    assert (
        choose_served_disposition(
            epistemic_state=EpistemicState.VERIFIED,
            limitation=None,
            disclosure_claim=DisclosureClaim.VERIFIED,
        )
        is ServedDisposition.DISCLOSE
    )


@pytest.mark.parametrize(
    "state", [s for s in EpistemicState if s is not EpistemicState.VERIFIED]
)
def test_verified_claim_without_verified_state_never_discloses(state):
    """THE Phase-1 guard: a verified claim must not produce DISCLOSE unless the state
    is actually VERIFIED — protects the lane from 'verified-looking' serving before the
    producer exists."""
    disp = choose_served_disposition(
        epistemic_state=state, limitation=None, disclosure_claim=DisclosureClaim.VERIFIED
    )
    assert disp is not ServedDisposition.DISCLOSE
    assert disp is ServedDisposition.COMMIT


def test_approximate_claim_discloses():
    assert (
        choose_served_disposition(
            epistemic_state=EpistemicState.EVIDENCED_INCOMPLETE,
            limitation=None,
            disclosure_claim=DisclosureClaim.APPROXIMATE,
        )
        is ServedDisposition.DISCLOSE
    )


def test_proposal_only_claim_proposes():
    assert (
        choose_served_disposition(
            epistemic_state=EpistemicState.UNDETERMINED,
            limitation=None,
            disclosure_claim=DisclosureClaim.PROPOSAL_ONLY,
        )
        is ServedDisposition.PROPOSE
    )


# --- limitation-driven dispositions (via real P0-1 assessments) -------------------- #

def test_ask_question_limitation_asks():
    assert _disp_for_family("cmb_underdetermined") is ServedDisposition.ASK


def test_emit_proposal_limitation_proposes():
    assert _disp_for_family("cmb_unsupported_reciprocal") is ServedDisposition.PROPOSE


def test_report_contradiction_limitation_reports():
    assert _disp_for_family("answer_key_contradiction") is ServedDisposition.REPORT


def test_step_aside_limitation_steps_aside():
    assert _disp_for_family("input_shape") is ServedDisposition.STEP_ASIDE


def test_hard_boundary_limitation_refuses():
    assert _disp_for_family("cmb_non_positive_net") is ServedDisposition.REFUSE


def test_scope_boundary_limitation_explains_not_refuses():
    """The explicit P0-3 choice: scope is EXPLAIN, not a hard REFUSE."""
    disp = _disp_for_family("unsupported_system_size")
    assert disp is ServedDisposition.EXPLAIN
    assert disp is not ServedDisposition.REFUSE


def test_limitation_dominates_disclosure_claim():
    """Even a fully-backed verified claim cannot serve an answer when a limitation blocks."""
    family = family_by_name("cmb_underdetermined")
    assert family is not None
    disp = choose_served_disposition(
        epistemic_state=EpistemicState.VERIFIED,
        limitation=assess_from_family(family),
        disclosure_claim=DisclosureClaim.VERIFIED,
    )
    assert disp is ServedDisposition.ASK


def test_answer_action_falls_through_to_serve():
    """A non-blocking limitation (resolution_action == 'answer') yields the serve decision."""
    la = LimitationAssessment(
        limitation_kind="missing_information",
        resolution_action="answer",
        epistemic_state=EpistemicState.UNDETERMINED,
        owner_organ="r2",
        blocking_reason="synthetic",
    )
    assert (
        choose_served_disposition(
            epistemic_state=EpistemicState.DECODED,
            limitation=la,
            disclosure_claim=DisclosureClaim.NONE,
        )
        is ServedDisposition.COMMIT
    )


# --- totality over both axes ------------------------------------------------------- #

def test_every_family_maps_to_a_disposition():
    for family in REGISTRY:
        disp = choose_served_disposition(
            epistemic_state=EpistemicState.UNDETERMINED, limitation=assess_from_family(family)
        )
        assert isinstance(disp, ServedDisposition), family.name


def test_every_disclosure_claim_serves_to_a_disposition():
    for claim in DisclosureClaim:
        disp = choose_served_disposition(
            epistemic_state=EpistemicState.VERIFIED, limitation=None, disclosure_claim=claim
        )
        assert isinstance(disp, ServedDisposition), claim


# --- hygiene ----------------------------------------------------------------------- #

def test_is_str_enum():
    assert issubclass(ServedDisposition, str)
    assert issubclass(ServedDisposition, Enum)


def test_module_is_off_serving():
    module_path = disposition_module.__file__
    assert module_path is not None
    src = pathlib.Path(module_path).read_text()
    mods = [n.module or "" for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom)]
    forbidden = [
        m for m in mods if "generate.derivation" in m or "reliability_gate" in m or m.endswith("verify")
    ]
    assert forbidden == []
