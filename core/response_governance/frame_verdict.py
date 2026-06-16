"""Default-dark FrameVerdict -> response-governance disposition (ADR-0222 §7/§14, B4 PR-4).

The ONLY lawful surface path for a closed-world verdict. It lowers a ``FrameVerdict`` to a
served disposition through the EXISTING ``core.epistemic_disclosure`` tables (no parallel
object), then hands the committed surface to the unchanged ``shape_surface`` gate.

DEFAULT-DARK: nothing in the live runtime calls this; the open-world
``govern_response`` / ``shape_surface`` STRICT path is byte-identical (this module changes no
existing file). INV-31 A3 is preserved because this module is NOT imported by
``core/response_governance/__init__`` or the open-world spine — only by the (future)
closed-world serving path and its tests.

A forged dict / untagged object cannot widen serving: the TYPE is the closed-world tag — only
a genuine ``FrameVerdict`` instance is accepted; anything else raises (INV-31 B2).

Mapping (ADR §7): committed answers (``entailed_true`` / ``entailed_false``) -> COMMIT at
``EpistemicState.INFERRED`` + ``DisclosureClaim.NONE`` (never EVIDENCED, never VERIFIED);
``contradiction`` -> REPORT; ``undetermined`` -> REFUSE; ``scope_boundary`` -> EXPLAIN.
``entailed_false`` is a grounded "No" — a committed answer, NOT a contradiction, NOT a refusal,
NOT a new ``LimitationKind``.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.epistemic_disclosure.disclosure_claim import DisclosureClaim
from core.epistemic_disclosure.disposition import (
    ServedDisposition,
    choose_served_disposition,
)
from core.epistemic_disclosure.limitation import LimitationAssessment
from core.epistemic_state import EpistemicState
from generate.frame_verdict.types import FrameVerdict, FrameVerdictKind


@dataclass(frozen=True, slots=True)
class ClosedWorldDisposition:
    """The default-dark served-disposition envelope for a closed-world verdict."""

    served_disposition: ServedDisposition
    epistemic_state: EpistemicState
    disclosure_claim: DisclosureClaim
    surface: str
    verdict: FrameVerdictKind


def disposition_for_frame_verdict(verdict: FrameVerdict) -> ClosedWorldDisposition:
    """Lower a ``FrameVerdict`` to a served disposition via the existing disclosure tables.
    Forged / untagged objects raise — the type is the closed-world tag."""
    if not isinstance(verdict, FrameVerdict):
        raise TypeError(
            "closed-world disposition requires a genuine FrameVerdict — a forged or untagged "
            "object cannot widen serving (INV-31 B2)."
        )

    limitation: LimitationAssessment | None
    match verdict.verdict:
        case FrameVerdictKind.ENTAILED_TRUE | FrameVerdictKind.ENTAILED_FALSE:
            # a committed grounded answer ("Yes" / "No"). INFERRED + DisclosureClaim.NONE
            # (ADR §7/§14); never EVIDENCED, never VERIFIED. NOT a contradiction, NOT a
            # limitation — entailed_false is an answer, not a block.
            state, limitation = EpistemicState.INFERRED, None
            surface = "Yes." if verdict.verdict is FrameVerdictKind.ENTAILED_TRUE else "No."
        case FrameVerdictKind.CONTRADICTION:
            state = EpistemicState.CONTRADICTED
            limitation = LimitationAssessment(
                limitation_kind="contradiction", resolution_action="report_contradiction",
                epistemic_state=state, owner_organ="frame_verdict",
                blocking_reason="frame_inconsistent",
            )
            surface = "The frame's premises are inconsistent."
        case FrameVerdictKind.SCOPE_BOUNDARY:
            state = EpistemicState.SCOPE_BOUNDARY
            limitation = LimitationAssessment(
                limitation_kind="scope_boundary", resolution_action="refuse_known_boundary",
                epistemic_state=state, owner_organ="frame_verdict",
                blocking_reason="outside_the_declared_frame",
            )
            surface = "That is outside the declared frame."
        case FrameVerdictKind.UNDETERMINED:
            state = EpistemicState.UNDETERMINED
            limitation = LimitationAssessment(
                limitation_kind="hard_boundary", resolution_action="refuse_known_boundary",
                epistemic_state=state, owner_organ="frame_verdict",
                blocking_reason="not_entailed_in_frame",
            )
            surface = "Undetermined within the frame."
        case _:  # pragma: no cover — exhaustive over the 5-member enum; loud if extended
            raise AssertionError(f"unhandled FrameVerdictKind: {verdict.verdict!r}")

    disposition = choose_served_disposition(
        epistemic_state=state, limitation=limitation, disclosure_claim=DisclosureClaim.NONE,
    )
    return ClosedWorldDisposition(
        served_disposition=disposition,
        epistemic_state=state,
        disclosure_claim=DisclosureClaim.NONE,
        surface=surface,
        verdict=verdict.verdict,
    )
