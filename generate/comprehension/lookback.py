"""ADR-0174 Phase 3 — lookback re-evaluation operator.

When a hypothesis carries unresolved slots (entries in
``Hypothesis.unresolved``), a later token can refine those slots —
binding a pronoun to its proper-noun antecedent, attaching a unit to a
dangling quantity, narrowing an ambiguous verb category.  This module
provides the ``reevaluate`` operator that applies a refinement to a
held hypothesis and re-runs the existing admissibility check.

Phase 3a (this module): the **substrate** for lookback. Concrete
refinement types:

  - :class:`PronounResolution` — bind a pronoun actor to a resolved
    proper-noun referent. The ``matched_actor_token`` stays as the
    pronoun (which IS in source, so grounding still passes); only the
    semantic actor field on the underlying Operation /
    InitialPossession is rewritten to the resolved name.

Phase 3b (follow-up): :class:`CompoundClauseExpansion` and other
refinement types covering the remaining compound-clause and verb-set
narrowness layers.  The reevaluate operator handles any refinement
type implementing :class:`Refinement`; adding new types does not
require ADR amendments to this module (only to the closed list of
``VALID_REFINEMENT_KINDS`` so the trace consumer can branch
deterministically).

Trust boundary: this module never weakens an admissibility predicate.
Every refined hypothesis is re-run through
:func:`generate.comprehension.constraint_propagation.check_constraints`
after refinement; a hypothesis that would fail constraints in its
refined form is eliminated, returning ``None`` from ``reevaluate``.
The ``wrong = 0`` invariant is preserved by construction — refinement
can only convert a refused hypothesis into an admitted one if every
admissibility sub-check passes on the refined candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, Union

from generate.comprehension.constraint_propagation import (
    ConstraintResult,
    check_constraints,
)
from generate.comprehension.state import (
    ComprehensionStateError,
    Hypothesis,
)


# ---------------------------------------------------------------------------
# Closed set of refinement kinds (trace contract)
# ---------------------------------------------------------------------------

# Each kind name identifies one concrete refinement subclass below.
# Adding a new kind requires adding a subclass AND extending this set
# (so the reader_trace consumer can branch deterministically without
# pattern-matching on Python types).
VALID_REFINEMENT_KINDS: Final[frozenset[str]] = frozenset(
    {
        "pronoun_resolution",
        # Phase 3b will add: "compound_clause_expansion", etc.
    }
)


# Closed slot names that may appear in Hypothesis.unresolved tuples.
# Refinements bind to one of these slots; the reevaluate operator
# matches refinement→slot via this closed set.
VALID_UNRESOLVED_SLOTS: Final[frozenset[str]] = frozenset(
    {
        "actor_pronoun",
        # Phase 3b will add: "clause_separator", etc.
    }
)


# ---------------------------------------------------------------------------
# Refinement types — sealed union via Refinement Union alias
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PronounResolution:
    """Refinement: bind an unresolved-actor pronoun to a proper-noun antecedent.

    Phase 3a — applied to a held :class:`Hypothesis` carrying
    ``"actor_pronoun"`` in its ``unresolved`` tuple.  The refinement
    leaves the underlying candidate's ``matched_actor_token`` intact
    (the pronoun, which grounds in the held statement's source span),
    and rewrites the candidate's semantic actor field
    (``Operation.actor`` for :class:`CandidateOperation`,
    ``InitialPossession.entity`` for :class:`CandidateInitial`) to the
    resolved name.

    The ``pronoun`` field carries the surface form for trace fidelity
    so the reader_trace event can record which pronoun was resolved at
    which token position.

    Fields:
        kind:        Literal "pronoun_resolution" (matches
                     VALID_REFINEMENT_KINDS membership; structural
                     discriminator for the Union below).
        pronoun:     Surface pronoun in the held statement
                     (e.g. ``"She"``, ``"He"``, ``"it"``).
        resolved_to: Proper-noun referent
                     (e.g. ``"Jan"``, ``"Georgie"``).
        evidence_source: Where the resolution came from — a closed set
                     of values so the trace consumer can attribute
                     deterministically.
    """

    pronoun: str
    resolved_to: str
    evidence_source: Literal["discourse_prior_subjects", "running_subject"]
    kind: Literal["pronoun_resolution"] = "pronoun_resolution"

    def __post_init__(self) -> None:
        if not isinstance(self.pronoun, str) or not self.pronoun:
            raise ComprehensionStateError(
                "PronounResolution.pronoun must be non-empty str"
            )
        if not isinstance(self.resolved_to, str) or not self.resolved_to:
            raise ComprehensionStateError(
                "PronounResolution.resolved_to must be non-empty str"
            )
        if self.evidence_source not in (
            "discourse_prior_subjects",
            "running_subject",
        ):
            raise ComprehensionStateError(
                "PronounResolution.evidence_source must be in "
                "{'discourse_prior_subjects', 'running_subject'}; "
                f"got {self.evidence_source!r}"
            )
        if self.kind != "pronoun_resolution":
            raise ComprehensionStateError(
                "PronounResolution.kind must be 'pronoun_resolution'"
            )


# Sealed union of all Phase-3 refinement types. Phase 3b will extend
# this with CompoundClauseExpansion etc.
Refinement = Union[PronounResolution]


# ---------------------------------------------------------------------------
# Internal: rebuild candidate with resolved actor
# ---------------------------------------------------------------------------


def _rebuild_candidate_with_resolved_actor(
    candidate: object, resolved_to: str
) -> object | None:
    """Rebuild a candidate replacing the semantic-actor field.

    For :class:`CandidateOperation`: rebuilds with a new
    :class:`Operation` carrying ``actor=resolved_to`` and keeps every
    other slot (operand, matched_verb, matched_value_token, etc.)
    intact.  ``matched_actor_token`` deliberately stays as the pronoun
    so the grounding check (``_token_in(matched_actor_token, haystack)``)
    continues to pass against the held statement's source span.

    For :class:`CandidateInitial`: rebuilds with a new
    :class:`InitialPossession` carrying ``entity=resolved_to`` and
    preserves ``matched_entity_token`` as the pronoun.

    Returns ``None`` when the candidate is not a known type — the
    caller treats this as a refinement-no-op (the hypothesis remains
    held, lookback did not find anything to do here).
    """
    # Lazy imports to avoid circular dependency on candidate-graph layer.
    from generate.math_candidate_parser import CandidateInitial
    from generate.math_problem_graph import (
        InitialPossession,
        Operation,
    )
    from generate.math_roundtrip import CandidateOperation

    if isinstance(candidate, CandidateOperation):
        old_op = candidate.op
        new_op = Operation(
            actor=resolved_to,
            kind=old_op.kind,
            operand=old_op.operand,
            target=old_op.target,
        )
        return CandidateOperation(
            op=new_op,
            source_span=candidate.source_span,
            matched_verb=candidate.matched_verb,
            matched_value_token=candidate.matched_value_token,
            matched_unit_token=candidate.matched_unit_token,
            matched_actor_token=candidate.matched_actor_token,
            matched_target_token=candidate.matched_target_token,
            matched_reference_actor_token=candidate.matched_reference_actor_token,
        )
    if isinstance(candidate, CandidateInitial):
        old_initial = candidate.initial
        new_initial = InitialPossession(
            entity=resolved_to,
            quantity=old_initial.quantity,
        )
        return CandidateInitial(
            initial=new_initial,
            source_span=candidate.source_span,
            matched_anchor=candidate.matched_anchor,
            matched_value_token=candidate.matched_value_token,
            matched_unit_token=candidate.matched_unit_token,
            matched_entity_token=candidate.matched_entity_token,
            composition_evidence=candidate.composition_evidence,
        )
    return None


# ---------------------------------------------------------------------------
# reevaluate operator
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReevaluateResult:
    """Outcome of a single reevaluate call.

    Fields:
        refined:          The refined Hypothesis if admitted, else None.
        previous:         The original hypothesis before refinement
                          (carried so trace events can record what changed).
        refinement_kind:  The refinement kind that was attempted
                          (matches Refinement.kind on the input).
        constraint_result: The result of re-running check_constraints
                          on the refined candidate (or None if refinement
                          could not be applied because the candidate
                          type was unknown).
        elimination_reason: Non-None iff refined is None.
    """

    refined: Hypothesis | None
    previous: Hypothesis
    refinement_kind: str
    constraint_result: ConstraintResult | None
    elimination_reason: str | None

    def __post_init__(self) -> None:
        if self.refinement_kind not in VALID_REFINEMENT_KINDS:
            raise ComprehensionStateError(
                "ReevaluateResult.refinement_kind must be in "
                f"VALID_REFINEMENT_KINDS; got {self.refinement_kind!r}"
            )
        if self.refined is None and self.elimination_reason is None:
            raise ComprehensionStateError(
                "ReevaluateResult.refined=None requires a non-None "
                "elimination_reason"
            )
        if self.refined is not None and self.elimination_reason is not None:
            raise ComprehensionStateError(
                "ReevaluateResult.refined is not None but "
                f"elimination_reason={self.elimination_reason!r} is set; "
                "these are inconsistent"
            )


def reevaluate(
    hypothesis: Hypothesis, refinement: Refinement
) -> ReevaluateResult:
    """Apply ``refinement`` to ``hypothesis``, re-run constraint check.

    Per ADR-0174 §Decision §Lookback: lookback walks open hypotheses
    and recomputes prior assignments when a later token resolves an
    earlier ambiguity.  This operator is the per-hypothesis primitive
    that pass invokes.

    Semantics:

      - If the refinement targets a slot that isn't in
        ``hypothesis.unresolved``, the refinement is a no-op: the
        function returns ``ReevaluateResult(refined=hypothesis, …)`` so
        the caller can keep the hypothesis unchanged.  This matches
        the ADR's "uncontested tokens contribute no recomputation
        work" bound.
      - If the refinement applies but the rebuilt candidate fails the
        re-run constraint check, ``refined`` is ``None`` and
        ``elimination_reason`` carries the first failing predicate's
        reason.
      - If the refinement applies and constraints pass, ``refined`` is
        a new :class:`Hypothesis` with the resolved slot removed from
        ``unresolved`` and a ``category_assignments`` entry recording
        the refinement event.

    The returned :class:`ReevaluateResult` always includes the previous
    hypothesis so trace serialisation can record the before/after pair.
    """
    # Dispatch on refinement kind. Phase 3a knows pronoun_resolution.
    # The defensive raise below is unreachable today (the Refinement
    # Union has one member), but it is correct future-proofing for
    # Phase 3b's CompoundClauseExpansion and other refinement types —
    # if a caller passes a non-Union type by accident, fail loudly.
    if isinstance(refinement, PronounResolution):
        return _apply_pronoun_resolution(hypothesis, refinement)
    raise ComprehensionStateError(  # type: ignore[unreachable]
        f"reevaluate: unsupported refinement type {type(refinement).__name__}"
    )


def _apply_pronoun_resolution(
    hypothesis: Hypothesis, refinement: PronounResolution
) -> ReevaluateResult:
    """Inner: rebuild candidate with resolved actor, re-run constraints."""
    if "actor_pronoun" not in hypothesis.unresolved:
        # No-op: this hypothesis doesn't carry the slot the refinement
        # targets. Return unchanged.
        return ReevaluateResult(
            refined=hypothesis,
            previous=hypothesis,
            refinement_kind=refinement.kind,
            constraint_result=None,
            elimination_reason=None,
        )

    rebuilt = _rebuild_candidate_with_resolved_actor(
        hypothesis.candidate, refinement.resolved_to
    )
    if rebuilt is None:
        # Candidate type unknown — refinement cannot apply. Return the
        # hypothesis unchanged; caller can decide whether to eliminate
        # on its own terms.
        return ReevaluateResult(
            refined=hypothesis,
            previous=hypothesis,
            refinement_kind=refinement.kind,
            constraint_result=None,
            elimination_reason=None,
        )

    # Build the refined hypothesis: same rank, same confidence_rank,
    # category_assignments extended with a refinement trace entry,
    # unresolved minus the now-resolved slot.
    #
    # The trace entry uses token_index=0 because Phase 3a applies
    # refinements at the problem level (after all sentences have been
    # processed), not at a specific token position. Phase 3b/4 may
    # specialise this when refinements fire mid-token-stream.
    refined_assignments = hypothesis.category_assignments + (
        (0, "pronoun_resolved", refinement.pronoun),
    )
    refined_unresolved = tuple(
        slot for slot in hypothesis.unresolved if slot != "actor_pronoun"
    )

    refined_hyp = Hypothesis(
        candidate=rebuilt,
        category_assignments=refined_assignments,
        constraint_state=hypothesis.constraint_state,
        confidence_rank=hypothesis.confidence_rank,
        unresolved=refined_unresolved,
    )

    # Re-run constraints. Refinement preserves wrong=0 by gating on the
    # same admissibility predicates that admit candidates today; a
    # refinement that produces a candidate failing any sub-check is
    # eliminated.
    result = check_constraints(refined_hyp)
    if result.admitted:
        return ReevaluateResult(
            refined=refined_hyp,
            previous=hypothesis,
            refinement_kind=refinement.kind,
            constraint_result=result,
            elimination_reason=None,
        )
    return ReevaluateResult(
        refined=None,
        previous=hypothesis,
        refinement_kind=refinement.kind,
        constraint_result=result,
        elimination_reason=(
            f"pronoun_resolution refined candidate failed re-check: "
            f"{result.elimination_reason}"
        ),
    )


__all__ = [
    "PronounResolution",
    "Refinement",
    "ReevaluateResult",
    "VALID_REFINEMENT_KINDS",
    "VALID_UNRESOLVED_SLOTS",
    "reevaluate",
]
