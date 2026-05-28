"""ADR-0174 Phase 2 — continuous constraint propagation.

Hoists the candidate-graph layer's admissibility predicates
(``_initial_admissible``, ``roundtrip_admissible``) into per-hypothesis
constraint checks that fire during reading rather than only at the end
of :func:`generate.math_candidate_graph.parse_and_solve`.

Phase 2 scope (this module):

  - ``hypothesis_from_initial`` / ``hypothesis_from_operation`` —
    adapters that wrap an existing :class:`CandidateInitial` /
    :class:`CandidateOperation` as a Phase-1 :class:`Hypothesis` ready
    to flow through ``ProblemReadingState.open_hypotheses``.
  - ``check_constraints`` — runs the same admissibility predicates the
    candidate-graph layer runs today, but returns a structured
    :class:`ConstraintResult` carrying the specific elimination reason
    instead of a bare bool.  Sub-checks are decomposed so a Phase-3
    partial hypothesis can run only the predicates whose slots are
    populated.
  - ``eliminate_violating`` — applies ``check_constraints`` to a tuple
    of hypotheses, returns ``(surviving, eliminations)``.  An
    elimination record carries the hypothesis id, the predicate that
    fired, and the reason — designed to serialise into a
    ``reader_trace`` event.

Phase 2 does NOT change admission semantics.  A candidate that passes
``check_constraints`` here is byte-equivalent to one that passes
``_initial_admissible`` / ``roundtrip_admissible`` at the
candidate-graph layer today.  The change is structural: the constraint
check is now hypothesis-based, the elimination is structured, and the
trace is visible.  Phase 3 will populate hypotheses from partial reads
(``apply_word`` mid-sentence); Phase 4 will wire in-loop contemplation
to resolve ambiguities the constraint check leaves with multiple
survivors.

Trust boundary: this module is read-only over the existing predicates.
It does not weaken any admissibility check.  The ``wrong = 0``
invariant is preserved by construction — every surviving hypothesis has
passed exactly the same predicate sub-checks that admit candidates
today.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, cast

from generate.comprehension.state import (
    ComprehensionStateError,
    HYPOTHESIS_CAP,
    Hypothesis,
)


# ---------------------------------------------------------------------------
# Constraint-result types
# ---------------------------------------------------------------------------


# Closed set of predicate names that may appear in a constraint result.
# Adding a new predicate requires an ADR amendment (the predicate names
# are a structural contract with the reader_trace consumer).
VALID_PREDICATE_NAMES: Final[frozenset[str]] = frozenset(
    {
        # _initial_admissible sub-checks
        "initial.anchor_grounds",
        "initial.value_grounds",
        "initial.unit_grounds",
        "initial.entity_grounds",
        # _composed_initial_admissible sub-checks (RAT-1)
        "composed_initial.evidence_complete",
        "composed_initial.input_tokens_ground",
        "composed_initial.currency_symbol_present",
        "composed_initial.entity_token_present",
        # roundtrip_admissible sub-checks
        "operation.verb_registered",
        "operation.verb_grounds",
        "operation.actor_grounds",
        "operation.value_grounds",
        "operation.unit_grounds",
        "operation.target_grounds",
        "operation.reference_actor_grounds",
        "operation.operand_shape_consistent",
        "operation.rate_denominator_grounds",
    }
)


@dataclass(frozen=True, slots=True)
class ConstraintResult:
    """Outcome of running constraints against one hypothesis.

    Fields:
        admitted:    True iff every applicable sub-check passed.
        predicates_run: Tuple of (predicate_name, outcome) for every
                     sub-check that fired. Sub-checks whose slots were
                     unpopulated are not included (Phase-3 conservative
                     in-flight behavior; Phase-2 candidates are complete
                     so every applicable predicate fires).
        elimination_reason: Non-None iff admitted=False; the first
                     predicate that failed (sub-checks short-circuit on
                     first failure to preserve current behavior).
    """

    admitted: bool
    predicates_run: tuple[tuple[str, Literal["ok", "fail", "skip"]], ...]
    elimination_reason: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.admitted, bool):
            raise ComprehensionStateError(
                f"ConstraintResult.admitted must be bool; got "
                f"{type(self.admitted).__name__}"
            )
        if not isinstance(self.predicates_run, tuple):
            raise ComprehensionStateError(
                "ConstraintResult.predicates_run must be tuple"
            )
        for idx, entry in enumerate(self.predicates_run):
            if not (
                isinstance(entry, tuple)
                and len(entry) == 2
                and isinstance(entry[0], str)
                and entry[0] in VALID_PREDICATE_NAMES
                and entry[1] in ("ok", "fail", "skip")
            ):
                raise ComprehensionStateError(
                    f"ConstraintResult.predicates_run[{idx}] must be "
                    "(predicate_name in VALID_PREDICATE_NAMES, outcome in "
                    f"{{ok, fail, skip}}); got {entry!r}"
                )
        if self.admitted and self.elimination_reason is not None:
            raise ComprehensionStateError(
                "ConstraintResult.admitted=True is inconsistent with "
                f"non-None elimination_reason={self.elimination_reason!r}"
            )
        if not self.admitted and self.elimination_reason is None:
            raise ComprehensionStateError(
                "ConstraintResult.admitted=False requires a non-None "
                "elimination_reason"
            )


@dataclass(frozen=True, slots=True)
class Elimination:
    """Structured record of one hypothesis being eliminated.

    Designed to serialise as a JSON object in ``reader_trace``.
    """

    confidence_rank: int
    predicate: str
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.confidence_rank, int) or isinstance(
            self.confidence_rank, bool
        ):
            raise ComprehensionStateError(
                "Elimination.confidence_rank must be int"
            )
        if self.predicate not in VALID_PREDICATE_NAMES:
            raise ComprehensionStateError(
                f"Elimination.predicate must be in VALID_PREDICATE_NAMES; "
                f"got {self.predicate!r}"
            )
        if not isinstance(self.reason, str) or not self.reason:
            raise ComprehensionStateError(
                "Elimination.reason must be non-empty str"
            )


# ---------------------------------------------------------------------------
# Hypothesis emitters — adapt existing candidate types
# ---------------------------------------------------------------------------


def hypothesis_from_initial(candidate: object, rank: int) -> Hypothesis:
    """Wrap a :class:`CandidateInitial` as a Phase-1 :class:`Hypothesis`.

    The candidate's per-slot tokens are not unpacked into
    ``category_assignments`` here — that wiring is Phase 3 work when
    apply_word starts threading category assignments through the reader.
    Phase 2 carries the candidate intact so downstream solver / verifier
    paths consume it unchanged.

    The ``unresolved`` tuple is empty: Phase 2 hypotheses are complete
    candidates produced by injectors, not partial reads.  Phase 3 will
    populate this with the slot names a partial hypothesis still needs.
    """
    if rank < 0 or rank >= HYPOTHESIS_CAP:
        raise ComprehensionStateError(
            f"hypothesis_from_initial: rank must be in [0, "
            f"{HYPOTHESIS_CAP}); got {rank}"
        )
    return Hypothesis(
        candidate=candidate,
        category_assignments=(),
        constraint_state=(),
        confidence_rank=rank,
        unresolved=(),
    )


def hypothesis_from_operation(candidate: object, rank: int) -> Hypothesis:
    """Wrap a :class:`CandidateOperation` as a Phase-1 :class:`Hypothesis`.

    See :func:`hypothesis_from_initial` for the structural notes;
    behaviorally identical, kept as a separate function so the call site
    documents intent and Phase 3 can specialise per type without
    rewriting the caller.
    """
    if rank < 0 or rank >= HYPOTHESIS_CAP:
        raise ComprehensionStateError(
            f"hypothesis_from_operation: rank must be in [0, "
            f"{HYPOTHESIS_CAP}); got {rank}"
        )
    return Hypothesis(
        candidate=candidate,
        category_assignments=(),
        constraint_state=(),
        confidence_rank=rank,
        unresolved=(),
    )


# ---------------------------------------------------------------------------
# Constraint checks — decomposed sub-checks per predicate
# ---------------------------------------------------------------------------


def _check_initial(candidate: object) -> ConstraintResult:
    """Run :func:`_initial_admissible` as decomposed sub-checks.

    Returns a :class:`ConstraintResult` carrying the specific predicate
    that failed (first-failure short-circuit, matching today's
    behavior).  When ``composition_evidence`` is non-None the candidate
    is a registry-gated composition and routes to
    :func:`_check_composed_initial` instead, mirroring the existing
    dispatch in ``_initial_admissible``.
    """
    # Lazy imports to avoid circular dependency on math_candidate_graph
    # → math_roundtrip → here.
    from generate.math_roundtrip import (
        _tokens, _token_in, _value_grounds, _unit_grounds,
    )

    ic = candidate
    composition_evidence = getattr(ic, "composition_evidence", None)
    if composition_evidence is not None:
        return _check_composed_initial(ic)

    matched_anchor = getattr(ic, "matched_anchor", None)
    matched_value_token = getattr(ic, "matched_value_token", None)
    matched_unit_token = getattr(ic, "matched_unit_token", None)
    matched_entity_token = getattr(ic, "matched_entity_token", None)
    source_span = getattr(ic, "source_span", None)
    if not all(
        isinstance(x, str) for x in
        (matched_anchor, matched_value_token, matched_unit_token,
         matched_entity_token, source_span)
    ):
        # Defensive — the candidate does not have the expected shape.
        # Treat as failed under a synthetic predicate that the trace
        # consumer can recognise.
        return ConstraintResult(
            admitted=False,
            predicates_run=(("initial.anchor_grounds", "fail"),),
            elimination_reason="candidate does not expose initial-shape slots",
        )

    # All five fields are confirmed str by the guard above.
    matched_anchor = cast(str, matched_anchor)
    matched_value_token = cast(str, matched_value_token)
    matched_unit_token = cast(str, matched_unit_token)
    matched_entity_token = cast(str, matched_entity_token)
    source_span = cast(str, source_span)
    haystack = _tokens(source_span)
    run: list[tuple[str, Literal["ok", "fail", "skip"]]] = []

    if not _token_in(matched_anchor, haystack):
        run.append(("initial.anchor_grounds", "fail"))
        return ConstraintResult(
            admitted=False,
            predicates_run=tuple(run),
            elimination_reason=(
                f"matched_anchor {matched_anchor!r} does not appear in "
                f"source tokens"
            ),
        )
    run.append(("initial.anchor_grounds", "ok"))

    if not _value_grounds(matched_value_token, haystack):
        run.append(("initial.value_grounds", "fail"))
        return ConstraintResult(
            admitted=False,
            predicates_run=tuple(run),
            elimination_reason=(
                f"matched_value_token {matched_value_token!r} does not "
                f"ground in source"
            ),
        )
    run.append(("initial.value_grounds", "ok"))

    if not _unit_grounds(matched_unit_token, source_span, haystack):
        run.append(("initial.unit_grounds", "fail"))
        return ConstraintResult(
            admitted=False,
            predicates_run=tuple(run),
            elimination_reason=(
                f"matched_unit_token {matched_unit_token!r} does not "
                f"ground in source"
            ),
        )
    run.append(("initial.unit_grounds", "ok"))

    # Multi-word entity: every word must ground (mirrors existing logic).
    for tok in matched_entity_token.split():
        if not _token_in(tok, haystack):
            run.append(("initial.entity_grounds", "fail"))
            return ConstraintResult(
                admitted=False,
                predicates_run=tuple(run),
                elimination_reason=(
                    f"matched_entity_token component {tok!r} does not "
                    f"appear in source tokens"
                ),
            )
    run.append(("initial.entity_grounds", "ok"))

    return ConstraintResult(
        admitted=True,
        predicates_run=tuple(run),
        elimination_reason=None,
    )


def _check_composed_initial(candidate: object) -> ConstraintResult:
    """Decomposed version of :func:`_composed_initial_admissible`.

    Verifies composition_evidence schema completeness, then that each
    input token grounds, optional currency symbol presence, and the
    matched_entity_token is populated.  Matches the existing
    short-circuit-on-first-failure semantics.
    """
    from generate.math_roundtrip import _tokens, _token_in

    ev = getattr(candidate, "composition_evidence", None)
    if not ev:
        return ConstraintResult(
            admitted=False,
            predicates_run=(("composed_initial.evidence_complete", "fail"),),
            elimination_reason="composition_evidence is empty",
        )

    required = {"composition_shape", "input_tokens", "entity_source"}
    if not required.issubset(ev.keys()):
        return ConstraintResult(
            admitted=False,
            predicates_run=(("composed_initial.evidence_complete", "fail"),),
            elimination_reason=(
                f"composition_evidence missing required keys: "
                f"{sorted(required - set(ev.keys()))}"
            ),
        )

    run: list[tuple[str, Literal["ok", "fail", "skip"]]] = [
        ("composed_initial.evidence_complete", "ok")
    ]

    source_span = getattr(candidate, "source_span", "") or ""
    haystack = _tokens(source_span)
    input_tokens_field = ev["input_tokens"]
    input_tokens: list[str] = (
        str(input_tokens_field).split("|") if input_tokens_field else []
    )
    if not input_tokens:
        run.append(("composed_initial.input_tokens_ground", "fail"))
        return ConstraintResult(
            admitted=False,
            predicates_run=tuple(run),
            elimination_reason="composition_evidence.input_tokens is empty",
        )
    for tok in input_tokens:
        if not _token_in(tok, haystack):
            run.append(("composed_initial.input_tokens_ground", "fail"))
            return ConstraintResult(
                admitted=False,
                predicates_run=tuple(run),
                elimination_reason=(
                    f"composition input token {tok!r} does not ground "
                    f"in source"
                ),
            )
    run.append(("composed_initial.input_tokens_ground", "ok"))

    currency_symbol = ev.get("currency_symbol")
    if currency_symbol:
        if currency_symbol not in source_span:
            run.append(("composed_initial.currency_symbol_present", "fail"))
            return ConstraintResult(
                admitted=False,
                predicates_run=tuple(run),
                elimination_reason=(
                    f"composition currency_symbol {currency_symbol!r} "
                    f"not present in source"
                ),
            )
        run.append(("composed_initial.currency_symbol_present", "ok"))
    else:
        run.append(("composed_initial.currency_symbol_present", "skip"))

    matched_entity_token = getattr(candidate, "matched_entity_token", "")
    if not matched_entity_token or not matched_entity_token.strip():
        run.append(("composed_initial.entity_token_present", "fail"))
        return ConstraintResult(
            admitted=False,
            predicates_run=tuple(run),
            elimination_reason="composition matched_entity_token is empty",
        )
    run.append(("composed_initial.entity_token_present", "ok"))

    return ConstraintResult(
        admitted=True,
        predicates_run=tuple(run),
        elimination_reason=None,
    )


def _check_operation(candidate: object) -> ConstraintResult:
    """Run :func:`roundtrip_admissible` as decomposed sub-checks.

    Mirrors the existing short-circuit-on-first-failure semantics.  Each
    sub-check populates the predicates_run trace so the eliminator can
    record exactly which predicate the candidate failed.
    """
    from generate.math_problem_graph import Comparison, Quantity, Rate
    from generate.math_roundtrip import (
        KIND_TO_VERBS,
        _tokens, _token_in, _value_grounds, _unit_grounds,
    )

    op = getattr(candidate, "op", None)
    if op is None:
        return ConstraintResult(
            admitted=False,
            predicates_run=(("operation.verb_registered", "fail"),),
            elimination_reason="candidate.op is None",
        )

    matched_verb = getattr(candidate, "matched_verb", "")
    source_span = getattr(candidate, "source_span", "")
    haystack = _tokens(source_span)

    run: list[tuple[str, Literal["ok", "fail", "skip"]]] = []

    valid_verbs = KIND_TO_VERBS.get(op.kind)
    if valid_verbs is None or matched_verb.lower() not in valid_verbs:
        run.append(("operation.verb_registered", "fail"))
        return ConstraintResult(
            admitted=False,
            predicates_run=tuple(run),
            elimination_reason=(
                f"matched_verb {matched_verb!r} not registered for op.kind "
                f"{op.kind!r}"
            ),
        )
    run.append(("operation.verb_registered", "ok"))

    if not _token_in(matched_verb, haystack):
        run.append(("operation.verb_grounds", "fail"))
        return ConstraintResult(
            admitted=False,
            predicates_run=tuple(run),
            elimination_reason=(
                f"matched_verb {matched_verb!r} does not appear in source"
            ),
        )
    run.append(("operation.verb_grounds", "ok"))

    matched_actor_token = getattr(candidate, "matched_actor_token", "")
    if not _token_in(matched_actor_token, haystack):
        run.append(("operation.actor_grounds", "fail"))
        return ConstraintResult(
            admitted=False,
            predicates_run=tuple(run),
            elimination_reason=(
                f"matched_actor_token {matched_actor_token!r} does not "
                f"appear in source"
            ),
        )
    run.append(("operation.actor_grounds", "ok"))

    matched_value_token = getattr(candidate, "matched_value_token", "")
    if op.kind == "compare_multiplicative" and matched_value_token == matched_verb:
        run.append(("operation.value_grounds", "skip"))
    elif not _value_grounds(matched_value_token, haystack):
        run.append(("operation.value_grounds", "fail"))
        return ConstraintResult(
            admitted=False,
            predicates_run=tuple(run),
            elimination_reason=(
                f"matched_value_token {matched_value_token!r} does not "
                f"ground in source"
            ),
        )
    else:
        run.append(("operation.value_grounds", "ok"))

    matched_unit_token = getattr(candidate, "matched_unit_token", "")
    if matched_unit_token:
        if not _unit_grounds(matched_unit_token, source_span, haystack):
            run.append(("operation.unit_grounds", "fail"))
            return ConstraintResult(
                admitted=False,
                predicates_run=tuple(run),
                elimination_reason=(
                    f"matched_unit_token {matched_unit_token!r} does not "
                    f"ground in source"
                ),
            )
        run.append(("operation.unit_grounds", "ok"))
    else:
        if not isinstance(op.operand, Comparison):
            run.append(("operation.unit_grounds", "fail"))
            return ConstraintResult(
                admitted=False,
                predicates_run=tuple(run),
                elimination_reason=(
                    "matched_unit_token is empty but operand is not a "
                    "Comparison (only comparisons may omit unit)"
                ),
            )
        run.append(("operation.unit_grounds", "skip"))

    matched_target_token = getattr(candidate, "matched_target_token", None)
    if matched_target_token is not None:
        if not _token_in(matched_target_token, haystack):
            run.append(("operation.target_grounds", "fail"))
            return ConstraintResult(
                admitted=False,
                predicates_run=tuple(run),
                elimination_reason=(
                    f"matched_target_token {matched_target_token!r} does "
                    f"not appear in source"
                ),
            )
        run.append(("operation.target_grounds", "ok"))
    else:
        run.append(("operation.target_grounds", "skip"))

    matched_reference_actor_token = getattr(
        candidate, "matched_reference_actor_token", None
    )
    if matched_reference_actor_token is not None:
        if not _token_in(matched_reference_actor_token, haystack):
            run.append(("operation.reference_actor_grounds", "fail"))
            return ConstraintResult(
                admitted=False,
                predicates_run=tuple(run),
                elimination_reason=(
                    f"matched_reference_actor_token "
                    f"{matched_reference_actor_token!r} does not appear "
                    f"in source"
                ),
            )
        run.append(("operation.reference_actor_grounds", "ok"))
    else:
        run.append(("operation.reference_actor_grounds", "skip"))

    # Operand shape consistency (mirrors roundtrip_admissible step 8).
    if op.kind == "apply_rate":
        if not isinstance(op.operand, Rate):
            run.append(("operation.operand_shape_consistent", "fail"))
            return ConstraintResult(
                admitted=False,
                predicates_run=tuple(run),
                elimination_reason=(
                    "op.kind='apply_rate' requires Rate operand; got "
                    f"{type(op.operand).__name__}"
                ),
            )
        run.append(("operation.operand_shape_consistent", "ok"))
        if not _token_in(op.operand.denominator_unit, haystack):
            run.append(("operation.rate_denominator_grounds", "fail"))
            return ConstraintResult(
                admitted=False,
                predicates_run=tuple(run),
                elimination_reason=(
                    f"Rate.denominator_unit "
                    f"{op.operand.denominator_unit!r} does not ground"
                ),
            )
        run.append(("operation.rate_denominator_grounds", "ok"))
    elif op.kind in ("compare_additive", "compare_multiplicative"):
        if not isinstance(op.operand, Comparison):
            run.append(("operation.operand_shape_consistent", "fail"))
            return ConstraintResult(
                admitted=False,
                predicates_run=tuple(run),
                elimination_reason=(
                    f"op.kind={op.kind!r} requires Comparison operand; got "
                    f"{type(op.operand).__name__}"
                ),
            )
        run.append(("operation.operand_shape_consistent", "ok"))
    else:
        if not isinstance(op.operand, Quantity):
            run.append(("operation.operand_shape_consistent", "fail"))
            return ConstraintResult(
                admitted=False,
                predicates_run=tuple(run),
                elimination_reason=(
                    f"op.kind={op.kind!r} requires Quantity operand; got "
                    f"{type(op.operand).__name__}"
                ),
            )
        run.append(("operation.operand_shape_consistent", "ok"))

    return ConstraintResult(
        admitted=True,
        predicates_run=tuple(run),
        elimination_reason=None,
    )


def check_constraints(hypothesis: Hypothesis) -> ConstraintResult:
    """Run the appropriate admissibility predicate on a hypothesis.

    Dispatches on the candidate type:
      - :class:`CandidateInitial` → :func:`_check_initial` (which itself
        dispatches to :func:`_check_composed_initial` when
        ``composition_evidence`` is non-None).
      - :class:`CandidateOperation` → :func:`_check_operation`.
      - Other types refuse cleanly — Phase 2 only knows the two
        existing candidate types.
    """
    from generate.math_candidate_parser import CandidateInitial
    from generate.math_roundtrip import CandidateOperation

    candidate = hypothesis.candidate
    if isinstance(candidate, CandidateInitial):
        return _check_initial(candidate)
    if isinstance(candidate, CandidateOperation):
        return _check_operation(candidate)
    return ConstraintResult(
        admitted=False,
        predicates_run=(("initial.anchor_grounds", "fail"),),
        elimination_reason=(
            f"unknown candidate type {type(candidate).__name__!r}; "
            "Phase 2 supports CandidateInitial and CandidateOperation only"
        ),
    )


# ---------------------------------------------------------------------------
# Bulk elimination
# ---------------------------------------------------------------------------


def eliminate_violating(
    hypotheses: tuple[Hypothesis, ...],
) -> tuple[tuple[Hypothesis, ...], tuple[Elimination, ...]]:
    """Apply :func:`check_constraints` to each hypothesis.

    Returns ``(survivors, eliminations)``. Survivors preserve their
    original :attr:`Hypothesis.confidence_rank` values **except** that
    the surviving set is re-densified — if hypothesis 0 is eliminated
    and hypothesis 1 survives, the survivor's rank stays at 1 in the
    elimination record but the returned tuple is renumbered to be
    dense-from-zero so :class:`ProblemReadingState` accepts it.

    Eliminations carry the ORIGINAL confidence_rank so the trace event
    points at the right candidate.
    """
    surviving_pairs: list[tuple[int, Hypothesis]] = []
    eliminations: list[Elimination] = []
    for hyp in hypotheses:
        result = check_constraints(hyp)
        if result.admitted:
            surviving_pairs.append((hyp.confidence_rank, hyp))
        else:
            # elimination_reason is non-None when admitted=False (post_init
            # invariant); pick the first failing predicate.
            failing = next(
                (name for name, outcome in result.predicates_run
                 if outcome == "fail"),
                "initial.anchor_grounds",
            )
            eliminations.append(
                Elimination(
                    confidence_rank=hyp.confidence_rank,
                    predicate=failing,
                    reason=result.elimination_reason or "unspecified",
                )
            )

    # Re-densify ranks so the survivors satisfy the
    # ProblemReadingState.open_hypotheses post_init invariant.
    densified: list[Hypothesis] = []
    surviving_pairs.sort(key=lambda x: x[0])
    for new_rank, (_, hyp) in enumerate(surviving_pairs):
        if new_rank == hyp.confidence_rank:
            densified.append(hyp)
        else:
            densified.append(
                Hypothesis(
                    candidate=hyp.candidate,
                    category_assignments=hyp.category_assignments,
                    constraint_state=hyp.constraint_state,
                    confidence_rank=new_rank,
                    unresolved=hyp.unresolved,
                )
            )
    return tuple(densified), tuple(eliminations)


__all__ = [
    "VALID_PREDICATE_NAMES",
    "ConstraintResult",
    "Elimination",
    "check_constraints",
    "eliminate_violating",
    "hypothesis_from_initial",
    "hypothesis_from_operation",
]
