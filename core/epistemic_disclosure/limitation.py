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
terminal, see :func:`terminal_for_action`).

**Q1-B transitional carve-out (this slice).** Two shipped families —
``missing_total_count`` and ``missing_weighted_total`` — are classified here as
``missing_information`` / ``ask_question``: the user *could state the total* and
unblock solving, so they are missing data, not capability gaps. The shipped
:data:`REGISTRY` still flags them ``proposal_allowed = True`` so that existing
consumers (:mod:`core.comprehension_attempt.proposal` /
:mod:`generate.contemplation.pass_manager`) keep emitting proposal-only artifacts
to the pile — until Q1-C/Q1-D wire ASK delivery to a served surface there is
nowhere for an ``ask_question`` to go, and silently dropping the proposal signal
would be a capability regression with no compensating intake. Once ASK is serving,
the REGISTRY flag flips to ``False`` and the carve-out
(:data:`Q1B_ASK_CARVE_OUT`) retires. The carve-out is named, enumerated, and
covered by an explicit test (``tests/test_limitation_assessment.py``) so its
removal is a conscious act, not a silent re-key.

**Off-serving.** Imports no ``generate.derivation`` / ``core.reliability_gate``; it
cannot move the sealed GSM8K metric. Nothing consumes ``resolution_action`` to change
serving yet — this slice only *classifies* and *describes residue*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
class MissingSlot:
    """One typed slot the ASK limitation identifies as missing.

    A *structural* description (NOT user-renderable prose): ``slot_name`` is the
    family-defined slot identifier (e.g. ``"total_count"``); ``expected_unit_or_type``
    is the family-typed expectation a future bound answer must satisfy (e.g.
    ``"count_int"``); ``binding_target`` is the structural role the slot fills in
    the organ's setup (e.g. ``"collective_unit_total"``), which Q2 answer-binding
    re-enters the gate against (scoping §4). Renderable, user-facing strings come
    later from grounded text spans (:attr:`LimitationAssessment.grounded_terms`),
    NEVER from these snake_case identifiers — that split is what keeps the renderer
    wrong=0-safe (scoping §2).
    """

    slot_name: str
    expected_unit_or_type: str
    binding_target: str


@dataclass(frozen=True, slots=True)
class LimitationAssessment:
    """One typed classification of the limitation blocking a comprehension attempt.

    ``epistemic_state`` (what is true) and ``resolution_action`` (what to do) are
    deliberately distinct: e.g. ``UNDETERMINED`` + ``ask_question`` for a missing
    datum. ``blocking_reason`` is the failure-family key (the partition key), so the
    assessment is back-traceable to the shipped registry.

    ``missing_slots`` and ``grounded_terms`` are the ASK *typed residue* — populated
    only for ``ask_question`` resolutions by :func:`assess_from_attempt`. Both
    default to empty so existing P0-1 callers using :func:`assess_from_family`
    continue to work unchanged. The wrong=0 invariant (scoping §2): a slot here
    carries family-typed structural identifiers only; renderable prose must come
    from ``grounded_terms`` (verbatim text spans), never fabricated.
    """

    limitation_kind: LimitationKind
    resolution_action: ResolutionAction
    epistemic_state: EpistemicState
    owner_organ: str | None
    blocking_reason: str
    missing_slots: tuple[MissingSlot, ...] = field(default_factory=tuple)
    grounded_terms: tuple[str, ...] = field(default_factory=tuple)


# --- The consolidating mapping (derived from the shipped registry, not invented) ---

