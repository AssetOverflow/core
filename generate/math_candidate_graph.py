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
from typing import TYPE_CHECKING, Final, Union

if TYPE_CHECKING:
    from core.config import RuntimeConfig

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


def _load_ratified_registry_or_empty() -> tuple:
    """Return the ratified recognizer registry, or () on any failure.

    ADR-0163 §Phase D — the candidate-graph consults this registry
    before refusing on an empty per-statement choice list.  Failures
    (e.g. malformed log) MUST NOT regress wrong=0; in that case the
    registry is treated as empty and the existing refusal path runs
    unchanged.  The registry projection itself is in-process cached
    by ``generate.recognizer_registry``.
    """
    try:
        from generate.recognizer_registry import load_ratified_registry
        return load_ratified_registry()
    except Exception:  # pragma: no cover — defensive: empty registry on any I/O error
        return ()

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
    # ADR-0164 Phase 1 — reader trace events (JSON-encoded strings).
    # Each element is a JSON object carrying {"layer", "phase", "outcome", ...}.
    # Empty tuple when comprehension_reader_questions flag is False (default).
    # Deferred: full integration with chat/telemetry.py JSONL sink is a
    # follow-up; these events are available for tests and delta-report analysis.
    reader_trace: tuple[str, ...] = ()

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


def _filtered_question_choices(
    sentence: str, problem_text: str | None = None
) -> list[CandidateUnknown]:
    """Return all admissible question candidates after the question-
    specific structural check.

    ADR-0163.D.3 — conditional-prefix recovery.  When the existing
    parser returns no candidates AND the question begins with an
    "If X, ..." conditional prefix, strip the prefix and re-try.
    This admits the ``nested_question_target`` shape that the bare
    regex misses (11 of 38 GSM8K train_sample post-Phase-D question
    refusals share this shape).  Skip-only safety: if the stripped
    question still produces no admissible candidate, refuse as before.

    ADR-0163.D.4 — ``problem_text`` is the full problem text used by
    the new question-grammar extensions for pronoun-entity resolution
    (Pattern C).  When None, pronoun-entity branches refuse.
    """
    out: list[CandidateUnknown] = []
    for qc in extract_question_candidates(sentence, problem_text):
        if _question_admissible(qc):
            out.append(qc)
    if not out:
        stripped = _strip_conditional_prefix(sentence)
        if stripped is not None and stripped != sentence:
            for qc in extract_question_candidates(stripped, problem_text):
                if _question_admissible(qc):
                    out.append(qc)
    return out[:MAX_CANDIDATES_PER_SENTENCE]


_CONDITIONAL_PREFIX_RE: re.Pattern[str] = re.compile(
    r"^\s*[Ii]f\s+.+?,\s+(?=[A-Za-z])",
)


def _strip_conditional_prefix(sentence: str) -> str | None:
    """ADR-0163.D.3 — remove an ``If X, `` conditional prefix.

    Returns the suffix with its first letter upper-cased when the
    pattern matches; returns ``None`` if no conditional prefix is
    present.  The transformation is deterministic and pure.
    """
    m = _CONDITIONAL_PREFIX_RE.match(sentence)
    if m is None:
        return None
    suffix = sentence[m.end():]
    if not suffix:
        return None
    # Existing question regexes expect a leading "How" (case-insensitive
    # in pattern); upper-case the first character to mirror the
    # canonical surface form so the deterministic match holds.
    return suffix[0].upper() + suffix[1:]


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
# ADR-0164 Phase 1 — comprehension reader dispatch helper
# ---------------------------------------------------------------------------

def _try_reader_for_question(
    question_sentence: str,
    per_sentence_choices: list[list[SentenceChoice]],
    statement_sentence_count: int,
    trace_out: list[str],
) -> list[CandidateUnknown] | None:
    """Invoke the Phase-1 comprehension reader for the question sentence.

    Returns a list with one CandidateUnknown on reader admission, or None
    when the reader refuses (caller falls through to the regex parser).

    Appends a JSON-encoded trace event to ``trace_out`` on every invocation
    (admit or fallthrough_to_regex).

    This function is the hybrid-dispatch core for ADR-0164 Phase 1.  The
    fallthrough path (reader refusal → regex) is intentional and must never
    raise: the reader is purely additive at Phase 1.
    """
    try:
        from generate.comprehension.lifecycle_runtime_adapter import (
            build_problem_state_from_candidates,
            invoke_reader_for_question,
            make_admit_trace_event,
            make_fallthrough_trace_event,
            project_to_candidate_unknown,
        )
    except ImportError:
        return None  # adapter not available — fall through silently

    # Flatten per_sentence_choices to a single list for state construction.
    # Take the first choice per sentence (deterministic: tiebreaker already ran).
    flat: list[SentenceChoice] = [choices[0] for choices in per_sentence_choices if choices]
    try:
        problem_state = build_problem_state_from_candidates(flat, statement_sentence_count)
    except Exception:
        return None  # construction failure → fall through

    result = invoke_reader_for_question(question_sentence, problem_state)
    if isinstance(result, tuple):
        slot, canonical_unit = result
        trace_out.append(make_admit_trace_event(slot, canonical_unit))
        candidate = project_to_candidate_unknown(
            slot, canonical_unit, question_sentence, problem_state
        )
        if candidate is not None and _question_admissible(candidate):
            return [candidate]
        # Reader admitted but projection failed or failed admissibility.
        # Do NOT fall through to regex (the reader's admission is authoritative
        # on what it could parse; if projection fails it's a structural gap,
        # not a reason to let the regex guess differently).
        return None
    else:
        # ReaderRefusal — fall through to regex.
        from generate.comprehension.state import ReaderRefusal
        if isinstance(result, ReaderRefusal):
            trace_out.append(make_fallthrough_trace_event(result))
        return None


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

