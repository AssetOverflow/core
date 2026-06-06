"""Relational comprehension — the first consumer of ``en_core_relational_predicates_v1``.

The COMPREHEND organ today mints type-membership and categorical/ordering/propositional
structure (see ``reader.py``). This sibling reader adds the next increment: BINARY
RELATIONS named by the relational-predicates pack's closed vocabulary
(``parent_of``, ``less_than``, ``left_of``, ``before_event`` …). It produces a
STANDARD ``Comprehension`` whose ``Relation.predicate`` IS a pack lemma, so the rest
of the spine consumes it unchanged: ``realize_comprehension`` is predicate-general
(it stores any single non-negated relation), and ``determine`` admits the closed
relational set for DIRECT entailment.

Fail-closed (wrong=0 at the comprehension layer):

  - a clause is read ONLY when it matches ``<A> is [the] <connective> <B>`` AND the
    connective's lemma is present in the LOADED pack (``pack_lemmas``). A non-matching
    surface, a negated form, a multi-word/reserved filler, or a lemma absent from the
    pack all REFUSE — never guess, never field-vote. Deterministic.
  - only the PREDICATE is closed-vocabulary; the two arguments may be OOV (arbitrary
    identifiers), grounded downstream by the OOV substrate.

Scope — ground binary relations, DIRECT reading only. NO transitive/symmetric/rule
inference: a symmetric lemma (``sibling_of``, ``equal_to``, ``adjacent_to`` …) reads
ONLY the stated direction; the converse is a sound-but-incomplete refusal at DETERMINE,
never a fabricated assertion. Negation is out of grammar (a negated surface refuses).

This reader is invoked EXPLICITLY (the pack is loaded by the caller, not default-mounted);
it does not perturb ``comprehend``'s templates or their wrong=0 tests.
"""

from __future__ import annotations

from language_packs.compiler import load_pack_entries

from generate.meaning_graph.model import (
    Entity,
    MeaningGraph,
    MeaningGraphError,
    MeaningSpan,
    Relation,
)
from generate.meaning_graph.reader import (
    Comprehension,
    Query,
    Refusal,
    _chunk,
    _Reject,
    _split_clauses,
    _split_sentences,
)

#: The pack whose closed predicate vocabulary this reader speaks.
RELATIONAL_PACK_ID = "en_core_relational_predicates_v1"

#: Surface connective (ordered tokens) -> pack predicate lemma. The ONLY surface
#: grammar this reader admits; the lemma must ALSO be present in the loaded pack
#: (fail-closed). Longest connective at a position wins (2-token before 1-token).
_CONNECTIVE_TO_LEMMA: dict[tuple[str, ...], str] = {
    # kinship
    ("parent", "of"): "parent_of",
    ("child", "of"): "child_of",
    ("sibling", "of"): "sibling_of",
    ("spouse", "of"): "spouse_of",
    # ordering / comparison
    ("less", "than"): "less_than",
    ("greater", "than"): "greater_than",
    ("equal", "to"): "equal_to",
    ("distinct", "from"): "distinct_from",
    # spatial
    ("left", "of"): "left_of",
    ("right", "of"): "right_of",
    ("inside", "of"): "inside_of",
    ("adjacent", "to"): "adjacent_to",
    # temporal
    ("before",): "before_event",
    ("after",): "after_event",
    ("during",): "during_event",
    ("overlaps",): "overlaps_event",
}

#: The closed set of predicates this reader can mint — the universe DETERMINE admits
#: for direct relational entailment. (The realized fact's predicate is one of these.)
RELATIONAL_PREDICATES = frozenset(_CONNECTIVE_TO_LEMMA.values())

#: Structural copula/article tokens stripped from an argument slot's edges. They are
#: scaffolding of the ``<A> is [the] …`` template, never part of an entity id.
_EDGE_FUNCTION_WORDS = frozenset({"is", "the"})

_MAX_CONNECTIVE_LEN = max(len(k) for k in _CONNECTIVE_TO_LEMMA)


def load_relational_pack_lemmas() -> frozenset[str]:
    """The lemma set of the loaded relational-predicates pack — the fail-closed
    authority a relational read is gated on. Loading is explicit (NOT a default
    mount); ``load_pack_entries`` is cached, so repeated calls are cheap."""
    return frozenset(entry.lemma for entry in load_pack_entries(RELATIONAL_PACK_ID))


