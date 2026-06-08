"""P0-1 — the pre-question limitation pass, as a CONSOLIDATING VIEW (session §1.5).

The intake gate of the Epistemic Disclosure spine: before contemplation chooses a
served disposition, it classifies *what KIND of limitation* is blocking resolution.
Asking a question is only one possible resolution, and asking is wrong unless the
limitation is specifically the kind a question resolves (missing/ambiguous external
information). Mis-classify and intake breaks two ways — refuse-when-should-ask (lose
the unlocking datum) or ask-when-should-propose (waste the channel).

This module is the first slice: the typed vocabulary (:data:`LimitationKind` /
:data:`ResolutionAction` / :class:`LimitationAssessment`) and the *mapping* that
DERIVES each from the already-shipped failure-family registry
(:data:`core.comprehension_attempt.failure_family.REGISTRY`) and contemplation
:class:`~generate.contemplation.findings.Terminal` set.

**Hard invariant (no fourth taxonomy).** Every assessment is mechanically derived
from an existing ``FailureFamily``; the *only* genuinely new resolution action is
``ask_question`` (the future Q1/ASK tenant — it is the one action with no shipped
terminal, see :func:`terminal_for_action`). The *only* family reclassification this
design calls for — ``missing_total_count`` / ``missing_weighted_total`` from
``capability_gap`` to ``missing_information`` — is **deferred** to Q1-B and decided
there with tests, NOT made here (see :data:`PENDING_Q1B_RECLASSIFICATION`). This
slice maps them to their *current* shipped classification.

**Off-serving.** Imports no ``generate.derivation`` / ``core.reliability_gate``; it
cannot move the sealed GSM8K metric. Nothing consumes ``resolution_action`` to change
serving yet — this slice only *classifies*.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core.comprehension_attempt.failure_family import (
    FailureFamily,
    family_for_reason,
)
from core.comprehension_attempt.model import ComprehensionAttempt
from core.epistemic_state import EpistemicState
from generate.contemplation.findings import Terminal

#: Why resolution is blocked. The split from :data:`ResolutionAction` keeps *state*
#: ("what is true / missing") distinct from *action* ("what to do about it").
LimitationKind = Literal[
    "missing_information",  # a needed datum is absent — could be supplied → ask
    "ambiguous_structure",  # data present, relationship unclear → ask (when user-resolvable)
    "scope_boundary",  # exceeds the current capability/evidence envelope → refuse/explain
    "capability_gap",  # info present, CORE lacks the transform → propose (or refuse if signal too coarse)
    "hard_boundary",  # mathematically/logically impossible or undefined → refuse
    "contradiction",  # evidence conflicts with a claimed answer → report
    "renderability_gap",  # asking is right but terms aren't grounded enough to name safely → ask-generic
    "input_shape",  # not this organ's domain → step aside
]

#: What to do about a limitation. ``ask_question`` is the genuinely new action this
#: spine introduces; the other five each correspond to a shipped contemplation
#: terminal (:func:`terminal_for_action`).
ResolutionAction = Literal[
    "answer",
    "ask_question",
    "emit_proposal",
    "refuse_known_boundary",
    "report_contradiction",
    "step_aside",
]


@dataclass(frozen=True, slots=True)
class LimitationAssessment:
    """One typed classification of the limitation blocking a comprehension attempt.

    ``epistemic_state`` (what is true) and ``resolution_action`` (what to do) are
    deliberately distinct: e.g. ``UNDETERMINED`` + ``ask_question`` for a missing
    datum. ``blocking_reason`` is the failure-family key (the partition key), so the
    assessment is back-traceable to the shipped registry.
    """

    limitation_kind: LimitationKind
    resolution_action: ResolutionAction
    epistemic_state: EpistemicState
    owner_organ: str | None
    blocking_reason: str


# --- The consolidating mapping (derived from the shipped registry, not invented) ---

#: ``EpistemicState`` each kind asserts. ``scope_boundary`` lights up the RESERVED
#: ``SCOPE_BOUNDARY`` state with a real producer; ``contradiction`` / ``ambiguous``
#: reuse the ACTIVE states. The refuse/propose kinds share ``UNDETERMINED`` — the
#: *kind* carries the distinction, the *state* only says "no answer determined".
_KIND_TO_STATE: dict[str, EpistemicState] = {
    "missing_information": EpistemicState.UNDETERMINED,
    "ambiguous_structure": EpistemicState.AMBIGUOUS,
    "scope_boundary": EpistemicState.SCOPE_BOUNDARY,
    "capability_gap": EpistemicState.UNDETERMINED,
    "hard_boundary": EpistemicState.UNDETERMINED,
    "contradiction": EpistemicState.CONTRADICTED,
    "renderability_gap": EpistemicState.UNDETERMINED,
    "input_shape": EpistemicState.UNDETERMINED,
}

#: The shipped contemplation ``Terminal`` each action corresponds to. ``ask_question``
#: is ``None`` — it is the ONE action the spine adds that has no terminal yet (Q1/ASK).
#: This map is the proof that the limitation pass is a consolidating view, not a new
#: universe: five of six actions already exist as terminals.
_ACTION_TO_TERMINAL: dict[str, Terminal | None] = {
    "answer": Terminal.SOLVED_VERIFIED,
    "emit_proposal": Terminal.PROPOSAL_EMITTED,
    "refuse_known_boundary": Terminal.REFUSED_KNOWN_BOUNDARY,
    "report_contradiction": Terminal.CONTRADICTION_DETECTED,
    "step_aside": Terminal.NO_PROGRESS,
    "ask_question": None,
}

#: Families Q1-B will reclassify (``capability_gap`` → ``missing_information``): the
#: user CAN supply the total, so it is missing information, not a capability gap. NOT
#: changed here — this slice keeps the current classification; Q1-B flips it with its
#: own tests. Listed so the deferral is explicit and greppable.
PENDING_Q1B_RECLASSIFICATION: frozenset[str] = frozenset(
    {"missing_total_count", "missing_weighted_total"}
)

#: family name → (LimitationKind, ResolutionAction). Keys must equal the REGISTRY's
#: family names exactly (asserted total by test). Classification rationale per family:
#:  - growth surfaces (``proposal_allowed``) → ``capability_gap`` / ``emit_proposal``
#:  - underdetermined / missing-datum refusals → ``missing_information`` / ``ask_question``
#:  - same-unit-but-no-cue ambiguity the user could resolve → ``ambiguous_structure`` / ask
#:  - math/logic impossibility, incoherence, coarse-signal parse gaps → ``hard_boundary`` / refuse
#:  - beyond-current-solver-envelope → ``scope_boundary`` / refuse
#:  - the answer-key verdict → ``contradiction`` / ``report_contradiction``
#:  - foreign text → ``input_shape`` / ``step_aside``
_FAMILY_TO_LIMITATION: dict[str, tuple[LimitationKind, ResolutionAction]] = {
    # cross-organ
    "input_shape": ("input_shape", "step_aside"),
    "admissibility_incompatible": ("hard_boundary", "refuse_known_boundary"),
    # R1
    "unsupported_clause_shape": ("capability_gap", "refuse_known_boundary"),
    "ungrounded_base": ("missing_information", "ask_question"),
    "over_determined": ("hard_boundary", "refuse_known_boundary"),
    # R2 boundaries
    "unsupported_system_size": ("scope_boundary", "refuse_known_boundary"),
    "indistinguishable_system": ("hard_boundary", "refuse_known_boundary"),
    "non_integer_solution": ("hard_boundary", "refuse_known_boundary"),
    "negative_solution": ("hard_boundary", "refuse_known_boundary"),
    "answer_choice_unresolved": ("ambiguous_structure", "refuse_known_boundary"),
    # R2 growth surfaces
    "missing_total_count": ("capability_gap", "emit_proposal"),  # PENDING_Q1B → missing_information/ask
    "missing_weighted_total": ("capability_gap", "emit_proposal"),  # PENDING_Q1B → missing_information/ask
    "missing_category_pair": ("capability_gap", "emit_proposal"),
    "missing_attribute_coefficient": ("capability_gap", "emit_proposal"),
    # R2 verdict
    "answer_key_contradiction": ("contradiction", "report_contradiction"),
    # R3
    "unsupported_rate_duration": ("capability_gap", "emit_proposal"),
    "rate_underdetermined": ("missing_information", "ask_question"),
    "unsupported_temporal_state": ("scope_boundary", "refuse_known_boundary"),
    # R4 combined-rate boundaries
    "cmb_unit_mismatch": ("hard_boundary", "refuse_known_boundary"),
    "cmb_combine_ambiguous": ("ambiguous_structure", "ask_question"),
    "cmb_underdetermined": ("missing_information", "ask_question"),
    "cmb_non_positive_net": ("hard_boundary", "refuse_known_boundary"),
    "cmb_non_integer": ("hard_boundary", "refuse_known_boundary"),
    # R4 growth surfaces
    "cmb_unsupported_rate_count": ("capability_gap", "emit_proposal"),
    "cmb_unsupported_reciprocal": ("capability_gap", "emit_proposal"),
    "cmb_unsupported_clock_interval": ("capability_gap", "emit_proposal"),
}

# A conservative refusal for any family/reason that is not in the mapping. The total
# mapping (asserted by test against REGISTRY) means this is dead in practice; if a new
# family ever lands unmapped, it refuses — it NEVER silently becomes an answerable
# question (the wrong=0-safe default).
_CONSERVATIVE_DEFAULT: tuple[LimitationKind, ResolutionAction] = (
    "hard_boundary",
    "refuse_known_boundary",
)


def assess_from_family(family: FailureFamily) -> LimitationAssessment:
    """The limitation a failure family expresses, as a typed assessment.

    Total over :data:`REGISTRY` (asserted by test). An unmapped family falls to the
    conservative refuse default — never ``ask_question``.
    """
    kind, action = _FAMILY_TO_LIMITATION.get(family.name, _CONSERVATIVE_DEFAULT)
    return LimitationAssessment(
        limitation_kind=kind,
        resolution_action=action,
        epistemic_state=_KIND_TO_STATE[kind],
        owner_organ=family.owner,
        blocking_reason=family.name,
    )


def assess_from_attempt(attempt: ComprehensionAttempt) -> LimitationAssessment | None:
    """Classify the limitation a comprehension attempt expresses, or ``None``.

    - ``contradiction`` outcome → report it (no refusal reason carries this; it is the
      answer-choice verdict).
    - a refusal → classify via its failure family; an *unclassified* refusal reason
      falls to the conservative refuse default (never ``ask_question``).
    - any non-limitation outcome (solved/admissible setup, or eval-only ``*_wrong``)
      → ``None``: there is no resolvable limitation to act on.
    """
    if attempt.outcome == "contradiction":
        return LimitationAssessment(
            limitation_kind="contradiction",
            resolution_action="report_contradiction",
            epistemic_state=EpistemicState.CONTRADICTED,
            owner_organ=attempt.organ,
            blocking_reason="answer_key_contradiction",
        )
    if not attempt.is_refusal:
        return None
    family = family_for_reason(attempt.refusal_reason)
    if family is None:
        kind, action = _CONSERVATIVE_DEFAULT
        return LimitationAssessment(
            limitation_kind=kind,
            resolution_action=action,
            epistemic_state=_KIND_TO_STATE[kind],
            owner_organ=attempt.organ,
            blocking_reason=attempt.refusal_reason or "unclassified",
        )
    return assess_from_family(family)


def terminal_for_action(action: ResolutionAction) -> Terminal | None:
    """The shipped contemplation ``Terminal`` an action corresponds to.

    ``None`` only for ``ask_question`` — the one action this spine adds that has no
    shipped terminal yet (the Q1/ASK tenant). Every other action maps to an existing
    terminal, which is what makes this a consolidating view rather than a new taxonomy.
    """
    return _ACTION_TO_TERMINAL[action]


__all__ = [
    "PENDING_Q1B_RECLASSIFICATION",
    "LimitationAssessment",
    "LimitationKind",
    "ResolutionAction",
    "assess_from_attempt",
    "assess_from_family",
    "terminal_for_action",
]
