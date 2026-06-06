"""ADR-0206 — Response Governance Bridge scaffold tests.

These are the schema-defined proof obligations for the scaffold (CLAUDE.md
"Schema-Defined Proof Obligations").  Each test is written so it would
**meaningfully fail** if the property it guards were silently broken:

- ``test_govern_response_is_strict_only`` fails if the stub ever emits a
  non-STRICT policy.
- ``test_strict_is_identity`` fails if STRICT stops being byte-identical.
- ``test_seam_is_live_wiring`` fails if ``shape_surface`` stops being
  policy-sensitive — i.e. if the seam became dead code that ignores its
  policy.  This is the proof that the cognition seam is live wiring held
  strict by exactly the STRICT return, NOT dead code.
- ``test_taxonomy_partition_is_total_and_disjoint`` fails if the 9/5/1
  scoping drifts from the actual EpistemicState enum.

No test here imports ``generate.derivation.verify`` — the math-serving
chokepoint (``select_self_verified``) is untouched by this PR (ADR-0206 §5).
"""

from __future__ import annotations

import pytest

from core.epistemic_state import EpistemicState
from core.response_governance import (
    ACTIVE_STATES,
    RECONCILE_STATES,
    RESERVED_STATES,
    STRICT_POLICY,
    ReachLevel,
    ReachPolicy,
    govern_response,
    shape_surface,
)

# A small but representative cross-product of governance inputs.  None of these
# license standins is a GENUINE licensed Action.SERVE LicenseDecision, so
# govern_response must return STRICT for ALL of them — only a ratified license widens
# (Step E). The forged dict ``{"licensed": True}`` is the load-bearing standin: a
# caller's say-so must NEVER widen.
_ALL_STATES = tuple(EpistemicState)
_LICENSE_STANDINS = (None, object(), {"licensed": True}, {"licensed": False})
_STAKES_STANDINS = (None, "high", "low", 0.0, 1.0)


# --- govern_response: STRICT unless a genuine SERVE license -------------------


@pytest.mark.parametrize("state", _ALL_STATES)
@pytest.mark.parametrize("license_decision", _LICENSE_STANDINS)
@pytest.mark.parametrize("stakes", _STAKES_STANDINS)
def test_govern_response_strict_without_a_genuine_license(state, license_decision, stakes):
    """STRICT for every input that is NOT a genuine licensed SERVE decision — the
    wrong==0 load-bearing line. A None, a bare object, or a forged ``{"licensed": True}``
    dict must NOT widen: widening rests on the gate's verdict over a committed ledger,
    never on a caller's say-so.
    """
    policy = govern_response(
        epistemic_state=state, license_decision=license_decision, stakes=stakes
    )
    assert policy.level is ReachLevel.STRICT
    assert policy is STRICT_POLICY


def test_govern_response_widens_only_on_genuine_serve_license():
    """Step E (ADR-0206 §5): a REAL licensed Action.SERVE LicenseDecision widens to
    APPROXIMATE; an unlicensed one, or a PROPOSE license, stays STRICT."""
    from core.reliability_gate import Action, Ceilings, ClassTally, license_for
    from core.response_governance import APPROXIMATE_POLICY

    licensed = license_for(ClassTally("c", correct=660), Action.SERVE, Ceilings.default())
    assert licensed.licensed is True
    assert govern_response(license_decision=licensed) is APPROXIMATE_POLICY

    unlicensed = license_for(ClassTally("c", wrong=660), Action.SERVE, Ceilings.default())
    assert unlicensed.licensed is False
    assert govern_response(license_decision=unlicensed) is STRICT_POLICY

    # A PROPOSE license is NOT a SERVE license — it must not widen a served answer.
    propose = license_for(ClassTally("c", correct=660), Action.PROPOSE, Ceilings.default())
    assert propose.licensed is True and propose.action is Action.PROPOSE
    assert govern_response(license_decision=propose) is STRICT_POLICY


def test_strict_policy_admits_only_decoded():
    """STRICT's admissible set is exactly {DECODED} — fully-grounded only."""
    assert STRICT_POLICY.admissible_states == frozenset({EpistemicState.DECODED})