def _strip_edges(toks: list[str]) -> list[str]:
    """Drop leading/trailing structural copula/article tokens from an argument slot."""
    out = list(toks)
    while out and out[0] in _EDGE_FUNCTION_WORDS:
        out = out[1:]
    while out and out[-1] in _EDGE_FUNCTION_WORDS:
        out = out[:-1]
    return out


def _split_around_connective(
    toks: list[str],
) -> tuple[list[str], str, list[str]] | None:
    """Find the FIRST connective (longest match at each position) -> (left, lemma,
    right). ``None`` when no connective from the closed grammar is present."""
    for i in range(len(toks)):
        for length in range(_MAX_CONNECTIVE_LEN, 0, -1):
            key = tuple(toks[i : i + length])
            lemma = _CONNECTIVE_TO_LEMMA.get(key)
            if lemma is not None:
                return toks[:i], lemma, toks[i + length :]
    return None


def comprehend_relational(
    text: str, pack_lemmas: frozenset[str], source_id: str = "input"
) -> Comprehension | Refusal:
    """Comprehend binary-relation *text* into a ``Comprehension`` over pack-named
    predicates, or a typed ``Refusal``.

    ``pack_lemmas`` is the loaded relational pack's lemma set (see
    ``load_relational_pack_lemmas``); a mapped lemma absent from it REFUSES
    (fail-closed on the pack, not on the static grammar).
    """
    if not text or not text.strip():
        return Refusal("empty")

    sentences = _split_sentences(text)
    if not sentences:
        return Refusal("empty")

    role_kind: dict[str, str] = {}
    span_for: dict[str, MeaningSpan] = {}
    relations: list[tuple[str, tuple[str, ...], MeaningSpan, bool]] = []
    queries: list[Query] = []

    def claim(entity_id: str, span: MeaningSpan) -> None:
        role_kind.setdefault(entity_id, "entity")
        span_for.setdefault(entity_id, span)

    try:
        for body, terminator, start, end in sentences:
            span = MeaningSpan(
                source_id=source_id, start=start, end=end, text=text[start:end]
            )
            is_question = terminator == "?"
            for clause in _split_clauses(body):
                _read_relational_clause(
                    clause, is_question, span, pack_lemmas, claim, relations, queries
                )
    except _Reject as rej:
        return rej.refusal

    try:
        entities = tuple(
            Entity(entity_id=eid, name=eid, span=span_for[eid], kind=role_kind[eid])
            for eid in sorted(role_kind)
        )
        graph = MeaningGraph(
            entities=entities,
            relations=tuple(
                Relation(pred, args, sp, negated)
                for pred, args, sp, negated in relations
            ),
        )
    except MeaningGraphError as exc:  # defensive — construction invariants
        return Refusal("invalid_graph", repr(exc))

    return Comprehension(meaning_graph=graph, queries=tuple(queries))


def _read_relational_clause(
    clause: str,
    question: bool,
    span: MeaningSpan,
    pack_lemmas: frozenset[str],
    claim,
    relations: list[tuple[str, tuple[str, ...], MeaningSpan, bool]],
    queries: list[Query],
) -> None:
    """Read one ``<A> is [the] <connective> <B>`` clause; mutate accumulators or REFUSE."""
    toks = clause.strip().lower().split()
    if not toks:
        raise _Reject("empty_clause", clause)
    if "is" not in toks:
        # The relational template is copular; without a copula it is not our shape.
        raise _Reject("no_relational_template", clause)

    split = _split_around_connective(toks)
    if split is None:
        raise _Reject("no_relational_template", clause)
    left, lemma, right = split

    # Fail-closed on the LOADED pack: the static grammar only maps to pack lemmas, so
    # this fires only when the caller passes a pack missing them — and it BITES if a
    # future grammar entry outruns the pack.
    if lemma not in pack_lemmas:
        raise _Reject("relational_lemma_not_in_pack", lemma)

    subject_toks = _strip_edges(left)
    object_toks = _strip_edges(right)
    if not subject_toks or not object_toks:
        raise _Reject("incomplete_relation", clause)

    # ``_chunk`` canonicalizes each slot to a reserved-free identifier (OOV-friendly)
    # and REFUSES junk / leaked function words (e.g. a negated "is not …" leaves the
    # reserved "not" in the slot -> refuse). Negation thus never reads as a positive.
    subject = _chunk(subject_toks, clause)
    obj = _chunk(object_toks, clause)
    claim(subject, span)
    claim(obj, span)

    if question:
        queries.append(Query(lemma, (subject, obj), span))
    else:
        relations.append((lemma, (subject, obj), span, False))