#: ``EpistemicState`` each kind asserts. ``scope_boundary`` lights up the RESERVED
#: ``SCOPE_BOUNDARY`` state with a real producer; ``contradiction`` / ``ambiguous``
#: reuse the ACTIVE states. The refuse/propose kinds share ``UNDETERMINED`` — the
#: *kind* carries the distinction, the *state* only says "no answer determined".
_KIND_TO_STATE: dict[LimitationKind, EpistemicState] = {
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
_ACTION_TO_TERMINAL: dict[ResolutionAction, Terminal | None] = {
    "answer": Terminal.SOLVED_VERIFIED,
    "emit_proposal": Terminal.PROPOSAL_EMITTED,
    "refuse_known_boundary": Terminal.REFUSED_KNOWN_BOUNDARY,
    "report_contradiction": Terminal.CONTRADICTION_DETECTED,
    "step_aside": Terminal.NO_PROGRESS,
    "ask_question": None,
}

#: **Transitional carve-out (Q1-B).** Families this slice classifies as
#: ``ask_question`` in the limitation layer while their shipped
#: :data:`REGISTRY` entries keep ``proposal_allowed = True`` so the contemplation
#: pass and proposal pile keep working unchanged. This is an honest migration seam:
#: the disclosure layer speaks the truthful classification now; the operational
#: layer keeps the current signal so nothing regresses before Q1-C/Q1-D wires ASK
#: delivery. Retirement: once ASK is serving, flip ``proposal_allowed = False`` on
#: these two families in :mod:`core.comprehension_attempt.failure_family`, drop
#: this set, and amend the ``proposal_allowed`` invariant in tests.
Q1B_ASK_CARVE_OUT: frozenset[str] = frozenset(
    {"missing_total_count", "missing_weighted_total"}
)

#: family name → (LimitationKind, ResolutionAction). Keys must equal the REGISTRY's
#: family names exactly (asserted total by test). Classification rationale per family:
#:  - growth surfaces (``proposal_allowed``) → ``capability_gap`` / ``emit_proposal``
#:    EXCEPT :data:`Q1B_ASK_CARVE_OUT` — see that constant's docstring
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
    # R2 growth surfaces — Q1-B reclassification (see Q1B_ASK_CARVE_OUT):
    # disclosure says ask; REGISTRY still emits proposals to the pile.
    "missing_total_count": ("missing_information", "ask_question"),
    "missing_weighted_total": ("missing_information", "ask_question"),
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

#: family name → typed slots an ASK assessment for that family identifies as missing.
#: Only families with a *known* slot structure appear here; an ask-mapped family without
#: an entry yields an empty residue (the "minimal" stance — never fabricate a slot the
#: family's contract has not pinned down yet). Slot semantics, per family:
#:  - ``missing_total_count``  : the collective-unit total count (R2 constraint C7);
#:    ``binding_target`` matches the equation slot the augmented input would fill
#:    (Q2 re-entry, scoping §4).
#:  - ``missing_weighted_total``: the measured-unit weighted total (R2 constraint C8).
#: Other ask-mapped families (``ungrounded_base``, ``rate_underdetermined``,
#: ``cmb_underdetermined``, ``cmb_combine_ambiguous``) get slots in later Q1 sub-PRs
#: once their per-family slot signatures are pinned with tests.
_FAMILY_TO_MISSING_SLOTS: dict[str, tuple[MissingSlot, ...]] = {
    "missing_total_count": (
        MissingSlot(
            slot_name="total_count",
            expected_unit_or_type="count_int",
            binding_target="collective_unit_total",
        ),
    ),
    "missing_weighted_total": (
        MissingSlot(
            slot_name="weighted_total",
            expected_unit_or_type="measured_unit_int",
            binding_target="weighted_total_value",
        ),
    ),
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
    conservative refuse default — never ``ask_question``. Residue defaults to empty;
    populating typed slots / grounded terms requires a specific attempt (use
    :func:`assess_from_attempt`).
    """
    kind, action = _FAMILY_TO_LIMITATION.get(family.name, _CONSERVATIVE_DEFAULT)
    return LimitationAssessment(
        limitation_kind=kind,
        resolution_action=action,
        epistemic_state=_KIND_TO_STATE[kind],
        owner_organ=family.owner,
        blocking_reason=family.name,
    )


def _residue_from_attempt(
    attempt: ComprehensionAttempt,
    family: FailureFamily,
    action: ResolutionAction,
) -> tuple[tuple[MissingSlot, ...], tuple[str, ...]]:
    """Typed ASK residue for an ask-mapped attempt — empty for any other action.

    Wrong=0 invariant (scoping §2): ``grounded_terms`` carries only verbatim text from
    :attr:`ComprehensionAttempt.evidence` SourceSpanLinks. If the attempt carries no
    evidence (today: every refused attempt — :mod:`core.comprehension_attempt.classify`
    leaves ``evidence = ()``), ``grounded_terms`` is empty, NEVER fabricated from the
    family or the refusal reason. ``missing_slots`` is family-derived (snake_case
    structural identifiers, not renderable prose) so it is always safe to emit; absent
    from :data:`_FAMILY_TO_MISSING_SLOTS` ⇒ no slots (minimal stance — never invent a
    slot the family contract has not pinned down).
    """
    if action != "ask_question":
        return ((), ())
    slots = _FAMILY_TO_MISSING_SLOTS.get(family.name, ())
    grounded = tuple(link.text for link in attempt.evidence)
    return (slots, grounded)


def assess_from_attempt(attempt: ComprehensionAttempt) -> LimitationAssessment | None:
    """Classify the limitation a comprehension attempt expresses, or ``None``.

    - ``contradiction`` outcome → report it (no refusal reason carries this; it is the
      answer-choice verdict).
    - a refusal → classify via its failure family; an *unclassified* refusal reason
      falls to the conservative refuse default (never ``ask_question``).
    - any non-limitation outcome (solved/admissible setup, or eval-only ``*_wrong``)
      → ``None``: there is no resolvable limitation to act on.

    For ask-mapped refusals, the returned assessment carries typed residue
    (:attr:`~LimitationAssessment.missing_slots` / ``grounded_terms``) per
    :func:`_residue_from_attempt`'s wrong=0 invariant.
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
    base = assess_from_family(family)
    missing_slots, grounded_terms = _residue_from_attempt(
        attempt, family, base.resolution_action
    )
    if not missing_slots and not grounded_terms:
        return base
    return LimitationAssessment(
        limitation_kind=base.limitation_kind,
        resolution_action=base.resolution_action,
        epistemic_state=base.epistemic_state,
        owner_organ=attempt.organ,
        blocking_reason=base.blocking_reason,
        missing_slots=missing_slots,
        grounded_terms=grounded_terms,
    )


def terminal_for_action(action: ResolutionAction) -> Terminal | None:
    """The shipped contemplation ``Terminal`` an action corresponds to.

    ``None`` only for ``ask_question`` — the one action this spine adds that has no
    shipped terminal yet (the Q1/ASK tenant). Every other action maps to an existing
    terminal, which is what makes this a consolidating view rather than a new taxonomy.
    """
    return _ACTION_TO_TERMINAL[action]


__all__ = [
    "Q1B_ASK_CARVE_OUT",
    "LimitationAssessment",
    "LimitationKind",
    "MissingSlot",
    "ResolutionAction",
    "assess_from_attempt",
    "assess_from_family",
    "terminal_for_action",
]
