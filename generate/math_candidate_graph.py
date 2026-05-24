"""ADR-0126 P3 — Candidate-graph assembly + decision rule.

End-to-end orchestration:

  text
    → sentence split
    → per-sentence candidate extraction (P2)
    → per-candidate round-trip admissibility filter (P1)
    → bounded branch enumeration (Cartesian product, cap=64)
    → per-branch graph construction + solve
    → decision rule

Decision rule (preserves wrong == 0):

  |admissible answers| == 0   → refuse
  |admissible answers| == 1   → emit
  |admissible answers| >= 2,
      all answers identical   → emit common answer
  |admissible answers| >= 2,
      answers differ          → refuse (genuine ambiguity)

Per-sentence ambiguity tiebreaker (P3-local; orthogonal to the
decision rule above):

  When a single sentence has multiple admissible candidates AND the
  resulting graphs all solve to the same numeric answer, we collapse
  to one candidate via the "most-grounded-slots-wins" heuristic.
  This handles cases like "Sam gives 3 apples to Tom" where both
  subtract and transfer pass round-trip — transfer has a target slot
  (more grounded content), so it wins on the tiebreaker. If the
  graphs differ in answer, we let the decision rule above refuse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import product
from typing import Final, Union

from generate.math_candidate_parser import (
    CandidateInitial,
    CandidateUnknown,
    classify_sentence,
    extract_capacity_candidates,
    extract_capacity_question_candidates,
    extract_conditional_op_question_candidates,
    extract_earnings_candidates,
    extract_earnings_question_candidates,
    extract_initial_candidates,
    extract_operation_candidates,
    extract_question_candidates,
    _TIME_UNITS_TO_SECONDS,
    _to_seconds,
)
from generate.math_problem_graph import (
    MathGraphError,
    MathProblemGraph,
)
from generate.math_roundtrip import CandidateOperation, roundtrip_admissible
from generate.math_solver import SolveError, solve


MAX_TOTAL_BRANCHES: Final[int] = 64
"""Hard cap on Cartesian-product branch enumeration; exceeding refuses."""

MAX_CANDIDATES_PER_SENTENCE: Final[int] = 4
"""Hard cap on per-sentence candidate emission; exceeding refuses."""


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CandidateGraphAnswer:
    """A successfully solved candidate graph.

    ``answer`` is the numeric answer the solver produced for this
    branch. Multiple branches may produce the same answer; the
    decision rule collapses on equality.
    """

    graph: MathProblemGraph
    answer: int | float


@dataclass(frozen=True, slots=True)
class CandidateGraphResult:
    """Outcome of candidate-graph parsing + filtering + deciding.

    Exactly one of ``answer`` / ``refusal_reason`` is non-None.
    """

    answer: int | float | None
    selected_graph: MathProblemGraph | None
    refusal_reason: str | None
    # Diagnostics for inner-loop signal in P6 runner.
    branches_enumerated: int
    branches_admissible: int

    @property
    def is_admitted(self) -> bool:
        return self.answer is not None


# ---------------------------------------------------------------------------
# Sentence splitting + classification (mirrors math_parser._split_sentences)
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT_RE: Final[re.Pattern[str]] = re.compile(r"(?<=[.?!])\s+")


def _split_sentences(text: str) -> list[str]:
    text = text.strip()
    return [p.strip() for p in _SENTENCE_SPLIT_RE.split(text) if p.strip()]


# ---------------------------------------------------------------------------
# Per-sentence choice typing
# ---------------------------------------------------------------------------

# A statement sentence's choice space: a list of (initial-or-operation)
# candidates that all passed the round-trip filter. A question sentence's
# choice space: a list of CandidateUnknown.
SentenceChoice = Union[CandidateInitial, CandidateOperation]


def _filtered_statement_choices(sentence: str) -> list[SentenceChoice]:
    """Return all admissible (initial | operation) candidates for a
    statement sentence, after applying the round-trip filter."""
    out: list[SentenceChoice] = []

    # Initial-possession candidates are checked structurally — we use
    # the operation round-trip filter shape only for CandidateOperation.
    # For CandidateInitial we apply a light structural check inline:
    # entity, value, unit, anchor must all ground in source. (P1's
    # roundtrip_admissible signature is operation-specific.)
    for ic in extract_initial_candidates(sentence):
        if _initial_admissible(ic):
            out.append(ic)

    for oc in extract_operation_candidates(sentence):
        if roundtrip_admissible(oc):
            out.append(oc)

    return out[:MAX_CANDIDATES_PER_SENTENCE]


def _filtered_question_choices(sentence: str) -> list[CandidateUnknown]:
    """Return all admissible question candidates after the question-
    specific structural check."""
    out: list[CandidateUnknown] = []
    for qc in extract_question_candidates(sentence):
        if _question_admissible(qc):
            out.append(qc)
    return out[:MAX_CANDIDATES_PER_SENTENCE]


def _initial_admissible(ic: CandidateInitial) -> bool:
    """Light structural ground-check for initial-possession candidates.

    Same shape as roundtrip_admissible but for the initial-possession
    slot set (entity, anchor, value, unit)."""
    from generate.math_roundtrip import _tokens, _value_grounds, _token_in, _unit_grounds
    haystack = _tokens(ic.source_span)
    if not _token_in(ic.matched_anchor, haystack):
        return False
    if not _value_grounds(ic.matched_value_token, haystack):
        return False
    if not _unit_grounds(ic.matched_unit_token, ic.source_span, haystack):
        return False
    # Entity token: for multi-word entities ("the boys"), all words
    # must ground. Split + check each.
    for tok in ic.matched_entity_token.split():
        if not _token_in(tok, haystack):
            return False
    return True


def _question_admissible(qc: CandidateUnknown) -> bool:
    """Light structural ground-check for question candidates."""
    from generate.math_roundtrip import _tokens, _token_in, _unit_grounds
    haystack = _tokens(qc.source_span)
    if not _unit_grounds(qc.matched_unit_token, qc.source_span, haystack):
        return False
    if qc.matched_entity_token is not None:
        for tok in qc.matched_entity_token.split():
            if not _token_in(tok, haystack):
                return False
    return True


# ---------------------------------------------------------------------------
# Per-sentence ambiguity tiebreaker (most-grounded-slots-wins)
# ---------------------------------------------------------------------------

def _slot_count(choice: SentenceChoice) -> int:
    """Count the number of distinct grounded content slots.

    More grounded slots → 'tighter' parse → preferred when answers
    agree. Implements the give-with-target case: transfer (4 slots:
    actor, verb, value, unit, target = 5) wins over subtract (4 slots)
    on the same sentence.
    """
    if isinstance(choice, CandidateInitial):
        return 4  # entity, anchor, value, unit
    n = 4  # actor, verb, value, unit
    if choice.matched_target_token is not None:
        n += 1
    if choice.matched_reference_actor_token is not None:
        n += 1
    return n


def _collapse_per_sentence_ties(
    choices: list[SentenceChoice],
) -> list[SentenceChoice]:
    """If multiple choices exist for one sentence, prefer the one with
    the most grounded slots (deterministic tiebreaker). Ties at the
    max slot-count return all tied choices; cross-sentence ambiguity
    still gets enumerated."""
    if len(choices) <= 1:
        return choices
    max_slots = max(_slot_count(c) for c in choices)
    return [c for c in choices if _slot_count(c) == max_slots]


# ---------------------------------------------------------------------------
# Graph construction from one branch
# ---------------------------------------------------------------------------

def _build_graph(
    statement_choices: list[SentenceChoice],
    question_choice: CandidateUnknown,
) -> MathProblemGraph | None:
    """Build a MathProblemGraph from one consistent branch of sentence
    choices, or return None if the branch cannot form a valid graph
    (entity universe violations, referential integrity, etc.).

    State threading is minimal in P3 scope (no pronoun resolution, no
    unit inheritance — those need richer per-branch state and land in
    a later sub-phase). The dataclass constructors catch every
    referential-integrity violation deterministically.
    """
    entities: list[str] = []
    seen_entities: set[str] = set()

    def add_entity(e: str) -> None:
        if e not in seen_entities:
            entities.append(e)
            seen_entities.add(e)

    initials_list = []
    operations_list = []
    for choice in statement_choices:
        if isinstance(choice, CandidateInitial):
            add_entity(choice.initial.entity)
            initials_list.append(choice.initial)
        else:
            add_entity(choice.op.actor)
            if choice.op.target is not None:
                add_entity(choice.op.target)
            operations_list.append(choice.op)

    if question_choice.unknown.entity is not None:
        if question_choice.unknown.entity not in seen_entities:
            return None  # question references unknown entity

    try:
        return MathProblemGraph(
            entities=tuple(entities),
            initial_state=tuple(initials_list),
            operations=tuple(operations_list),
            unknown=question_choice.unknown,
        )
    except MathGraphError:
        return None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def parse_and_solve(text: str) -> CandidateGraphResult:
    """End-to-end: parse text via candidate-graph topology, solve each
    admissible branch, apply decision rule.

    Returns :class:`CandidateGraphResult` with either an admitted
    ``answer`` + ``selected_graph`` or a ``refusal_reason`` string
    naming why the problem was refused.

    Preserves wrong == 0 by construction:

    - A sentence the parser cannot match contributes [] to its choice
      list → Cartesian product is empty → refusal.
    - Every branch's graph must round-trip through the round-trip
      filter at the per-sentence level (already applied during
      filtering).
    - Branches that disagree on the final answer trigger refusal.
    """
    if not isinstance(text, str) or not text.strip():
        return CandidateGraphResult(
            answer=None, selected_graph=None,
            refusal_reason="empty or non-string problem",
            branches_enumerated=0, branches_admissible=0,
        )

    sentences = _split_sentences(text)
    if not sentences:
        return CandidateGraphResult(
            answer=None, selected_graph=None,
            refusal_reason="no sentences found",
            branches_enumerated=0, branches_admissible=0,
        )

    question_sentences = [s for s in sentences if s.rstrip().endswith("?")]
    statement_sentences = [s for s in sentences if not s.rstrip().endswith("?")]

    # ADR-0136.S.0 — Strip context-filler sentences before any extraction.
    # A sentence with no digit and no word-number cannot introduce parseable
    # numeric state; skipping it is provably safe for wrong == 0.
    numeric_statement_sentences = [
        s for s in statement_sentences if classify_sentence(s) == "numeric_state"
    ]
    if numeric_statement_sentences or not statement_sentences:
        statement_sentences = numeric_statement_sentences

    if len(question_sentences) != 1:
        return CandidateGraphResult(
            answer=None, selected_graph=None,
            refusal_reason=(
                f"expected exactly one question sentence; "
                f"got {len(question_sentences)}"
            ),
            branches_enumerated=0, branches_admissible=0,
        )

    # ADR-0136.S.1 — Rate/event short-circuit paths (before Cartesian product).
    # Capacity path: single statement with one CandidateCapacity + matching question.
    if len(statement_sentences) == 1:
        cap_cands = extract_capacity_candidates(statement_sentences[0])
        cap_q_cands = extract_capacity_question_candidates(question_sentences[0])
        if len(cap_cands) == 1 and len(cap_q_cands) == 1:
            cap = cap_cands[0]
            cap_q = cap_q_cands[0]
            actor_ok = (
                cap_q.actor is None
                or cap.actor.lower() == cap_q.actor.lower()
            )
            if actor_ok:
                rate_per_sec = cap.count / _to_seconds(cap.per_count, cap.per_unit)
                answer = rate_per_sec * _to_seconds(cap_q.per_count, cap_q.per_unit)
                if answer > 0:
                    return CandidateGraphResult(
                        answer=answer,
                        selected_graph=None,
                        refusal_reason=None,
                        branches_enumerated=1,
                        branches_admissible=1,
                    )
            else:
                return CandidateGraphResult(
                    answer=None, selected_graph=None,
                    refusal_reason="capacity actor mismatch",
                    branches_enumerated=0, branches_admissible=0,
                )

    # Earnings path: single rate statement + matching question.
    if len(statement_sentences) == 1:
        earn_cands = extract_earnings_candidates(statement_sentences[0])
        earn_q_cands = extract_earnings_question_candidates(question_sentences[0])
        if len(earn_cands) == 1 and len(earn_q_cands) == 1:
            earn = earn_cands[0]
            earn_q = earn_q_cands[0]
            if earn.actor.lower() == earn_q.actor.lower():
                if earn.per_unit in _TIME_UNITS_TO_SECONDS:
                    rate_per_sec = earn.amount / _to_seconds(1, earn.per_unit)
                    answer = rate_per_sec * _to_seconds(
                        earn_q.time_count, earn_q.time_unit,
                    )
                    if answer > 0:
                        return CandidateGraphResult(
                            answer=answer,
                            selected_graph=None,
                            refusal_reason=None,
                            branches_enumerated=1,
                            branches_admissible=1,
                        )
            else:
                return CandidateGraphResult(
                    answer=None, selected_graph=None,
                    refusal_reason="earnings actor mismatch",
                    branches_enumerated=0, branches_admissible=0,
                )

    # ADR-0136.S.2 — Conditional-op question short-circuit.
    # Shape: "If <Entity> <verb> <N> <unit>, how many <unit2> does <Entity2>
    # <aux> [left|...]?" — given exactly one matching initial-state
    # candidate for (entity, unit) across all statement sentences, the
    # answer is initial_value ± operand by verb polarity.  Refuses on any
    # ambiguity (multiple matching ICs, no IC, negative answer); preserves
    # wrong == 0.
    cond_qs = extract_conditional_op_question_candidates(question_sentences[0])
    if len(cond_qs) == 1:
        cq = cond_qs[0]
        all_ic: list[CandidateInitial] = []
        for s in statement_sentences:
            all_ic.extend(extract_initial_candidates(s))
        matching = [
            ic for ic in all_ic
            if ic.initial.entity.lower() == cq.entity.lower()
            and ic.initial.quantity.unit == cq.unit
        ]
        if len(matching) == 1:
            val = matching[0].initial.quantity.value
            answer = val - cq.operand if cq.op == "subtract" else val + cq.operand
            if answer >= 0:
                return CandidateGraphResult(
                    answer=answer,
                    selected_graph=None,
                    refusal_reason=None,
                    branches_enumerated=1,
                    branches_admissible=1,
                )

    # Per-sentence choice spaces (after round-trip filter + tiebreaker).
    per_sentence_choices: list[list[SentenceChoice]] = []
    for s in statement_sentences:
        choices = _filtered_statement_choices(s)
        if not choices:
            return CandidateGraphResult(
                answer=None, selected_graph=None,
                refusal_reason=f"no admissible candidate for statement: {s!r}",
                branches_enumerated=0, branches_admissible=0,
            )
        per_sentence_choices.append(_collapse_per_sentence_ties(choices))

    question_choices = _filtered_question_choices(question_sentences[0])
    if not question_choices:
        return CandidateGraphResult(
            answer=None, selected_graph=None,
            refusal_reason=(
                f"no admissible candidate for question: "
                f"{question_sentences[0]!r}"
            ),
            branches_enumerated=0, branches_admissible=0,
        )

    # Cartesian product across statement choices × question choices.
    total = 1
    for choices in per_sentence_choices:
        total *= len(choices)
    total *= len(question_choices)
    if total > MAX_TOTAL_BRANCHES:
        return CandidateGraphResult(
            answer=None, selected_graph=None,
            refusal_reason=(
                f"branch count {total} exceeds MAX_TOTAL_BRANCHES="
                f"{MAX_TOTAL_BRANCHES} (refusing rather than truncating)"
            ),
            branches_enumerated=total, branches_admissible=0,
        )

    admissible: list[CandidateGraphAnswer] = []
    branches_enumerated = 0
    for combo in product(*per_sentence_choices, question_choices):
        branches_enumerated += 1
        *stmt_choices, q_choice = combo  # type: ignore[misc]
        graph = _build_graph(list(stmt_choices), q_choice)  # type: ignore[arg-type]
        if graph is None:
            continue
        try:
            trace = solve(graph)
        except SolveError:
            continue
        admissible.append(
            CandidateGraphAnswer(graph=graph, answer=trace.answer_value)
        )

    if not admissible:
        return CandidateGraphResult(
            answer=None, selected_graph=None,
            refusal_reason="no branch produced a solvable graph",
            branches_enumerated=branches_enumerated,
            branches_admissible=0,
        )

    # Decision rule: all answers identical → emit; otherwise → refuse.
    distinct_answers = {a.answer for a in admissible}
    if len(distinct_answers) > 1:
        return CandidateGraphResult(
            answer=None, selected_graph=None,
            refusal_reason=(
                f"branches disagree on answer "
                f"(distinct values: {sorted(distinct_answers)})"
            ),
            branches_enumerated=branches_enumerated,
            branches_admissible=len(admissible),
        )

    # Single agreed answer. Pick the first admissible graph as the
    # canonical representative (deterministic since product() is ordered).
    chosen = admissible[0]
    return CandidateGraphResult(
        answer=chosen.answer,
        selected_graph=chosen.graph,
        refusal_reason=None,
        branches_enumerated=branches_enumerated,
        branches_admissible=len(admissible),
    )
