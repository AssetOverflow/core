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

  - a clause is read ONLY when it matches ``<A> is [the] <connective> <B>`` with the
    copula sitting STRUCTURALLY adjacent to the connective, AND the connective's lemma
    is present in the LOADED pack (``pack_lemmas``), AND neither argument slot carries
    leftover relational/reserved vocabulary. A non-matching surface, a dangling copula,
    a negated form, an argument slot holding a connective token (a trailing qualifier
    like "… of Dan during school" — unparsed structure, NOT an entity), or a lemma
    absent from the pack all REFUSE — never guess, never field-vote. Deterministic.
  - only the PREDICATE is closed-vocabulary; the two arguments may be OOV (arbitrary
    identifiers), grounded downstream by the OOV substrate. A clean multi-word entity
    ("north station") canonicalizes per the join contract; an argument that still holds
    relational structure refuses rather than fabricate a compound entity.

Scope — this reader grounds stated binary relations in the STATED DIRECTION only; it
performs no inference itself. DETERMINE then applies declared ONE-HOP relational algebra
over the realized facts — inverse/converse pairs and pack-declared symmetric predicates
(``INVERSE_OF`` / ``SYMMETRIC_PREDICATES``) — so a symmetric lemma's converse and an
inverse pair NOW determine soundly. Transitive relational closure, negation (out of
grammar — a negated surface refuses), and closed-world falsehood remain out of scope.

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

# --------------------------------------------------------------------------- #
# Relational algebra — the SOUND one-hop rules DETERMINE may apply. Each rule
# reads a stored fact in its OTHER lawful direction; open-world (asserts only
# True), ONE hop (no transitive chaining), structurally sound by construction.
# --------------------------------------------------------------------------- #

#: INVERSE/converse pairs: ``p(a, b)`` holds iff ``q(b, a)`` holds. The pack carries
#: no inverse metadata (only the ``graph.edge.symmetric`` tag), so the converse edges
#: are declared here as a closed table; a test pins every member to
#: ``RELATIONAL_PREDICATES`` so a typo cannot mint an unknown predicate.
_INVERSE_PAIRS: frozenset[frozenset[str]] = frozenset({
    frozenset({"parent_of", "child_of"}),
    frozenset({"less_than", "greater_than"}),
    frozenset({"left_of", "right_of"}),
    frozenset({"before_event", "after_event"}),
})

#: ``lemma -> its converse lemma`` (both directions), derived from ``_INVERSE_PAIRS``.
#: A predicate NOT in this map has no converse — so ``less_than`` is never self-inverse.
INVERSE_OF: dict[str, str] = {
    lemma: other
    for pair in _INVERSE_PAIRS
    for lemma, other in (tuple(pair), tuple(pair)[::-1])
}

#: The semantic-domain tag the relational pack uses to mark a symmetric predicate.
_SYMMETRIC_DOMAIN_TAG = "graph.edge.symmetric"

#: SYMMETRIC predicates: ``p(a, b)`` holds iff ``p(b, a)`` holds. This MIRRORS the pack
#: ontology (the ``graph.edge.symmetric`` tag, see ``load_relational_pack_symmetric``);
#: a test pins the two equal so the table can never silently diverge from the pack. A
#: predicate NOT here is asymmetric — so ``parent_of`` is never read in both directions.
SYMMETRIC_PREDICATES: frozenset[str] = frozenset({
    "sibling_of", "spouse_of", "equal_to",
    "distinct_from", "adjacent_to", "overlaps_event",
})


def load_relational_pack_symmetric() -> frozenset[str]:
    """The symmetric-predicate lemmas as DECLARED by the loaded pack ontology (the
    ``graph.edge.symmetric`` semantic-domain tag). ``SYMMETRIC_PREDICATES`` is pinned
    equal to this by a test — the pack is the source of truth, the constant is the
    runtime-cheap mirror (no per-determination pack load)."""
    return frozenset(
        entry.lemma
        for entry in load_pack_entries(RELATIONAL_PACK_ID)
        if _SYMMETRIC_DOMAIN_TAG in entry.semantic_domains
    )


#: The article stripped from an argument slot's edges ("the box" -> "box"). The
#: copula ("is") is NOT stripped here — it is enforced STRUCTURALLY (adjacent to the
#: connective) so a dangling copula ("Monday before Friday is.") cannot read as a fact.
_ARTICLE = "the"

#: Every token that participates in a connective. An argument slot must be FREE of
#: these: leftover relational vocabulary means unparsed structure (a trailing
#: qualifier like "… of Dan DURING school", a second relation), so the honest output
#: is a Refusal — not a fabricated compound entity ("dan_during_school"). Without this
#: the refusal net is accidental (it fires only when the leaked token happens to be in
#: reader._RESERVED), which is a comprehension-layer wrong=0 hole: "… of Bob during the
#: trip" refuses (article leaks) while "… of Dan during school" fabricates.
_CONNECTIVE_TOKENS = frozenset(tok for key in _CONNECTIVE_TO_LEMMA for tok in key)

_MAX_CONNECTIVE_LEN = max(len(k) for k in _CONNECTIVE_TO_LEMMA)


def load_relational_pack_lemmas() -> frozenset[str]:
    """The lemma set of the loaded relational-predicates pack — the fail-closed
    authority a relational read is gated on. Loading is explicit (NOT a default
    mount); ``load_pack_entries`` is cached, so repeated calls are cheap."""
    return frozenset(entry.lemma for entry in load_pack_entries(RELATIONAL_PACK_ID))


def _strip_article_edges(toks: list[str]) -> list[str]:
    """Drop a leading/trailing article ("the") from an argument slot — an entity id is
    never the bare article. (The copula is handled structurally, not stripped here.)"""
    out = list(toks)
    while out and out[0] == _ARTICLE:
        out = out[1:]
    while out and out[-1] == _ARTICLE:
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

    split = _split_around_connective(toks)
    if split is None:
        raise _Reject("no_relational_template", clause)
    left, lemma, right = split

    # Fail-closed on the LOADED pack: the static grammar only maps to pack lemmas, so
    # this fires only when the caller passes a pack missing them — and it BITES if a
    # future grammar entry outruns the pack.
    if lemma not in pack_lemmas:
        raise _Reject("relational_lemma_not_in_pack", lemma)

    # Structural copula: the template is ``<A> is [the] <connective> <B>``. The copula
    # must sit ADJACENT to the connective (fact: the tail of the left side; question:
    # its head) — not merely present somewhere. This refuses a dangling copula
    # ("Monday before Friday is.") and a question-shaped statement ("Is Monday before
    # Friday." with a period) rather than fabricating a fact from them.
    if question:
        if not left or left[0] != "is":
            raise _Reject("no_relational_template", clause)
        subject_toks = left[1:]
    else:
        lead = left[:-1] if (left and left[-1] == _ARTICLE) else list(left)
        if not lead or lead[-1] != "is":
            raise _Reject("no_relational_template", clause)
        subject_toks = lead[:-1]

    subject_toks = _strip_article_edges(subject_toks)
    object_toks = _strip_article_edges(right)
    if not subject_toks or not object_toks:
        raise _Reject("incomplete_relation", clause)

    # Fail-closed on leftover relational structure: an argument slot carrying a
    # connective token ("… of Dan DURING school", "X is left of Y INSIDE Z") is unparsed
    # structure, not an entity. Refuse — never chunk it into a fabricated compound
    # entity. (Without this the net is accidental, firing only on reader._RESERVED.)
    if any(t in _CONNECTIVE_TOKENS for t in (*subject_toks, *object_toks)):
        raise _Reject("extra_relational_structure", clause)

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
