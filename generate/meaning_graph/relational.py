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

  - a clause is read ONLY by one of two CLOSED surfaces: the copula-connective grammar
    ``<A> is [the] <connective> <B>`` (the copula sitting STRUCTURALLY adjacent to the
    connective), OR the closed finite-verb surface ``<A> overlaps <B>`` /
    ``Does <A> overlap <B>?`` (no copula; ``overlaps_event`` ONLY — see
    ``_read_finite_verb_clause``). In BOTH the lemma must be present in the LOADED pack
    (``pack_lemmas``) AND neither argument slot may carry leftover relational/reserved
    vocabulary or an adverb modifier. A non-matching surface, a dangling copula, a
    connective WITHOUT its copula ("Monday before Friday."), a negated form, an
    adverb-modified overlap ("A nearly overlaps B"), an argument slot holding a connective
    token (a trailing qualifier like "… of Dan during school" — unparsed structure, NOT an
    entity), or a lemma absent from the pack all REFUSE — never guess, never field-vote.
    Deterministic.
  - only the PREDICATE is closed-vocabulary; the two arguments may be OOV (arbitrary
    identifiers), grounded downstream by the OOV substrate. A clean multi-word entity
    ("north station") canonicalizes per the join contract; an argument that still holds
    relational structure refuses rather than fabricate a compound entity.

Scope — this reader grounds stated binary relations in the STATED DIRECTION only; it
performs no inference itself. DETERMINE then applies declared relational algebra over the
realized facts — ONE-HOP inverse/converse pairs and pack-declared symmetric predicates
(``INVERSE_OF`` / ``SYMMETRIC_PREDICATES``), AND SOUND TRANSITIVE CLOSURE over the
declared strict-order predicates (``TRANSITIVE_PREDICATES`` — ``less_than`` /
``greater_than`` / ``before_event`` / ``after_event``) — so a symmetric lemma's converse,
an inverse pair, and a same-predicate strict-order chain NOW determine soundly. Negation
(out of grammar — a negated surface refuses) and closed-world falsehood remain out of
scope.

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


#: TRANSITIVE strict-order predicates: ``p(a, b) ∧ p(b, c) ⊨ p(a, c)``. DETERMINE may
#: close these — and ONLY these — transitively over their OWN realized edges (never
#: composing with inverse/symmetric/other-predicate edges; that mixing stays one-hop).
#: CLOSED and default-OFF: a predicate is transitive ONLY if listed here. Restricted to
#: STRICT ORDERS whose transitivity is sound by their order semantics — numeric comparison
#: (``less_than`` / ``greater_than``) and event precedence (``before_event`` /
#: ``after_event``). DELIBERATELY EXCLUDED (each would be UNSOUND or needs a proof this
#: slice lacks): ``sibling_of`` / ``spouse_of`` (symmetric, NOT transitive),
#: ``parent_of`` / ``child_of`` (``parent ∘ parent`` = grandparent ≠ parent), the spatial
#: ``left_of`` / ``right_of`` and containment ``inside_of`` / ``during_event`` (need an
#: explicit shared-frame / total-order proof). A test pins every member to
#: ``RELATIONAL_PREDICATES`` AND asserts the excluded predicates stay out.
TRANSITIVE_PREDICATES: frozenset[str] = frozenset({
    "less_than", "greater_than", "before_event", "after_event",
})


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

# --------------------------------------------------------------------------- #
# Finite-verb surface (B3) — a verb-form relation with NO copula. CLOSED and
# default-off, kept SEPARATE from the copula-connective grammar above: the ONLY
# finite verb admitted is ``overlaps`` (``overlaps_event``). The other connectives
# (before / after / during / inside / adjacent …) are UNCHANGED — they still REQUIRE
# the copula, so "Monday before Friday." stays a refusal (no connective bypass).
# --------------------------------------------------------------------------- #

#: Declarative finite-verb token: ``<A> overlaps <B>``.
_FINITE_VERB_DECLARATIVE = "overlaps"
#: Interrogative finite-verb token (base form, with the ``does`` auxiliary):
#: ``Does <A> overlap <B>?``.
_FINITE_VERB_INTERROGATIVE = "overlap"
#: The pack lemma the finite-verb surface mints. Already in ``RELATIONAL_PREDICATES`` via
#: the ``("overlaps",)`` connective entry, so the predicate universe is UNCHANGED.
_FINITE_VERB_LEMMA = "overlaps_event"

#: Adverb / sequencing tokens that must NEVER be absorbed into a finite-verb argument
#: slot. A finite-verb GUARD, not a general grammar: an adverb-modified or sequenced
#: overlap REFUSES rather than fabricate an entity (``a_nearly``, ``b_then_c``). These are
#: NOT in ``reader._RESERVED``, so ``_chunk`` would otherwise silently absorb them — the
#: exact wrong=0 hazard the adversarial audit flagged.
_FINITE_VERB_MODIFIERS = frozenset(
    {"nearly", "completely", "partially", "mostly", "barely", "then"}
)


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