def parse_and_solve(
    text: str,
    config: "RuntimeConfig | None" = None,
) -> CandidateGraphResult:
    """End-to-end: parse text via candidate-graph topology, solve each
    admissible branch, apply decision rule.

    Args:
        text: The problem text to parse.
        config: Optional :class:`core.config.RuntimeConfig`.  When None,
            defaults to flag-OFF behaviour (byte-identical to today).
            Pass ``RuntimeConfig(comprehension_reader_questions=True)`` to
            activate the ADR-0164 Phase-1 comprehension reader for question
            sentences.

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
    - When the comprehension reader is active (flag ON), a reader refusal
      falls through to the existing regex parser — the reader is purely
      additive.  A reader admission that produces wrong > 0 cannot occur
      because the same admissibility gate, solver, and verifier run
      downstream of the reader as they run today.
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
    #
    # ADR-0163 §Phase D — ratified-recognizer admission guard.
    # Before refusing on an empty choice list, consult the ratified
    # RecognizerSpec registry.  When the registry recognizes the
    # statement, drop it from per_sentence_choices entirely instead of
    # refusing: a recognized statement contributes ZERO math state so
    # the Cartesian product remains identical to "this statement was
    # never there," preserving wrong=0 by construction.  Downstream
    # consumption of parsed_anchors (turning recognized rate/temporal
    # surfaces into solver state) is Phase E follow-up work.
    _ratified_registry = _load_ratified_registry_or_empty()
    per_sentence_choices: list[list[SentenceChoice]] = []
    for s in statement_sentences:
        choices = _filtered_statement_choices(s)
        if not choices:
            if _ratified_registry:
                from generate.recognizer_match import match as _recognizer_match
                recognizer_match = _recognizer_match(s, _ratified_registry)
                if recognizer_match is not None:
                    # ADR-0163.D.2 — per-category anchor injection.
                    # The matcher may carry populated parsed_anchors that
                    # an injector turns into typed solver primitives
                    # (CandidateInitial / CandidateOperation).  When the
                    # injector returns a non-empty tuple, the recognized
                    # statement contributes math state to the Cartesian
                    # product the same way the existing parser's output
                    # does — and every constructed candidate has already
                    # passed _initial_admissible upstream of this call.
                    # When the injector returns () (skip-only fallback —
                    # the round-2 default and the only path for v1
                    # categories without an injector), the statement is
                    # dropped from per_sentence_choices, preserving the
                    # wrong=0 safety net by construction.
                    from generate.recognizer_anchor_inject import (
                        inject_from_match,
                    )
                    injected = inject_from_match(recognizer_match, s)
                    if injected:
                        admitted: list[SentenceChoice] = [
                            c for c in injected if _initial_admissible(c)
                        ]
                        if len(admitted) == len(injected) and admitted:
                            per_sentence_choices.append(
                                _collapse_per_sentence_ties(admitted)
                            )
                            continue
                    # Recognized but no injection — skip the sentence, do
                    # not refuse.  Identical to the round-2 skip-only
                    # wiring; preserves wrong=0 because zero math state
                    # is contributed.
                    continue
            return CandidateGraphResult(
                answer=None, selected_graph=None,
                refusal_reason=f"no admissible candidate for statement: {s!r}",
                branches_enumerated=0, branches_admissible=0,
            )
        per_sentence_choices.append(_collapse_per_sentence_ties(choices))

    # ADR-0164 Phase 1 — comprehension reader hybrid dispatch.
    # When comprehension_reader_questions is True, try the reader FIRST.
    # On reader admission, use the reader's CandidateUnknown; on refusal,
    # fall through to the existing regex question parser (Pattern A/B/C).
    # The reader is purely additive: a refusal MUST NOT prevent admission
    # by the regex parser.
    reader_trace: list[str] = []
    reader_question_choices: list[CandidateUnknown] | None = None
    _use_reader = (
        config is not None and config.comprehension_reader_questions
    )
    if _use_reader:
        reader_question_choices = _try_reader_for_question(
            question_sentences[0],
            per_sentence_choices,
            len(statement_sentences),
            reader_trace,
        )

    # Fall through to the regex parser when the flag is off OR the reader
    # refused on the question sentence.
    if reader_question_choices is not None:
        question_choices = reader_question_choices
    else:
        question_choices = _filtered_question_choices(question_sentences[0], text)

    if not question_choices:
        return CandidateGraphResult(
            answer=None, selected_graph=None,
            refusal_reason=(
                f"no admissible candidate for question: "
                f"{question_sentences[0]!r}"
            ),
            branches_enumerated=0, branches_admissible=0,
            reader_trace=tuple(reader_trace),
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
            reader_trace=tuple(reader_trace),
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
            reader_trace=tuple(reader_trace),
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
            reader_trace=tuple(reader_trace),
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
        reader_trace=tuple(reader_trace),
    )