# --- shape_surface: STRICT identity + live wiring ---------------------------


@pytest.mark.parametrize("state", _ALL_STATES)
def test_strict_is_identity(state):
    """At STRICT, shape_surface returns the committed surface verbatim.

    This is the byte-identity guarantee that makes the cognition seam a
    no-op.  A disclosed_alternative is supplied to prove STRICT ignores it
    (it must NOT leak into the surface at STRICT).
    """
    committed = f"grounded answer for {state.value}"
    out = shape_surface(
        STRICT_POLICY,
        committed_surface=committed,
        decode_state=state,
        disclosed_alternative="A DIFFERENT, RISKIER STRING",
    )
    assert out == committed


def test_seam_is_live_wiring():
    """LIVE-WIRING PROOF (cognition path, no select_self_verified touched).

    Force the governor's decision to APPROXIMATE and show the SAME consumer
    the production path calls produces a DIFFERENT surface than at STRICT
    for the same input.  This proves shape_surface is genuinely
    policy-sensitive — the seam reads its policy and is not dead code — and
    therefore that the cognition path's strictness is held by exactly the
    STRICT return value, nothing else.
    """
    committed = "grounded answer"
    alternative = "best-effort estimate"
    decode_state = EpistemicState.UNVERIFIED_POSSIBLE  # not strict-admissible

    strict_out = shape_surface(
        STRICT_POLICY,
        committed_surface=committed,
        decode_state=decode_state,
        disclosed_alternative=alternative,
    )

    approximate_policy = ReachPolicy(
        level=ReachLevel.APPROXIMATE,
        admissible_states=frozenset({EpistemicState.DECODED}),
        rationale="test:forced-approximate",
        license_ratio=1.0,
    )
    approx_out = shape_surface(
        approximate_policy,
        committed_surface=committed,
        decode_state=decode_state,
        disclosed_alternative=alternative,
    )

    # The consumer read the policy: STRICT committed verbatim; APPROXIMATE
    # surfaced the disclosed alternative with an epistemic prefix.
    assert strict_out == committed
    assert approx_out != strict_out
    assert alternative in approx_out
    assert approx_out.startswith("[approximate]")


def test_widening_admissible_state_commits_without_disclosure():
    """A widening level commits an admissible decode-state without a prefix.

    Guards the branch that distinguishes "admissible at this level" (commit
    the alternative as-is) from "inadmissible" (disclose).  Keeps the
    future-pathway logic honest and exercised.
    """
    widening = ReachPolicy(
        level=ReachLevel.APPROXIMATE,
        admissible_states=frozenset({EpistemicState.EVIDENCED_INCOMPLETE}),
        rationale="test:admissible",
    )
    out = shape_surface(
        widening,
        committed_surface="committed",
        decode_state=EpistemicState.EVIDENCED_INCOMPLETE,
        disclosed_alternative="alt",
    )
    assert out == "alt"  # admitted: no disclosure prefix


# --- Taxonomy scoping (ADR-0206 §4) -----------------------------------------


def test_taxonomy_partition_is_total_and_disjoint():
    """The 9/5/1 partition covers every EpistemicState exactly once.

    If a state is added to the enum without being placed in the governing
    loop's partition, this fails — keeping the "honestly scoped, not
    half-dead" contract enforced rather than asserted.
    """
    assert len(ACTIVE_STATES) == 9
    assert len(RESERVED_STATES) == 5
    assert len(RECONCILE_STATES) == 1

    union = ACTIVE_STATES | RESERVED_STATES | RECONCILE_STATES
    assert union == set(EpistemicState)

    # Pairwise disjoint — no state wears two roles.
    assert not (ACTIVE_STATES & RESERVED_STATES)
    assert not (ACTIVE_STATES & RECONCILE_STATES)
    assert not (RESERVED_STATES & RECONCILE_STATES)


def test_evidenced_is_the_reconcile_state():
    """EVIDENCED is the orphaned drift (recognition owns its own copy)."""
    assert RECONCILE_STATES == frozenset({EpistemicState.EVIDENCED})
