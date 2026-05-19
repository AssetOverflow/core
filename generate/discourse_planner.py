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
from generate.intent import DialogueIntent, IntentTag


@unique
class ResponseMode(Enum):
    """Presentation-depth axis, orthogonal to ``IntentTag``.

    A request like "Explain truth" vs "Tell me about truth" carries the
    same ``IntentTag`` (DEFINITION/NARRATIVE) but a different mode.
    Keeping mode separate from intent prevents corrupting the semantic
    enum with presentation concerns (same lesson as ADR-0049's
    syntactic subject extraction).
    """

    BRIEF = "brief"
    EXPLAIN = "explain"
    WALKTHROUGH = "walkthrough"
    PARAGRAPH = "paragraph"
    EXAMPLE = "example"


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


def plan_discourse(
    intent: DialogueIntent,
    mode: ResponseMode,
    bundle: GroundingBundle,
) -> DiscoursePlan:
    """Pure planner function — contract-only signature in this landing.

    Same ``(intent, mode, bundle)`` must produce the same plan on every
    invocation: no I/O, no clock reads, no module-level mutable state.

    The implementation is intentionally deferred: a follow-up ADR will
    fill in the move-selection rules (anchor → support → relation →
    transition → closure) per ``ResponseMode``.  Landing the signature
    first locks the contract callers can target without committing to
    the heuristics that will populate it.
    """

    _ = (intent, mode, bundle)
    raise NotImplementedError(
        "plan_discourse is contract-only in this landing; "
        "move-selection rules will land in a follow-up ADR."
    )


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
]
