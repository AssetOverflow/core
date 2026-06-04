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

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import product
from typing import Final, Union

from generate.comprehension.state import Hypothesis
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
from generate.math_completeness import uncovered_quantities
from generate.derivation.r1_reconstruction import reconstruct_r1_total
from generate.math_roundtrip import CandidateOperation, roundtrip_admissible
from generate.math_solver import SolveError, solve


MAX_TOTAL_BRANCHES: Final[int] = 64
"""Hard cap on Cartesian-product branch enumeration; exceeding refuses."""


def _try_r1_reconstruction(
    text: str,
    *,
    existing_trace: tuple[str, ...],
) -> CandidateGraphResult | None:
    """Attempt the narrow R1 typed reconstruction path.

    Returns None when the text has no R1 signal.  A non-admitted R1 attempt is
    still returned so its deterministic refusal evidence can be surfaced in the
    reader trace while preserving the caller's refusal posture.
    """
    r1 = reconstruct_r1_total(text)
    if r1 is None:
        return None
    trace = (*existing_trace, *r1.reader_trace)
    if r1.is_admitted:
        assert r1.answer is not None
        return CandidateGraphResult(
            answer=r1.answer,
            selected_graph=r1.graph,
            refusal_reason=None,
            branches_enumerated=1,
            branches_admissible=1,
            reader_trace=trace,
        )
    return CandidateGraphResult(
        answer=None,
        selected_graph=None,
        refusal_reason=f"r1_reconstruction: {r1.refusal_reason}",
        branches_enumerated=0,
        branches_admissible=0,
        reader_trace=trace,
    )


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
    # ADR-0191 — the originating branch (statement choices + question
    # choice).  Carries per-candidate consumed-token provenance the
    # completeness guard needs; the MathProblemGraph itself discards it.
    branch: tuple["SentenceChoice | CandidateUnknown", ...] = ()


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
    # Reader trace events (JSON-encoded strings).  Each element is a JSON
    # object carrying {"layer", "phase", "outcome", ...}.  Carries the
    # ADR-0174 Phase-2 constraint-elimination events from the recognizer
    # path.  Deferred: full integration with chat/telemetry.py JSONL sink.
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
    slot set (entity, anchor, value, unit).

    RAT-1 — when ``ic.composition_evidence`` is non-None the candidate
    is a registry-gated composition (ADR-0169); the derived value /
    canonical unit / cross-sentence entity will not literally appear in
    source_span. Branch to :func:`_composed_initial_admissible` which
    checks the composition INPUT tokens (count, amount, currency
    symbol) ground instead. The composition_shape is gated upstream by
    the composition_registry consult in
    :func:`generate.recognizer_anchor_inject.inject_from_match`.
    """
    if ic.composition_evidence is not None:
        return _composed_initial_admissible(ic)
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


def _composed_initial_admissible(ic: CandidateInitial) -> bool:
    """RAT-1 — admissibility gate for registry-gated composition candidates.

    Preserves wrong=0 by requiring each composition INPUT token to
    ground in source_span. The derived value (e.g. ``1200`` from
    ``3 × 400``, or ``150`` from ``100 + 50``) and canonicalized unit
    are NOT required to be literal because they are deterministic
    arithmetic over grounded inputs.

    composition_evidence schema (all keys required):
      - composition_shape: str   — the surface_pattern (registry-gated upstream)
      - input_tokens:     str    — pipe-separated list of literal tokens
                                   (e.g. "3|400" for multiplicative,
                                    "100|50" for additive)
      - entity_source:    str    — "same_sentence" | "prior_sentence"
    Optional:
      - currency_symbol:  str    — substring required in source_span (for currency shapes)

    Each input_token must ground in source_span tokens.
    matched_entity_token must be non-empty (matcher's binding is
    trusted; cross-unit/cross-sentence refusals happen upstream).
    """
    from generate.math_roundtrip import _tokens, _token_in

    ev = ic.composition_evidence
    if not ev:
        return False
    required = {"composition_shape", "input_tokens", "entity_source"}
    if not required.issubset(ev.keys()):
        return False

    haystack = _tokens(ic.source_span)
    input_tokens = ev["input_tokens"].split("|") if ev["input_tokens"] else []
    if not input_tokens:
        return False
    for tok in input_tokens:
        if not _token_in(tok, haystack):
            return False
    currency_symbol = ev.get("currency_symbol")
    if currency_symbol and currency_symbol not in ic.source_span:
        return False
    if not ic.matched_entity_token or not ic.matched_entity_token.strip():
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

def parse_and_solve(text: str, *, sealed: bool = False) -> CandidateGraphResult:
    """End-to-end: parse text via candidate-graph topology, solve each
    admissible branch, apply decision rule.

    ADR-0186 — ``sealed`` selects the sealed injector lane. The default
    ``sealed=False`` is the frozen serving path (the ``train_sample`` runner
    and serving always pass it), so the ratified serving count is byte-identical.
    ``sealed=True``
    additionally consults ``_SEALED_INJECTORS`` (the in-development W2-W5
    injectors) at the per-statement injection site below; it is used only by
    the sealed eval runner. The seal is injector eligibility, not a forked
    reader — every other reader step is identical.

    Args:
        text: The problem text to parse.

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

    ADR-0174 Phase 5a: the recognizer/candidate-graph path is the single
    canonical reader.  The flag-gated incremental-reader dispatch
    (``_try_comprehension_reader`` / ``_try_reader_for_question``) was
    retired — it admitted 0/50 on train_sample and only added a dead
    fall-through.  ``lifecycle.py`` itself survives because the ADR-0172
    contemplation corridor (``comprehension/audit.py`` →
    ``teaching/math_*``) still uses its reader surface.
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
    # ADR-0191 — preserve EVERY statement sentence before the numeric-only
    # filter below drops non-numeric ones.  The completeness guard must see
    # quantity signals carried in dropped sentences (e.g. "Jerry has twice
    # as many … as Ivan" has no digit but a multiplier the reading must
    # account for) to catch confabulations that emit a partial reading.
    all_statement_sentences = list(statement_sentences)

    # ADR-0136.S.0 — Strip context-filler sentences before any extraction.
    # A sentence with no digit and no word-number cannot introduce parseable
    # numeric state; skipping it is provably safe for wrong == 0.
    #
    # RAT-1 — but context-filler sentences DO carry proper-noun subjects
    # that downstream composition shapes (case 0019: "John adopts a dog"
    # establishes John before the composition sentence) need for
    # cross-sentence subject binding. Capture the discourse subjects
    # BEFORE filtering so the cross-sentence resolver can reach them.
    from generate.recognizer_match import extract_proper_noun_subject as _rat1_extract_subj
    _discourse_prior_subjects: dict[str, str] = {}
    _running_subject: str | None = None
    for _s in statement_sentences:
        head = _rat1_extract_subj(_s)
        if head is not None:
            _running_subject = head
        # Map this statement to the subject available BEFORE it.
        _discourse_prior_subjects[_s] = _running_subject if _running_subject and _running_subject != head else (
            _running_subject if head is None else _discourse_prior_subjects.get(_s)
        )
    # Re-walk to set the strict "prior" (head from EARLIER sentences only).
    _running_subject = None
    _discourse_prior_subjects = {}
    for _s in statement_sentences:
        _discourse_prior_subjects[_s] = _running_subject
        head = _rat1_extract_subj(_s)
        if head is not None:
            _running_subject = head

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

    # ── DISABLED (2026-06-04): serving promotion bridges removed ──────────────
    # The FIRST real sealed measurement (1,319 held-out GSM8K, decrypted by the
    # operator) showed the product-promotion bridge (ADR-0195) commits 0 correct /
    # 5 WRONG on held-out — a `wrong=0` breach that was invisible because the
    # working metric was the 50-case train sample the bridges were tuned to.
    # Bisection: disabling `resolve_promotable_product` restores sealed 0/0/1319.
    # `resolve_promotable_goal_residual` (ADR-0207 §5 step 2) is 0/0 on held-out
    # (inert) — removed too, since its only effect was inflating the train proxy.
    # Both production modules remain in generate/derivation/; only their serving
    # promotion is unwired, until a gate is built that is proven `wrong=0` on the
    # SEALED set (not the train sample). Restoring `wrong=0` is the prime directive
    # and outranks the train-sample "correct" the bridges produced.
    # ──────────────────────────────────────────────────────────────────────────

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
    # ME-2 — track a running proper-noun subject across sentences so the
    # recognizer matcher can resolve cross-sentence composition shapes
    # (e.g. case 0019: "John adopts a dog... 3 vet appointments at
    # $400 each"). Update AFTER each statement is processed (the current
    # statement's subject is not yet trusted when matching that same
    # statement; only prior sentences contribute).
    _prior_subject: str | None = None
    # ADR-0174 Phase 2 — statement-scoped trace of constraint eliminations.
    # Merged into the question-stage reader_trace below so the consumer
    # sees both per-sentence eliminations (Phase 2) and reader events
    # (Phase 1, ADR-0164) in one stream.
    _statement_trace: list[str] = []
    for s_idx, s in enumerate(statement_sentences):
        # RAT-1 — prefer the discourse-level prior (which sees context-filler
        # sentences like "John adopts a dog from a shelter"); fall back to
        # the in-loop running subject when discourse map has no entry.
        _effective_prior = _discourse_prior_subjects.get(s, _prior_subject) or _prior_subject
        choices = _filtered_statement_choices(s)
        if not choices:
            if _ratified_registry:
                from generate.recognizer_match import (
                    extract_proper_noun_subject as _extract_subj,
                    match as _recognizer_match,
                )
                recognizer_match = _recognizer_match(
                    s, _ratified_registry, prior_subject=_effective_prior
                )
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
                    injected = inject_from_match(recognizer_match, s, sealed=sealed)
                    # ADR-0174 Phase 3 — lookback pronoun resolution.
                    # When the matcher tagged any anchor with
                    # ``requires_pronoun_resolution``, the injected
                    # candidates carry the pronoun as actor/entity and
                    # are held until lookback either binds them to a
                    # discourse antecedent or drops them.  The
                    # discourse map (_discourse_prior_subjects /
                    # _prior_subject) is consulted in the same
                    # precedence as ME-2 cross-sentence binding so
                    # behaviour is consistent across recognizer
                    # categories.  When no antecedent is available,
                    # we drop the candidates (refusal-preferring;
                    # preserves wrong=0).
                    if injected and any(
                        isinstance(a, Mapping)
                        and a.get("requires_pronoun_resolution")
                        for a in recognizer_match.parsed_anchors
                    ):
                        from generate.comprehension.lookback import (
                            PronounResolution,
                            reevaluate,
                        )
                        from generate.comprehension.constraint_propagation import (
                            hypothesis_from_initial as _hyp_from_initial,
                            hypothesis_from_operation as _hyp_from_operation,
                        )

                        # Extract the held pronoun (the matcher
                        # guarantees a single subject_role across the
                        # anchor set for discrete_count_statement v1).
                        _held_pronoun: str | None = None
                        for a in recognizer_match.parsed_anchors:
                            if (
                                isinstance(a, Mapping)
                                and a.get("requires_pronoun_resolution")
                            ):
                                _sr = a.get("subject_role")
                                if isinstance(_sr, str):
                                    _held_pronoun = _sr
                                    break

                        _antecedent = _effective_prior
                        # ADR-0174 Phase 3a — multi-actor pronoun
                        # ambiguity defense.  When the problem has
                        # more than one distinct proper-noun subject
                        # in prior context, picking the most-recent
                        # is a guess (e.g. "Alice has 5. Bob has 3.
                        # She buys 2." — "She" should bind to Alice
                        # by gender but the discourse map returns
                        # Bob).  No safety net downstream would catch
                        # a wrong attribution (single-binding
                        # emission → no multi-branch disagreement;
                        # verifier re-derives the same wrong graph).
                        # Refuse rather than guess.  Surfaced by
                        # 2026-05-28 Phase 1-3a lookback review;
                        # see project-adr-0174-multi-actor-pronoun-hazard
                        # memory and CLAUDE.md §Lookback Review
                        # Discipline.
                        _distinct_priors = {
                            v for v in _discourse_prior_subjects.values()
                            if v is not None
                        }
                        if _prior_subject is not None:
                            _distinct_priors.add(_prior_subject)
                        _multi_actor_ambiguous = len(_distinct_priors) > 1
                        if _held_pronoun is None or not _antecedent:
                            # No resolution path available — drop the
                            # held candidates and log the lookback
                            # event so the trace records why.
                            _statement_trace.append(json.dumps({
                                "layer": "lookback",
                                "phase": 3,
                                "outcome": "no_antecedent",
                                "pronoun": _held_pronoun or "<missing>",
                                "sentence_index": s_idx,
                            }, sort_keys=True))
                            injected = ()
                        elif _multi_actor_ambiguous:
                            # ADR-0174 Phase 4 — invoke in-loop
                            # contemplate before declaring ambiguity.
                            # When the gendered-names pack uniquely
                            # binds the pronoun to one antecedent,
                            # admit via the resolved binding. When
                            # contemplate returns None (ambiguous
                            # evidence, missing names, epicene
                            # pronoun), the Phase 3a defense fires
                            # cleanly — refusal-preferring discipline.
                            from generate.comprehension.contemplate import (
                                contemplate,
                            )
                            from generate.comprehension.state import (
                                ProblemReadingState as _PRS,
                            )
                            # Phase 4 invocation requires Hypothesis
                            # residuals so contemplate can match its
                            # contract. Build the held hypotheses
                            # here (mirrors the post-resolution path
                            # below) so contemplate has well-typed
                            # input even though Phase 4a only uses
                            # candidate_antecedents.
                            _ps_stub = _PRS(
                                entity_registry=(),
                                accumulated_initial_state=(),
                                accumulated_operations=(),
                                unknown_target_slot=None,
                                pronoun_resolution_history=(),
                                sentence_index=s_idx,
                                source_text_offset=0,
                            )
                            _ant_tuple = tuple(sorted(_distinct_priors))
                            _residual: tuple[Hypothesis, ...] = tuple(
                                Hypothesis(
                                    candidate=(ant,),  # sentinel; Phase 4a uses candidate_antecedents
                                    category_assignments=(),
                                    constraint_state=(),
                                    confidence_rank=i,
                                    unresolved=("actor_pronoun",),
                                )
                                for i, ant in enumerate(_ant_tuple)
                            )
                            _resolution = contemplate(
                                _ps_stub, _residual,
                                pronoun_hint=_held_pronoun,
                                candidate_antecedents=_ant_tuple,
                            )
                            if _resolution is not None and _resolution.source == "pack":
                                # Pack adapter encoded the chosen
                                # antecedent in evidence[-1] as
                                # ("en_core_names_v1", "chosen=<name>").
                                _chosen: str | None = None
                                for _src, _fact in _resolution.evidence:
                                    if _fact.startswith("chosen="):
                                        _chosen = _fact.split("=", 1)[1]
                                        break
                                if _chosen is not None:
                                    _statement_trace.append(json.dumps({
                                        "layer": "contemplate",
                                        "phase": 4,
                                        "outcome": "resolved",
                                        "source": _resolution.source,
                                        "pronoun": _held_pronoun,
                                        "resolved_to": _chosen,
                                        "evidence": [list(e) for e in _resolution.evidence],
                                        "sub_question": _resolution.sub_question,
                                        "sentence_index": s_idx,
                                    }, sort_keys=True))
                                    # Override _antecedent for the
                                    # downstream PronounResolution
                                    # path below; the multi-actor
                                    # branch becomes admit-via-evidence
                                    # instead of refuse-on-ambiguity.
                                    _antecedent = _chosen
                                    _multi_actor_ambiguous = False  # admit path proceeds
                            if _multi_actor_ambiguous:
                                # Contemplate didn't disambiguate —
                                # original Phase 3a defense fires.
                                _statement_trace.append(json.dumps({
                                    "layer": "contemplate",
                                    "phase": 4,
                                    "outcome": "ambiguous_unresolvable",
                                    "pronoun": _held_pronoun,
                                    "candidate_antecedents": sorted(_distinct_priors),
                                    "sentence_index": s_idx,
                                }, sort_keys=True))
                                _statement_trace.append(json.dumps({
                                    "layer": "lookback",
                                    "phase": 3,
                                    "outcome": "no_antecedent_ambiguous",
                                    "pronoun": _held_pronoun,
                                    "candidate_antecedents": sorted(_distinct_priors),
                                    "sentence_index": s_idx,
                                }, sort_keys=True))
                                injected = ()
                        else:
                            _refinement = PronounResolution(
                                pronoun=_held_pronoun,
                                resolved_to=_antecedent,
                                evidence_source=(
                                    "discourse_prior_subjects"
                                    if s in _discourse_prior_subjects
                                    else "running_subject"
                                ),
                            )
                            _resolved: list[object] = []
                            _all_resolved = True
                            for _rank, _c in enumerate(injected):
                                if isinstance(_c, CandidateInitial):
                                    _base = _hyp_from_initial(_c, _rank)
                                elif isinstance(_c, CandidateOperation):
                                    _base = _hyp_from_operation(_c, _rank)
                                else:
                                    _all_resolved = False
                                    break
                                _held = Hypothesis(
                                    candidate=_base.candidate,
                                    category_assignments=_base.category_assignments,
                                    constraint_state=_base.constraint_state,
                                    confidence_rank=_base.confidence_rank,
                                    unresolved=("actor_pronoun",),
                                )
                                _result = reevaluate(_held, _refinement)
                                _statement_trace.append(json.dumps({
                                    "layer": "lookback",
                                    "phase": 3,
                                    "outcome": "admitted" if _result.refined else "eliminated",
                                    "pronoun": _held_pronoun,
                                    "resolved_to": _antecedent,
                                    "confidence_rank": _rank,
                                    "evidence_source": _refinement.evidence_source,
                                    "sentence_index": s_idx,
                                }, sort_keys=True))
                                if _result.refined is None:
                                    _all_resolved = False
                                    break
                                _resolved.append(_result.refined.candidate)  # type: ignore[arg-type]
                            if _all_resolved and _resolved:
                                injected = tuple(_resolved)
                            else:
                                injected = ()
                    if injected:
                        # ADR-0174 Phase 2 — hypothesis-based admission
                        # with structured elimination tracing.  Each
                        # injected candidate becomes a Hypothesis with
                        # confidence_rank == emission order; the
                        # constraint propagator runs the same predicates
                        # _initial_admissible / roundtrip_admissible run
                        # today (decomposed into sub-checks) and returns
                        # (survivors, eliminations).  Eliminations append
                        # as JSON trace events to reader_trace so the
                        # operator can see WHICH predicate eliminated the
                        # candidate, not just that admission failed.
                        # Admission semantics are byte-equivalent to the
                        # pre-Phase-2 inline loop: a candidate survives
                        # here iff it survived the predicate dispatch
                        # there.
                        from generate.comprehension.constraint_propagation import (
                            eliminate_violating,
                            hypothesis_from_initial,
                            hypothesis_from_operation,
                        )

                        hyps_in: list[Hypothesis] = []
                        for rank, c in enumerate(injected):
                            if isinstance(c, CandidateInitial):
                                hyps_in.append(
                                    hypothesis_from_initial(c, rank)
                                )
                            elif isinstance(c, CandidateOperation):
                                hyps_in.append(
                                    hypothesis_from_operation(c, rank)
                                )
                        survivors, eliminations = eliminate_violating(
                            tuple(hyps_in)
                        )
                        for elim in eliminations:
                            _statement_trace.append(json.dumps({
                                "layer": "constraint_propagation",
                                "phase": 2,
                                "outcome": "eliminated",
                                "confidence_rank": elim.confidence_rank,
                                "predicate": elim.predicate,
                                "reason": elim.reason,
                                "sentence_index": s_idx,
                            }, sort_keys=True))
                        admitted: list[SentenceChoice] = [
                            h.candidate for h in survivors  # type: ignore[misc]
                        ]
                        if len(admitted) == len(injected) and admitted:
                            per_sentence_choices.append(
                                _collapse_per_sentence_ties(admitted)
                            )
                            continue
                    # Recognized but no injection — REFUSE.
                    #
                    # The earlier "skip-only" reasoning ("zero math state
                    # contributed → wrong=0 preserved by construction") is
                    # wrong in the same way the case 0050 hazard was wrong:
                    # silently dropping a recognized math statement is
                    # equivalent to admitting an incomplete graph at the
                    # problem level — the solver answers from whatever
                    # remains, which is not the right answer to the input
                    # problem.  ADR-0167 / Brief 11 §"correct-count greed"
                    # established this principle on the reader path; this
                    # commit extends it to the recognizer path.
                    #
                    # If the recognizer matches but the injector cannot
                    # produce typed solver state, the right answer is
                    # "I don't know" — i.e. refuse.  When an injector is
                    # added that handles this shape, this branch becomes
                    # dead and can be retired.
                    r1_result = _try_r1_reconstruction(
                        text,
                        existing_trace=tuple(_statement_trace),
                    )
                    if r1_result is not None and r1_result.is_admitted:
                        return r1_result
                    if r1_result is not None:
                        _statement_trace = list(r1_result.reader_trace)
                    return CandidateGraphResult(
                        answer=None, selected_graph=None,
                        refusal_reason=(
                            "recognizer matched but produced no injection "
                            f"for statement: {s!r} "
                            f"(category={recognizer_match.category.value})"
                        ),
                        branches_enumerated=0, branches_admissible=0,
                        # ADR-0174 Phase 3a — preserve statement-stage
                        # trace events on early refusal so consumers see
                        # WHY admission failed (lookback no_antecedent,
                        # constraint_propagation eliminations, etc.).
                        reader_trace=tuple(_statement_trace),
                    )
            r1_result = _try_r1_reconstruction(
                text,
                existing_trace=tuple(_statement_trace),
            )
            if r1_result is not None and r1_result.is_admitted:
                return r1_result
            if r1_result is not None:
                _statement_trace = list(r1_result.reader_trace)
            return CandidateGraphResult(
                answer=None, selected_graph=None,
                refusal_reason=f"no admissible candidate for statement: {s!r}",
                branches_enumerated=0, branches_admissible=0,
                reader_trace=tuple(_statement_trace),
            )
        per_sentence_choices.append(_collapse_per_sentence_ties(choices))
        # ME-2 — update prior_subject AFTER this sentence is processed.
        # The current sentence's head proper-noun is now eligible to be
        # the cross-sentence subject for the next sentence's composition
        # match.
        from generate.recognizer_match import (
            extract_proper_noun_subject as _extract_subj_for_update,
        )
        _head = _extract_subj_for_update(s)
        if _head is not None:
            _prior_subject = _head

    # ADR-0174 Phase 2 — seed reader_trace with statement-stage
    # constraint-propagation events so consumers still see the Phase-2
    # elimination events in one ordered stream.  (ADR-0174 Phase 5a: the
    # flag-gated question-reader dispatch was retired; the recognizer
    # question parser is the single path.)
    reader_trace: list[str] = list(_statement_trace)
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
            CandidateGraphAnswer(
                graph=graph,
                answer=trace.answer_value,
                branch=(*stmt_choices, q_choice),
            )
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

    # ADR-0191 — completeness guard (the missing admissibility leg).
    # The branch grounded + round-tripped, but that only proves the
    # quantities it DID read are real — not that it read ALL of them.
    # If any source quantity (across every statement sentence + the
    # question) is absent from the chosen reading, emitting its answer
    # would confabulate a partial reading.  Refuse instead (wrong==0).
    # Refusal-only: this can never turn a refusal into an answer, so it
    # cannot create a wrong answer — only remove confabulations.
    uncovered = uncovered_quantities(
        statement_sentences=all_statement_sentences,
        question_text=question_sentences[0],
        branch=chosen.branch,
    )
    if uncovered:
        r1_result = _try_r1_reconstruction(
            text,
            existing_trace=tuple(reader_trace),
        )
        if r1_result is not None and r1_result.is_admitted:
            return r1_result
        if r1_result is not None:
            reader_trace = list(r1_result.reader_trace)
        return CandidateGraphResult(
            answer=None, selected_graph=None,
            refusal_reason=(
                "incomplete reading: source quantities "
                f"{sorted(uncovered)} not consumed by the solved graph"
            ),
            branches_enumerated=branches_enumerated,
            branches_admissible=len(admissible),
            reader_trace=tuple(reader_trace),
        )

    return CandidateGraphResult(
        answer=chosen.answer,
        selected_graph=chosen.graph,
        refusal_reason=None,
        branches_enumerated=branches_enumerated,
        branches_admissible=len(admissible),
        reader_trace=tuple(reader_trace),
    )
