"""ADR-0206 §2-§3 — the reach policy and its STRICT-only scaffold.

A :class:`ReachPolicy` is the per-response decision about *how far into
uncertainty a response may reach* — the thing CORE today does not compute.
The full bridge will derive it from the decode-state of the grounding and
the reliability gate's license (ADR-0206 §1).  This module ships only the
**STRICT** end of that spectrum, wired so the seam is live but inert.

Two functions form the seam:

``govern_response``
    The decision point.  Scaffold: returns :data:`STRICT_POLICY` for every
    input.  This is the single return value the ``wrong == 0`` guarantee
    rests on — mutate it and the live-wiring tests diverge loudly.

``shape_surface``
    The consumer.  At :attr:`ReachLevel.STRICT` it is the IDENTITY
    transform (returns the committed surface verbatim).  The higher reach
    levels are the future widening pathway; they are *unreachable in
    production today* because ``govern_response`` never emits them, but
    they are real, policy-sensitive code so the seam is not dead.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique

from core.epistemic_state import EpistemicState


@unique
class ReachLevel(Enum):
    """How far a governed response may reach beyond fully-grounded fact.

    Ordered conceptually STRICT < APPROXIMATE < EXTRAPOLATE < CREATIVE.
    Only STRICT is emitted by the scaffold; the rest name the spectrum the
    bridge will earn the right to enter via the reliability gate.
    """

    STRICT = "strict"  # commit only fully-grounded; else refuse/disclose (TODAY)
    APPROXIMATE = "approximate"  # disclosed best-estimate from incomplete evidence
    EXTRAPOLATE = "extrapolate"  # disclosed inference past the evidence
    CREATIVE = "creative"  # disclosed imaginative / novel construction


@dataclass(frozen=True, slots=True)
class ReachPolicy:
    """The per-response governance decision.

    ``admissible_states`` is the set of decode-states whose surface may be
    *committed as-is* at this level; states outside it are either refused
    (STRICT) or surfaced as a disclosed alternative (higher levels).
    ``rationale`` and ``license_ratio`` keep the decision inspectable —
    the same discipline the reliability gate uses for ``LicenseDecision``.
    """

    level: ReachLevel
    admissible_states: frozenset[EpistemicState]
    rationale: str
    license_ratio: float = 0.0


# --- Taxonomy scoping (ADR-0206 §4) -----------------------------------------
# The 15 declared EpistemicState members, partitioned by their role in the
# governing loop.  This is the "honestly scoped, not half-dead" contract:
# every state is either ACTIVE (produced today AND consumed by the loop),
# RESERVED (named here, not yet produced, each tied to a capability that
# must land first), or RECONCILE (a real drift, fixed in its own PR).
#
# Verified against the source tree on the ADR-0206 branch: exactly 9 states
# are ever produced (DECODED ×6, UNDETERMINED ×3, EPISTEMIC_STATE_NEEDED ×3,
# UNVERIFIED_POSSIBLE/UNVERIFIED_NOVEL/CONTRADICTED/AMBIGUOUS ×2,
# EVIDENCED_INCOMPLETE/INFERRED ×1) and 6 are never produced.  Of those 6,
# five are RESERVED and one (EVIDENCED) is RECONCILE.

ACTIVE_STATES: frozenset[EpistemicState] = frozenset(
    {
        EpistemicState.DECODED,  # fully grounded — strict-admissible
        EpistemicState.EVIDENCED_INCOMPLETE,  # partial grounding — approximate+
        EpistemicState.INFERRED,  # derived — extrapolate+
        EpistemicState.UNVERIFIED_POSSIBLE,  # possibility — extrapolate+ (disclosed)
        EpistemicState.UNVERIFIED_NOVEL,  # OOV — creative only (disclosed)
        EpistemicState.CONTRADICTED,  # never committed — force refuse
        EpistemicState.AMBIGUOUS,  # never committed — force refuse/clarify
        EpistemicState.UNDETERMINED,  # never committed — refuse
        EpistemicState.EPISTEMIC_STATE_NEEDED,  # sentinel — force situate step
    }
)

# Never produced today; each unlocks only when its named capability lands.
RESERVED_STATES: frozenset[EpistemicState] = frozenset(
    {
        EpistemicState.VERIFIED,  # needs canonical-comparison pass (soundness != correctness);
        #                           the ONLY state that will license widening past gold.
        EpistemicState.COMPUTATIONALLY_BOUNDED,  # search-budget exhausted; search.py is the near-term emitter.
        EpistemicState.SCOPE_BOUNDARY,  # out-of-domain refusal; needs domain-scope detection.
        EpistemicState.PERCEIVED,  # raw ingest pre-comprehension; needs a perception lane.
        EpistemicState.DECODED_UNARTICULATED,  # decoded but no realizer surface; articulation-gap case.
    }
)

# Declared here but never produced, while recognition/outcome.py defines its
# OWN "evidenced" constant.  Real drift — reconciled in a dedicated PR
# (ADR-0206 §5), kept OUT of this purely-additive scaffold.
RECONCILE_STATES: frozenset[EpistemicState] = frozenset({EpistemicState.EVIDENCED})


# --- The scaffold's single governing decision -------------------------------

# STRICT admits only the fully-grounded decode-state; everything else is
# refused/disclosed by the existing response path.  This is informational
# at STRICT (shape_surface short-circuits to identity) but records the
# contract the bridge will enforce once widening is built.
_STRICT_ADMISSIBLE: frozenset[EpistemicState] = frozenset({EpistemicState.DECODED})

STRICT_POLICY: ReachPolicy = ReachPolicy(
    level=ReachLevel.STRICT,
    admissible_states=_STRICT_ADMISSIBLE,
    rationale="scaffold:strict-only (ADR-0206 §3 — risk-reward widening not yet built)",
    license_ratio=0.0,
)

# Step E (ADR-0206 §5) — the first widening rung. APPROXIMATE keeps the SAME admissible
# set as STRICT ({DECODED}): a fully-grounded surface commits verbatim, but anything less
# grounded (a converse GUESS is ``UNVERIFIED_POSSIBLE``) is surfaced by ``shape_surface``
# as a DISCLOSED ``[approximate]`` alternative. So a licensed estimate is never committed
# silently — admitting its state here would defeat the disclosure the rung exists for.
APPROXIMATE_POLICY: ReachPolicy = ReachPolicy(
    level=ReachLevel.APPROXIMATE,
    admissible_states=_STRICT_ADMISSIBLE,
    rationale="license-gated widening (ADR-0206 §5 / Step E — SERVE earned on a committed ClassTally)",
    license_ratio=1.0,
)

# Disclosure prefixes for the widening levels.  Real
# code so the higher-level branch of shape_surface is genuinely
# policy-sensitive, exercised by the live-wiring test.
_DISCLOSURE_PREFIX: dict[ReachLevel, str] = {
    ReachLevel.APPROXIMATE: "[approximate]",
    ReachLevel.EXTRAPOLATE: "[extrapolated]",
    ReachLevel.CREATIVE: "[exploratory]",
}


def _serve_licensed(license_decision: object | None) -> bool:
    """True iff ``license_decision`` is a GENUINE, licensed ``Action.SERVE`` decision.

    Strict by type on purpose: only a real :class:`~core.reliability_gate.LicenseDecision`
    that the gate marked ``licensed`` for ``Action.SERVE`` widens. A ``None``, a bare
    object, or a forged dict (``{"licensed": True}``) is NOT a ratified license and stays
    STRICT — the wrong=0 guard is that widening rests on the gate's verdict over a
    committed ledger, never on a caller's say-so.
    """
    from core.reliability_gate import Action
    from core.reliability_gate.gate import LicenseDecision

    return (
        isinstance(license_decision, LicenseDecision)
        and license_decision.action is Action.SERVE
        and license_decision.licensed
    )


def govern_response(
    *,
    epistemic_state: EpistemicState | None = None,
    license_decision: object | None = None,
    stakes: object | None = None,
) -> ReachPolicy:
    """Decide the reach policy for a response.

    Step E (ADR-0206 §5) — the first license-gated widening. Returns
    :data:`APPROXIMATE_POLICY` IFF ``license_decision`` is a genuine licensed
    ``Action.SERVE`` decision (a predicate-class that earned SERVE on the committed
    reliability ledger); otherwise :data:`STRICT_POLICY`. Every current serving call
    site passes no ``license_decision`` → STRICT → byte-identical to the pre-E path.

    The STRICT default remains the load-bearing line for ``wrong == 0``: nothing
    widens without a ratified license, and even APPROXIMATE only ever surfaces a
    DISCLOSED estimate (``shape_surface`` adds ``[approximate]``), never a silent
    commit. ``stakes``-weighing (SITUATE) stays designed-not-built (ADR-0206 §1).
    """
    if _serve_licensed(license_decision):
        return APPROXIMATE_POLICY
    return STRICT_POLICY


def shape_surface(
    policy: ReachPolicy,
    *,
    committed_surface: str,
    decode_state: EpistemicState,
    disclosed_alternative: str | None = None,
) -> str:
    """Apply ``policy`` to a committed surface — the response-path consumer.

    At :attr:`ReachLevel.STRICT` (the only level :func:`govern_response`
    emits today) this is the IDENTITY transform: the committed surface is
    returned verbatim, byte-identical to the pre-bridge path.  This is why
    wiring the seam into :mod:`chat.runtime` changes no behavior.

    The higher reach levels are the future widening pathway.  They are
    real and policy-sensitive — a non-admissible decode-state is surfaced
    as a *disclosed alternative* rather than committed silently — so the
    seam is live wiring, not dead code.  They are unreachable in production
    today only because ``govern_response`` never emits them.
    """
    if policy.level is ReachLevel.STRICT:
        return committed_surface

    # --- Future widening pathway (unreachable in production today) ---
    alternative = (
        committed_surface if disclosed_alternative is None else disclosed_alternative
    )
    if decode_state in policy.admissible_states:
        return alternative
    prefix = _DISCLOSURE_PREFIX.get(policy.level, "")
    return f"{prefix} {alternative}".strip() if prefix else alternative
