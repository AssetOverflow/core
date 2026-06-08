"""P0-3 — ServedDisposition: the served-surface decision (mapping scaffold only).

The third axis of the Epistemic Disclosure bus. Given (a) the epistemic state, (b)
the limitation assessment (if resolution is blocked), and (c) the disclosure claim,
:func:`choose_served_disposition` decides WHAT KIND OF MOVE the served surface makes:
commit / disclose / ask / propose / report / explain / refuse / step-aside.

This is a PURE MAPPING. No rendering, no bus behaviour, no ``verify.py``, no
``govern_response`` mutation — nothing consumes the result yet. P0-3 only fixes the
decision table so a later slice / Phase 1 can wire it.

The load-bearing rule (the Phase-1 guard): a ``DisclosureClaim.VERIFIED`` discloses
ONLY when the epistemic state is actually ``EpistemicState.VERIFIED``. An unbacked
verified claim degrades to a plain ``COMMIT`` — it is NEVER served as verified before
the producer exists. This protects the whole VERIFIED lane from accidental
"verified-looking" serving.

Off-serving: imports no ``generate.derivation`` / ``core.reliability_gate``.
"""

from __future__ import annotations

from enum import Enum, unique

from core.epistemic_disclosure.disclosure_claim import DisclosureClaim
from core.epistemic_disclosure.limitation import LimitationAssessment
from core.epistemic_state import EpistemicState


@unique
class ServedDisposition(str, Enum):
    """What kind of move the served surface makes.

    ``str``-valued for stable serialization (the ``EpistemicState`` /
    ``DisclosureClaim`` convention).
    """

    COMMIT = "commit"  # serve a fully-grounded answer as-is, no epistemic caveat
    DISCLOSE = "disclose"  # serve under a disclosure claim ([verified] / [approximate])
    ASK = "ask"  # ask the user for the missing/ambiguous datum (Q1 tenant)
    PROPOSE = "propose"  # offer a review-only capability proposal, do not assert
    REPORT = "report"  # report a contradiction with a supplied answer key
    EXPLAIN = "explain"  # explain that the ask is outside the current envelope (scope)
    REFUSE = "refuse"  # hard-stop refusal (impossible / unreadable / known boundary)
    STEP_ASIDE = "step_aside"  # not this organ's domain — cede


def choose_served_disposition(
    *,
    epistemic_state: EpistemicState,
    limitation: LimitationAssessment | None,
    disclosure_claim: DisclosureClaim = DisclosureClaim.NONE,
) -> ServedDisposition:
    """Decide the served disposition. Pure, deterministic, total.

    A blocking limitation dominates — you do not serve an answer, you ask / propose /
    report / explain / refuse / step aside per its resolution action. (A limitation
    whose action is ``answer`` is non-blocking and falls through to the serve
    decision.) With no blocking limitation, the disclosure claim + epistemic state pick
    the serve mode, under the Phase-1 ``VERIFIED`` guard.

    NOTE (scaffold trust boundary): a blocking epistemic state (CONTRADICTED,
    AMBIGUOUS, UNDETERMINED) reaches this function AS a limitation (e.g. a contradiction
    arrives as ``report_contradiction``), not as ``limitation=None``. The serve branch
    trusts ``limitation=None`` to mean "servable".
    """
    if limitation is not None:
        match limitation.resolution_action:
            case "ask_question":
                return ServedDisposition.ASK
            case "emit_proposal":
                return ServedDisposition.PROPOSE
            case "report_contradiction":
                return ServedDisposition.REPORT
            case "step_aside":
                return ServedDisposition.STEP_ASIDE
            case "refuse_known_boundary":
                # scope_boundary is the governed "outside the current envelope"
                # disposition — it may render as a refusal later, but must NOT collapse
                # into a hard boundary here.
                if limitation.limitation_kind == "scope_boundary":
                    return ServedDisposition.EXPLAIN
                return ServedDisposition.REFUSE
            case "answer":
                pass  # non-blocking — fall through to the serve decision

    return _serve_disposition(epistemic_state, disclosure_claim)


def _serve_disposition(
    epistemic_state: EpistemicState, disclosure_claim: DisclosureClaim
) -> ServedDisposition:
    """The no-blocking-limitation branch: claim + state pick the serve mode."""
    match disclosure_claim:
        case DisclosureClaim.VERIFIED:
            # The Phase-1 guard: disclose-as-verified ONLY with the backing state.
            if epistemic_state is EpistemicState.VERIFIED:
                return ServedDisposition.DISCLOSE
            return ServedDisposition.COMMIT
        case DisclosureClaim.APPROXIMATE:
            return ServedDisposition.DISCLOSE
        case DisclosureClaim.PROPOSAL_ONLY:
            return ServedDisposition.PROPOSE
        case DisclosureClaim.NONE:
            return ServedDisposition.COMMIT
        case _:  # pragma: no cover - exhaustive over the 4-member enum; loud if extended
            raise AssertionError(f"unhandled disclosure_claim: {disclosure_claim!r}")


__all__ = ["ServedDisposition", "choose_served_disposition"]
