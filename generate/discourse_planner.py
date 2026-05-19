"""Discourse planner contract — typed multi-move plan over grounded facts.

This module is **contract-only** in its initial landing: it defines the
frozen dataclasses, enums, canonical serialization, and the pure planner
function signature.  It has **no runtime wiring**.  Nothing in
``chat/*`` or any live ``ChatRuntime`` path imports from here yet.

Architectural rationale (see memory: feedback-design-fix-upstream-not-beside):
the existing ``realize_target`` already renders paragraph-scale output
when fed a multi-node ``PropositionGraph`` (``evals/discourse_paragraph``
passes at ``accuracy=1.0 / replay_determinism=1.0``).  The bottleneck is
upstream — ``graph_planner.build_target`` receives one-node graphs from
runtime grounding.  The fix is to lift grounding into a typed
``DiscoursePlan`` *before* the graph is built, so the realizer is fed
multi-node graphs from real runtime evidence rather than hand-authored
fixtures.

Pipeline target:

    DialogueIntent + ResponseMode + GroundingBundle
      -> DiscoursePlan          (this module's output)
      -> PropositionGraph       (graph_planner, downstream)
      -> ArticulationTarget     (existing)
      -> RealizedPlan           (existing)
      -> surface / trace_hash   (existing)

Doctrine invariants this layer must satisfy:

* Every fact carries a source tag (``pack / teaching / vault / operator``)
  — no decorative prose, no ungrounded transitions.
* Canonical serialization (alphabetical keys, separators stripped) so
  two equal plans hash to the same bytes.  This is the precondition
  for folding ``DiscoursePlan`` into ``compute_trace_hash`` in a later
  ADR — and is asserted by the companion contract tests *before* any
  trace-hash change lands.
* Frozen dataclasses with ``slots=True``; ``tuple[...]`` containers
  rather than ``list[...]``.  Equality is by value.
* The planner function is **pure**: no I/O, no module-level mutable
  state, no clock reads.  Same ``(intent, mode, bundle)`` → same plan.

Reserved for follow-up ADRs (intentionally absent here):

* Classification of ``ResponseMode`` from raw input.
* Structured grounding accessors (``pack_grounded_facts``,
  ``teaching_grounded_chains``, ``cross_pack_grounded_chains``).
* Runtime wiring behind ``RuntimeConfig.discourse_planner=False``.
* Folding ``DiscoursePlan`` serialization into ``compute_trace_hash``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum, unique

from generate.graph_planner import Relation
from generate.intent import DialogueIntent, IntentTag, ResponseMode


@unique
class FactSource(Enum):
    """Provenance of a ``GroundedFact``.

    The enum order encodes canonical precedence used by
    :func:`GroundingBundle.sorted_facts`:

        pack < teaching < vault < operator

    This mirrors in-pack precedence doctrine (ADR-0063 cross-pack
    resolver: cognition pack consulted first) and the four-tier
    inter-session memory architecture (ADR-0055: vault → audit →
    reviewed corpus → ratified packs).
    """

    PACK = "pack"
    TEACHING = "teaching"
    VAULT = "vault"
    OPERATOR = "operator"


_FACT_SOURCE_PRIORITY: dict[FactSource, int] = {
    FactSource.PACK: 0,
    FactSource.TEACHING: 1,
    FactSource.VAULT: 2,
    FactSource.OPERATOR: 3,
}


@unique
class DiscourseMoveKind(Enum):
    """Five-move vocabulary the planner draws from.

    * ``ANCHOR``     — establish the topic (always position 0).
    * ``SUPPORT``    — add a domain/definitional fact about the anchor.
    * ``RELATION``   — add a cause/verification/chain fact.
    * ``TRANSITION`` — move topic to a related node (introduces new
      ``topic`` value distinct from prior move).
    * ``CLOSURE``    — summarize endpoint or limitation.
    """

    ANCHOR = "anchor"
    SUPPORT = "support"
    RELATION = "relation"
    TRANSITION = "transition"
    CLOSURE = "closure"


@dataclass(frozen=True, slots=True)
class GroundedFact:
    """Atomic, sourced, canonically-sortable fact triple.

    ``source_id`` is the provenance pointer inside ``source``:
    pack lemma id, teaching chain id, vault entry hash, operator name.
    It is preserved in the serialization so replay can re-locate the
    fact deterministically.
    """

    subject: str
    predicate: str
    obj: str
    source: FactSource
    source_id: str

    def as_dict(self) -> dict[str, str]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.obj,
            "source": self.source.value,
            "source_id": self.source_id,
        }

    def sort_key(self) -> tuple[int, str, str, str, str]:
        return (
            _FACT_SOURCE_PRIORITY[self.source],
            self.subject,
            self.predicate,
            self.obj,
            self.source_id,
        )


@dataclass(frozen=True, slots=True)
class GroundingBundle:
    """Collection of grounded facts available to the planner.

    The bundle is *unordered* at construction time; callers obtain a
    canonical view via :meth:`sorted_facts`.  This decouples the input
    of structured grounding accessors (which may iterate corpora in any
    order) from the planner's deterministic output.
    """

    facts: tuple[GroundedFact, ...] = ()

    def sorted_facts(self) -> tuple[GroundedFact, ...]:
        return tuple(sorted(self.facts, key=GroundedFact.sort_key))

    def facts_by_source(self, source: FactSource) -> tuple[GroundedFact, ...]:
        return tuple(f for f in self.sorted_facts() if f.source is source)

    def is_empty(self) -> bool:
        return len(self.facts) == 0

    def as_dict(self) -> dict[str, object]:
        return {"facts": tuple(f.as_dict() for f in self.sorted_facts())}


@dataclass(frozen=True, slots=True)
class DiscourseMove:
    """One step in a ``DiscoursePlan``.

    ``topic``                — the subject the move is *about* right now.
    ``given``                — tuple of lemmas already established by
                               prior moves (information shared with the
                               reader).  Empty for ``ANCHOR``.
    ``new``                  — lemmas introduced by this move.
    ``relation_to_previous`` — ``None`` for ``ANCHOR``; otherwise the
                               rhetorical relation linking back to the
                               immediately-prior move.
    ``fact``                 — the ``GroundedFact`` this move surfaces;
                               ``None`` for ``CLOSURE`` moves that only
                               summarize prior facts.
    """

    kind: DiscourseMoveKind
    topic: str
    given: tuple[str, ...] = ()
    new: tuple[str, ...] = ()
    relation_to_previous: Relation | None = None
    fact: GroundedFact | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "topic": self.topic,
            "given": tuple(self.given),
            "new": tuple(self.new),
            "relation_to_previous": (
                self.relation_to_previous.value
                if self.relation_to_previous is not None
                else None
            ),
            "fact": self.fact.as_dict() if self.fact is not None else None,
        }


@dataclass(frozen=True, slots=True)
class DiscoursePlan:
    """Ordered, typed multi-move plan over a grounding bundle.

    Equality and serialization are positional in ``moves``: the planner
    is responsible for emitting moves in canonical order, and consumers
    must not reorder them.  ``as_dict`` is byte-stable across runs;
    ``to_json`` produces the exact bytes that a later ADR will hash into
    ``compute_trace_hash``.
    """

    intent: DialogueIntent
    mode: ResponseMode
    moves: tuple[DiscourseMove, ...] = field(default_factory=tuple)

    def is_empty(self) -> bool:
        return len(self.moves) == 0

    def anchor(self) -> DiscourseMove | None:
        for m in self.moves:
            if m.kind is DiscourseMoveKind.ANCHOR:
                return m
        return None

    def topics(self) -> tuple[str, ...]:
        seen: list[str] = []
        for m in self.moves:
            if m.topic not in seen:
                seen.append(m.topic)
        return tuple(seen)

    def as_dict(self) -> dict[str, object]:
        return {
            "intent": {
                "tag": self.intent.tag.value,
                "subject": self.intent.subject,
                "secondary_subject": self.intent.secondary_subject,
                "relation": self.intent.relation,
                "frame": self.intent.frame,
            },
            "mode": self.mode.value,
            "moves": tuple(m.as_dict() for m in self.moves),
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


def _move_budget(mode: ResponseMode) -> tuple[int, int]:
    """Return ``(min_moves, max_moves)`` for *mode*.

    BRIEF      → exactly 1 (ANCHOR only) so flag-on rendering of a
                 single-sentence pack-grounded surface stays at parity
                 with the existing string composer.
    EXPLAIN    → up to 3 (ANCHOR + SUPPORT + RELATION).
    PARAGRAPH  → up to 5 (ANCHOR + SUPPORT + RELATION + TRANSITION +
                 CLOSURE).
    EXAMPLE    → up to 3 (ANCHOR + RELATION + CLOSURE) — instance-shape
                 surfacing through the reverse-chain view.
    WALKTHROUGH→ deferred (needs operator-chain semantics), capped at 1.
    """

    return _MODE_BUDGETS.get(mode, (1, 1))


_MODE_BUDGETS: dict[ResponseMode, tuple[int, int]] = {
    ResponseMode.BRIEF: (1, 1),
    ResponseMode.EXPLAIN: (1, 3),
    ResponseMode.PARAGRAPH: (1, 5),
    ResponseMode.EXAMPLE: (1, 3),
    ResponseMode.WALKTHROUGH: (1, 1),
}


def _select_anchor(
    intent: DialogueIntent,
    bundle: GroundingBundle,
) -> GroundedFact | None:
    """Pick the anchor fact: a pack ``is_defined_as`` for the subject if
    available, otherwise the first canonical pack fact, otherwise the
    first canonical fact of any source.
    """

    if bundle.is_empty():
        return None
    subject = intent.subject.strip().lower()
    pack_facts = bundle.facts_by_source(FactSource.PACK)
    # Prefer is_defined_as on the subject (carries the gloss).
    for fact in pack_facts:
        if fact.subject == subject and fact.predicate == "is_defined_as":
            return fact
    # Fall back to the first canonical pack fact on the subject.
    for fact in pack_facts:
        if fact.subject == subject:
            return fact
    # Fall back to the first canonical fact of any source.
    for fact in bundle.sorted_facts():
        return fact
    return None


def _select_support(
    anchor: GroundedFact,
    bundle: GroundingBundle,
) -> GroundedFact | None:
    """Pick a SUPPORT fact distinct from the anchor: a pack ``belongs_to``
    on the anchor's subject if available.
    """

    for fact in bundle.facts_by_source(FactSource.PACK):
        if fact == anchor:
            continue
        if fact.subject != anchor.subject:
            continue
        if fact.predicate == "belongs_to":
            return fact
    # Any other pack fact on the same subject.
    for fact in bundle.facts_by_source(FactSource.PACK):
        if fact == anchor or fact.subject != anchor.subject:
            continue
        return fact
    return None


def _select_relation(
    anchor: GroundedFact,
    bundle: GroundingBundle,
    *,
    exclude: frozenset[tuple[int, str, str, str, str]] = frozenset(),
) -> GroundedFact | None:
    """Pick a RELATION fact: a teaching/cross-pack chain rooted on the
    anchor's subject.
    """

    for fact in bundle.facts_by_source(FactSource.TEACHING):
        if fact.sort_key() in exclude:
            continue
        if fact.subject == anchor.subject:
            return fact
    return None


def _select_transition(
    relation: GroundedFact,
    bundle: GroundingBundle,
    *,
    exclude: frozenset[tuple[int, str, str, str, str]] = frozenset(),
) -> GroundedFact | None:
    """Pick a TRANSITION fact: a teaching/cross-pack chain rooted on the
    RELATION's object (the topic shifts to the chain's tail).
    """

    target = relation.obj.strip().lower()
    if not target:
        return None
    for fact in bundle.facts_by_source(FactSource.TEACHING):
        if fact.sort_key() in exclude:
            continue
        if fact.subject == target:
            return fact
    # No same-source continuation — try any pack fact on the new topic
    # (lets the closure step still describe the transitioned topic).
    for fact in bundle.facts_by_source(FactSource.PACK):
        if fact.sort_key() in exclude:
            continue
        if fact.subject == target:
            return fact
    return None


def plan_discourse(
    intent: DialogueIntent,
    mode: ResponseMode,
    bundle: GroundingBundle,
) -> DiscoursePlan:
    """Deterministic discourse planner.

    Selects ordered moves from *bundle* according to *mode*'s budget
    and the canonical anchor/support/relation/transition/closure
    vocabulary.  Pure: same ``(intent, mode, bundle)`` always produces
    the same plan; no I/O, no clock reads, no module-level state.

    Empty bundles produce an empty plan rather than raising — callers
    fall through to the existing single-sentence composer path so the
    runtime is always safe to call with the flag on.

    Mode rules:

    * ``BRIEF``       — ANCHOR only.  Equivalent to today's single-
                        sentence pack-grounded surface.
    * ``EXPLAIN``     — ANCHOR + SUPPORT + RELATION (up to 3 moves).
    * ``PARAGRAPH``   — ANCHOR + SUPPORT + RELATION + TRANSITION +
                        CLOSURE (up to 5 moves).
    * ``EXAMPLE``     — ANCHOR + RELATION + CLOSURE (up to 3 moves).
                        The relation is selected from the reverse-chain
                        view via the bundle (callers supply
                        cross-pack `include_object_view=True`).
    * ``WALKTHROUGH`` — deferred to a follow-up ADR; falls back to
                        BRIEF shape so the planner is total.
    """

    if bundle.is_empty():
        return DiscoursePlan(intent=intent, mode=mode, moves=())

    anchor_fact = _select_anchor(intent, bundle)
    if anchor_fact is None:
        return DiscoursePlan(intent=intent, mode=mode, moves=())

    moves: list[DiscourseMove] = [
        DiscourseMove(
            kind=DiscourseMoveKind.ANCHOR,
            topic=anchor_fact.subject,
            given=(),
            new=(anchor_fact.subject,),
            relation_to_previous=None,
            fact=anchor_fact,
        )
    ]
    used: set[tuple[int, str, str, str, str]] = {anchor_fact.sort_key()}
    _, max_moves = _move_budget(mode)
    if max_moves <= 1 or mode is ResponseMode.WALKTHROUGH:
        return DiscoursePlan(intent=intent, mode=mode, moves=tuple(moves))

    given_lemmas: list[str] = [anchor_fact.subject]
    last_topic = anchor_fact.subject

    # SUPPORT (EXPLAIN, PARAGRAPH — not EXAMPLE which goes anchor→relation).
    if mode in (ResponseMode.EXPLAIN, ResponseMode.PARAGRAPH):
        support_fact = _select_support(anchor_fact, bundle)
        if support_fact is not None:
            moves.append(
                DiscourseMove(
                    kind=DiscourseMoveKind.SUPPORT,
                    topic=support_fact.subject,
                    given=tuple(given_lemmas),
                    new=(support_fact.obj,),
                    relation_to_previous=Relation.ELABORATION,
                    fact=support_fact,
                )
            )
            used.add(support_fact.sort_key())
            given_lemmas.append(support_fact.obj)
            last_topic = support_fact.subject
            if len(moves) >= max_moves:
                return DiscoursePlan(
                    intent=intent, mode=mode, moves=tuple(moves)
                )

    # RELATION.
    relation_fact = _select_relation(
        anchor_fact, bundle, exclude=frozenset(used)
    )
    if relation_fact is not None:
        moves.append(
            DiscourseMove(
                kind=DiscourseMoveKind.RELATION,
                topic=relation_fact.subject,
                given=tuple(given_lemmas),
                new=(relation_fact.obj,),
                relation_to_previous=Relation.CAUSE,
                fact=relation_fact,
            )
        )
        used.add(relation_fact.sort_key())
        given_lemmas.append(relation_fact.obj)
        last_topic = relation_fact.subject
        if len(moves) >= max_moves:
            return DiscoursePlan(
                intent=intent, mode=mode, moves=tuple(moves)
            )

    # TRANSITION (PARAGRAPH only).
    transition_fact: GroundedFact | None = None
    if mode is ResponseMode.PARAGRAPH and relation_fact is not None:
        transition_fact = _select_transition(
            relation_fact, bundle, exclude=frozenset(used)
        )
        if transition_fact is not None:
            moves.append(
                DiscourseMove(
                    kind=DiscourseMoveKind.TRANSITION,
                    topic=transition_fact.subject,
                    given=tuple(given_lemmas),
                    new=(transition_fact.obj,),
                    relation_to_previous=Relation.SEQUENCE,
                    fact=transition_fact,
                )
            )
            used.add(transition_fact.sort_key())
            given_lemmas.append(transition_fact.obj)
            last_topic = transition_fact.subject
            if len(moves) >= max_moves:
                return DiscoursePlan(
                    intent=intent, mode=mode, moves=tuple(moves)
                )

    # CLOSURE (PARAGRAPH, EXAMPLE) — summarize the latest topic.  No
    # new fact (fact=None); closure carries the prior given lemmas
    # forward without introducing new content.
    if mode in (ResponseMode.PARAGRAPH, ResponseMode.EXAMPLE):
        moves.append(
            DiscourseMove(
                kind=DiscourseMoveKind.CLOSURE,
                topic=last_topic,
                given=tuple(given_lemmas),
                new=(),
                relation_to_previous=Relation.ELABORATION,
                fact=None,
            )
        )

    return DiscoursePlan(intent=intent, mode=mode, moves=tuple(moves))


# ---------------------------------------------------------------------------
# Plan rendering — deterministic multi-clause surface
# ---------------------------------------------------------------------------
#
# A first renderer that joins each move's grounded fact into a clause
# using fixed connectives.  Step 5 of the discourse-planner sequencing
# uses this for the initial runtime wiring; a follow-up ADR will route
# plans through the existing PropositionGraph → realize_target spine.
#
# Every visible token in the rendered surface is either:
#   * the subject/object of a GroundedFact (verbatim from pack lexicon
#     or reviewed teaching corpus),
#   * the gloss or semantic_domains string of a pack fact (verbatim),
#   * a fixed-template connective from the table below.
# No synthesis, no LLM, no approximation.

_PREDICATE_HUMANIZE: dict[str, str] = {
    "is_defined_as": "is",
    "belongs_to": "belongs to",
}


def _humanize_predicate(predicate: str) -> str:
    return _PREDICATE_HUMANIZE.get(predicate, predicate.replace("_", " "))


def _clause_for(move: DiscourseMove) -> str | None:
    """Render a single move into one declarative clause, or ``None``
    when the move carries no fact (e.g. CLOSURE without summary fact).
    """

    fact = move.fact
    if fact is None:
        return None
    if move.kind is DiscourseMoveKind.ANCHOR and fact.predicate == "is_defined_as":
        return f"{fact.subject} is {fact.obj}"
    if fact.predicate == "is_defined_as":
        return f"{fact.subject} is {fact.obj}"
    if fact.predicate == "belongs_to":
        return f"{fact.subject} belongs to {fact.obj}"
    return f"{fact.subject} {_humanize_predicate(fact.predicate)} {fact.obj}"


_MOVE_CONNECTIVE: dict[DiscourseMoveKind, str] = {
    DiscourseMoveKind.ANCHOR: "",
    DiscourseMoveKind.SUPPORT: "Furthermore, ",
    DiscourseMoveKind.RELATION: "In turn, ",
    DiscourseMoveKind.TRANSITION: "Consequently, ",
    DiscourseMoveKind.CLOSURE: "",
}


def render_plan(plan: DiscoursePlan) -> str:
    """Render a :class:`DiscoursePlan` as a deterministic multi-clause
    surface terminated with periods.

    Empty plans render to the empty string — callers must check
    ``plan.is_empty()`` and fall back to their existing path before
    calling this.  Single-move plans render as a single sentence
    byte-equivalent to today's pack-grounded surface for the same fact.

    Determinism: ``render_plan(p) == render_plan(p)`` for any plan
    ``p``; the function is pure.
    """

    if plan.is_empty():
        return ""
    clauses: list[str] = []
    for idx, move in enumerate(plan.moves):
        clause = _clause_for(move)
        if clause is None:
            continue
        if idx == 0:
            head = clause[0].upper() + clause[1:] if clause else clause
            clauses.append(f"{head}.")
            continue
        connective = _MOVE_CONNECTIVE.get(move.kind, "")
        if connective:
            head = clause[0].lower() + clause[1:] if clause else clause
            clauses.append(f"{connective}{head}.")
        else:
            head = clause[0].upper() + clause[1:] if clause else clause
            clauses.append(f"{head}.")
    return " ".join(clauses)


__all__ = [
    "DiscourseMove",
    "DiscourseMoveKind",
    "DiscoursePlan",
    "DialogueIntent",
    "FactSource",
    "GroundedFact",
    "GroundingBundle",
    "IntentTag",
    "Relation",
    "ResponseMode",
    "plan_discourse",
    "render_plan",
]