def _read_finite_verb_clause(
    toks: list[str],
    question: bool,
    pack_lemmas: frozenset[str],
    span: MeaningSpan,
    claim,
    relations: list[tuple[str, tuple[str, ...], MeaningSpan, bool]],
    queries: list[Query],
) -> bool:
    """Read the closed finite-verb surface (``overlaps_event`` ONLY), or return ``False``
    when the clause is NOT a finite-verb form (the caller then tries the copula grammar).

    Two surfaces: declarative ``<A> overlaps <B>`` and interrogative
    ``Does <A> overlap <B>?`` (base form + the ``does`` auxiliary). Once a clause IS
    recognized as a finite-verb form it EMITS or REFUSES — it never falls through, so a
    malformed overlap cannot reach the copula grammar. Fail-closed: emits only when the
    lemma is in the loaded pack AND each argument slot is, after article stripping, EXACTLY
    ONE content token. That single-token gate is the load-bearing backstop — it closes the
    UNBOUNDED adverb / negation / trailing-qualifier / second-verb class a blocklist
    cannot (so ``meeting never overlaps lunch`` does NOT become a positive
    ``overlaps_event(meeting_never, lunch)``). The ``_FINITE_VERB_MODIFIERS`` and
    ``_CONNECTIVE_TOKENS`` checks add precise refusal reasons for the common bare-modifier
    / second-verb slots; ``_chunk`` then validates the token. Scoped to ``overlaps`` only,
    so the other connectives keep requiring the copula.
    """
    if question:
        # interrogative ``does <A> overlap <B>`` (the '?' terminator is already stripped).
        if not toks or toks[0] != "does" or _FINITE_VERB_INTERROGATIVE not in toks[1:]:
            return False  # not the finite-verb query form — fall through
        verb_idx = toks.index(_FINITE_VERB_INTERROGATIVE, 1)
        left, right = toks[1:verb_idx], toks[verb_idx + 1 :]
    else:
        # declarative ``<A> overlaps <B>``.
        if _FINITE_VERB_DECLARATIVE not in toks:
            return False  # not the finite-verb declarative form — fall through
        verb_idx = toks.index(_FINITE_VERB_DECLARATIVE)
        left, right = toks[:verb_idx], toks[verb_idx + 1 :]

    # From here the clause IS a finite-verb form — emit or REFUSE, never fall through.
    if _FINITE_VERB_LEMMA not in pack_lemmas:
        raise _Reject("relational_lemma_not_in_pack", _FINITE_VERB_LEMMA)

    subject_toks = _strip_article_edges(left)
    object_toks = _strip_article_edges(right)
    if not subject_toks or not object_toks:
        raise _Reject("incomplete_relation", " ".join(toks))

    slot_toks = (*subject_toks, *object_toks)
    # adverb / sequencing guard — a precise refusal for the common modifiers when one is a
    # BARE slot ("Nearly overlaps dawn."); these are NOT in reader._RESERVED.
    if any(t in _FINITE_VERB_MODIFIERS for t in slot_toks):
        raise _Reject("finite_verb_modifier", " ".join(toks))
    # leftover relational structure (a second finite verb / any connective token), reusing
    # the copula path's fabrication net: "A overlaps B overlaps C", trailing qualifiers.
    if any(t in _CONNECTIVE_TOKENS for t in slot_toks):
        raise _Reject("extra_relational_structure", " ".join(toks))

    # POSITIVE fail-closed slot gate — the backstop a blocklist cannot provide. Each
    # finite-verb slot must be EXACTLY ONE content token (after article stripping). An
    # enumerated adverb/negation list is UNBOUNDED and leaks ("almost", "sometimes",
    # "never", a trailing qualifier "lunch today", a second verb "overlap"): the
    # adversarial audit found each glued silently into a fabricated id (e.g.
    # ``overlaps_event(meeting_never, lunch)`` — a negated sentence committed as a POSITIVE
    # belief). Requiring a single token closes the whole class — any extra token leaves a
    # 2+-token slot and REFUSES. Multi-word entities in the finite-verb surface are
    # deferred (they need a positive content lexicon, which OOV entities preclude).
    if len(subject_toks) != 1 or len(object_toks) != 1:
        raise _Reject("finite_verb_unclean_slot", " ".join(toks))

    # _chunk canonicalizes and validates the single token (rejects a non-identifier).
    subject = _chunk(subject_toks, " ".join(toks))
    obj = _chunk(object_toks, " ".join(toks))
    claim(subject, span)
    claim(obj, span)

    if question:
        queries.append(Query(_FINITE_VERB_LEMMA, (subject, obj), span))
    else:
        relations.append((_FINITE_VERB_LEMMA, (subject, obj), span, False))
    return True


def _read_relational_clause(
    clause: str,
    question: bool,
    span: MeaningSpan,
    pack_lemmas: frozenset[str],
    claim,
    relations: list[tuple[str, tuple[str, ...], MeaningSpan, bool]],
    queries: list[Query],
) -> None:
    """Read one clause into accumulators or REFUSE. Two SEPARATE branches: the closed
    finite-verb surface (``<A> overlaps <B>`` / ``Does <A> overlap <B>?``) is tried first;
    everything else falls to the copula-connective grammar (``<A> is [the] <connective>
    <B>``), which is unchanged — the other connectives still require the copula."""
    toks = clause.strip().lower().split()
    if not toks:
        raise _Reject("empty_clause", clause)

    # B3 finite-verb branch (closed: overlaps_event only). Handles the no-copula
    # finite-verb surfaces with strict fail-closed guards, and returns False (fall
    # through to the copula grammar below) ONLY when the clause is not a finite-verb form.
    if _read_finite_verb_clause(
        toks, question, pack_lemmas, span, claim, relations, queries
    ):
        return

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
