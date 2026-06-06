"""The general comprehension reader — disciplined Path β (Phase 2a / 2b).

Reads subject/relation/object STRUCTURE symbolically from the token sequence via
domain-agnostic templates keyed on FUNCTION WORDS + ORDER, then mints content as
``MeaningGraph`` entities/relations + ``Query`` objects. The field provably cannot
recover this structure (the holonomy fold is lossy/non-invertible — see the
α-falsification in ``docs/analysis/phase2-general-comprehension-organ-scope-2026-06-05.md``);
the field's honest role is grounding/coherence, not composition.

Refusal-first: a clause that matches no template, a filler that is not a clean
identifier, an unrecognized plural, a MULTI-WORD noun phrase, or a role conflict
all REFUSE — never guess. That keeps ``wrong=0`` at the comprehension layer
(refusal is success; a fabricated reading is the only failure).

Templates (function-word + order; domain-agnostic — the same templates read
animals, professions, geography, kin, metals, ranks):

  membership / subsumption (set_membership shapes)
    - ``<X> is a|an <Y>``            -> member(individual=X, class=Y)
    - ``the <X> is a|an <Y>``        -> member(X, Y)
    - ``is [the] <X> a|an <Y>?``     -> Query member(X, Y)
    - ``are all <Xs> <Ys>?``         -> Query subset(sing X, sing Y)

  categorical (syllogism shapes); subject/predicate are plural classes
    - ``all  <Xs> are <Ys>``         -> subset(sing X, sing Y)        (A)
    - ``no   <Xs> are <Ys>``         -> disjoint(sing X, sing Y)      (E)
    - ``some <Xs> are <Ys>``         -> intersects(sing X, sing Y)    (I)
    - ``some <Xs> are not <Ys>``     -> some_not(sing X, sing Y)      (O)
    - ``therefore <categorical>``    -> Query of the same predicate (the conclusion)

  ordering (total_ordering shapes); X/Y are single items
    - ``<X> [is] <less-comp> [than] <Y>``     -> less(X, Y)
    - ``<X> [is] <greater-comp> [than] <Y>``  -> less(Y, X)
    - ``compare <X> with <Y>``                -> Query compare(X, Y)
    - ``sort [ascending|descending]`` /
      ``... order from <low> to <high>``      -> Query sort(order)

Multi-word noun phrases chunk by the CANONICALIZATION CONTRACT (see
``evals/comprehension/CANONICALIZATION.md``): a noun-phrase slot canonicalizes to
its tokens lowercased and joined with ``_`` ("North station"->"north_station",
"Level one"->"level_one"); a plural class slot singularizes its head first
("metal objects"->"metal_object"). Join is information-preserving on purpose —
head-word-only ("metal objects"->"metal") would collapse distinct phrases
("metal objects" vs "metal tools") into a false identity, itself a wrong=0 hazard.
A slot containing a reserved function word, or an adjacent-NP boundary that cannot
be located (the "are all <Xs> <Ys>?" two-NP case), still REFUSES rather than guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from generate.meaning_graph.model import (
    Entity,
    MeaningGraph,
    MeaningGraphError,
    MeaningSpan,
    Relation,
)

_ARTICLES = frozenset({"a", "an"})

# Common irregular plurals the corpus exercises. Conservative + closed; an
# unrecognized plural REFUSES rather than guessing a wrong singular (wrong=0).
_IRREGULAR_PLURALS = {
    "people": "person",
    "men": "man",
    "women": "woman",
    "children": "child",
    "feet": "foot",
    "teeth": "tooth",
    "mice": "mouse",
    "geese": "goose",
}

# Categorical quantifier -> the MeaningGraph predicate it mints. The predicate
# vocabulary is shared between facts and the "therefore" conclusion query, and is
# neutral: the syllogism projector maps {subset:A, disjoint:E, intersects:I,
# some_not:O}, while the set_membership projector reads subset/member only.
_QUANTIFIER_PREDICATE = {
    "all": "subset",
    "no": "disjoint",
    "some": "intersects",  # "some ... not" is special-cased to some_not
}

# Pairwise-order comparators. "less" means X < Y -> less(X, Y); "greater" means
# X > Y -> less(Y, X). Closed sets; an unknown comparator falls through to refusal.
_COMP_LESS = frozenset(
    {"below", "under", "beneath", "lower", "shorter", "smaller", "earlier", "closer", "before"}
)
_COMP_GREATER = frozenset(
    {"above", "over", "higher", "taller", "larger", "bigger", "greater", "later", "after", "farther", "further"}
)

# Sort-direction endpoints: "from <low> to <high>" is ascending; reversed is
# descending. Closed sets; an unrecognized endpoint refuses the sort query.
_SORT_LOW = frozenset(
    {"lowest", "shortest", "smallest", "least", "earliest", "bottom", "first", "low"}
)
_SORT_HIGH = frozenset(
    {"highest", "tallest", "largest", "greatest", "most", "latest", "top", "last", "high"}
)

# Function words that may NEVER appear inside a noun-phrase slot. A slot anchored
# by templates should hold only content tokens; if a reserved token leaks in, the
# clause is mis-parsed and we REFUSE rather than chunk junk (e.g. "beta in the
# same order" -> contains "the"/"order" -> refuse, not "beta_in_the_same_order").
_RESERVED = (
    _ARTICLES
    | _COMP_LESS
    | _COMP_GREATER
    | _SORT_LOW
    | _SORT_HIGH
    | {
        "is", "are", "than", "with", "not", "all", "no", "some", "therefore",
        "compare", "sort", "and", "or", "the", "from", "to", "order",
        "exist", "exists", "them", "which", "in", "of", "on", "at", "by",
    }
)

_SENTENCE_RE = re.compile(r"\s*([^.?!]+?)\s*([.?!])")


@dataclass(frozen=True, slots=True)
class Query:
    """A question over the comprehended facts (asks whether a relation holds)."""

    predicate: str
    arguments: tuple[str, ...]
    span: MeaningSpan
    negated: bool = False


@dataclass(frozen=True, slots=True)
class Comprehension:
    """Successful comprehension: a fact graph plus any questions asked."""

    meaning_graph: MeaningGraph
    queries: tuple[Query, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Refusal:
    """A typed refusal — the reader could not honestly read the input."""

    reason: str
    detail: str = ""


class _Reject(Exception):
    """Internal control-flow signal: a clause matched a template shape but is not
    honestly readable (multi-word NP, bad morphology, role conflict). Carries the
    typed ``Refusal`` so ``comprehend`` returns it verbatim."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.refusal = Refusal(reason, detail)


def _singularize(word: str) -> str | None:
    """Conservative plural -> singular. None when not confidently a plural."""
    if word in _IRREGULAR_PLURALS:
        return _IRREGULAR_PLURALS[word]
    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"
    if word.endswith(("ses", "xes", "zes", "ches", "shes")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 1:
        return word[:-1]
    return None


def _chunk(words: list[str], detail: str) -> str:
    """A noun-phrase slot -> a single canonical id by the canonicalization
    contract: lowercase tokens joined with ``_`` (information-preserving — distinct
    phrases never collapse). REFUSE if the slot is empty, holds a reserved function
    word, or yields a non-identifier."""
    if not words:
        raise _Reject("empty_np", detail)
    toks = [w.strip().lower() for w in words]
    # A reserved word is a parse-leak signal only INSIDE a multi-token slot. A
    # single-token slot is the whole NP — its token is content even if it spells a
    # function word (e.g. an item literally named "A", which is also the article).
    if len(toks) > 1 and any(t in _RESERVED for t in toks):
        raise _Reject("reserved_word_in_np", detail)
    canonical = "_".join(toks)
    if not canonical.isidentifier():
        raise _Reject("non_identifier_filler", detail)
    return canonical


def _chunk_class(words: list[str], detail: str) -> str:
    """A plural class noun-phrase slot -> singular canonical class id. The HEAD
    (final) token is singularized, then the phrase is chunked: "metal objects" ->
    "metal_object", "people" -> "person". REFUSE if the head is not a recognizable
    plural (e.g. the adjectival predicate "trained")."""
    if not words:
        raise _Reject("empty_np", detail)
    *modifiers, head = (w.strip().lower() for w in words)
    singular_head = _singularize(head)
    if singular_head is None:
        raise _Reject("unknown_morphology", detail)
    return _chunk([*modifiers, singular_head], detail)


def _split_sentences(text: str) -> list[tuple[str, str, int, int]]:
    """Return (body, terminator, start, end) for each sentence in *text*."""
    out: list[tuple[str, str, int, int]] = []
    matched_any = False
    for m in _SENTENCE_RE.finditer(text):
        matched_any = True
        body = m.group(1)
        if body.strip():
            out.append((body, m.group(2), m.start(1), m.end(1)))
    if not matched_any:
        body = text.strip()
        if body:
            start = text.find(body)
            out.append((body, ".", start, start + len(body)))
    return out


def _split_clauses(body: str) -> list[str]:
    """Split a sentence body into clauses on commas; strip a leading and/or."""
    clauses: list[str] = []
    for part in body.split(","):
        toks = part.split()
        if toks and toks[0].lower() in {"and", "or"}:
            toks = toks[1:]
        if toks:
            clauses.append(" ".join(toks))
    return clauses


def _parse_categorical(toks: list[str], detail: str) -> tuple[str, str, str] | None:
    """``<quant> <Xs> are [not] <Ys>`` -> (predicate, sub, sup); None if not it."""
    if not toks or toks[0] not in _QUANTIFIER_PREDICATE:
        return None
    if "are" not in toks:
        return None
    quant = toks[0]
    are_idx = toks.index("are")
    subject_words = toks[1:are_idx]
    predicate_words = toks[are_idx + 1:]
    negated = bool(predicate_words) and predicate_words[0] == "not"
    if negated:
        predicate_words = predicate_words[1:]
    if not subject_words or not predicate_words:
        raise _Reject("incomplete_categorical", detail)
    sub = _chunk_class(subject_words, detail)
    sup = _chunk_class(predicate_words, detail)
    if quant == "some" and negated:
        predicate = "some_not"
    elif negated:
        # "no ... not" / "all ... not" are out of this grammar; refuse, don't guess.
        raise _Reject("unsupported_negation", detail)
    else:
        predicate = _QUANTIFIER_PREDICATE[quant]
    return predicate, sub, sup


def _parse_comparative(toks: list[str], detail: str) -> tuple[str, str] | None:
    """``<X> [is] <comp> [than] <Y>`` -> (less_item, greater_item); None if not it."""
    comp_idx = next(
        (i for i, t in enumerate(toks) if t in _COMP_LESS or t in _COMP_GREATER),
        None,
    )
    if comp_idx is None:
        return None
    left = toks[:comp_idx]
    if left and left[-1] == "is":
        left = left[:-1]
    right = toks[comp_idx + 1:]
    if right and right[0] == "than":
        right = right[1:]
    if not left or not right:
        raise _Reject("incomplete_comparative", detail)
    x = _chunk(left, detail)
    y = _chunk(right, detail)
    if toks[comp_idx] in _COMP_LESS:
        return x, y  # X < Y
    return y, x  # X > Y  ->  less(Y, X)


def _parse_sort(toks: list[str], detail: str) -> str | None:
    """A sort request -> "ascending"|"descending"; None if not a sort request."""
    is_sort = toks and toks[0] == "sort"
    is_order = "order" in toks and "from" in toks
    if not (is_sort or is_order):
        return None
    if "ascending" in toks:
        return "ascending"
    if "descending" in toks:
        return "descending"
    if "from" in toks and "to" in toks:
        lo = toks[toks.index("from") + 1] if toks.index("from") + 1 < len(toks) else ""
        hi = toks[toks.index("to") + 1] if toks.index("to") + 1 < len(toks) else ""
        if lo in _SORT_LOW and hi in _SORT_HIGH:
            return "ascending"
        if lo in _SORT_HIGH and hi in _SORT_LOW:
            return "descending"
    raise _Reject("ambiguous_sort_order", detail)


def _parse_propositional(toks: list[str], detail: str) -> tuple[str, tuple[str, ...], bool] | None:
    """A propositional clause -> (predicate, atom_ids, negated); None if not it.

    Grammar (atoms are single tokens or reserved-free multi-word NPs):
      ``if <P> then <Q>``  -> ("implies", (P, Q), False)
      ``not <P>``          -> ("asserted", (P,), True)
      ``<P> or <Q>``       -> ("or", (P, Q), False)
      ``<P>`` (one token)  -> ("asserted", (P,), False)
    Anything else is None (let other templates / refusal handle it)."""
    if not toks:
        return None
    if toks[0] == "if" and "then" in toks:
        then_idx = toks.index("then")
        return "implies", (_chunk(toks[1:then_idx], detail), _chunk(toks[then_idx + 1:], detail)), False
    if toks[0] == "not":
        return "asserted", (_chunk(toks[1:], detail),), True
    if "or" in toks:
        i = toks.index("or")
        return "or", (_chunk(toks[:i], detail), _chunk(toks[i + 1:], detail)), False
    if len(toks) == 1:  # bare atomic assertion (single token only — keep the floor)
        return "asserted", (_chunk(toks, detail),), False
    return None


def comprehend(text: str, source_id: str = "input") -> Comprehension | Refusal:
    """Comprehend *text* into a MeaningGraph + queries, or a typed Refusal."""
    if not text or not text.strip():
        return Refusal("empty")

    sentences = _split_sentences(text)
    if not sentences:
        return Refusal("empty")

    role_kind: dict[str, str] = {}
    span_for: dict[str, MeaningSpan] = {}
    relations: list[tuple[str, tuple[str, ...], MeaningSpan, bool]] = []
    queries: list[Query] = []

    def claim(entity_id: str, kind: str, span: MeaningSpan) -> None:
        prior = role_kind.get(entity_id)
        if prior is not None and prior != kind:
            raise _Reject("role_conflict", entity_id)
        role_kind[entity_id] = kind
        span_for.setdefault(entity_id, span)

    try:
        for body, terminator, start, end in sentences:
            span = MeaningSpan(
                source_id=source_id, start=start, end=end, text=text[start:end]
            )
            is_question = terminator == "?"
            for clause in _split_clauses(body):
                _read_clause(clause, is_question, span, claim, relations, queries)
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
                Relation(pred, args, sp, negated) for pred, args, sp, negated in relations
            ),
        )
    except MeaningGraphError as exc:  # defensive — construction invariants
        return Refusal("invalid_graph", repr(exc))

    return Comprehension(meaning_graph=graph, queries=tuple(queries))


def _read_clause(
    clause: str,
    question: bool,
    span: MeaningSpan,
    claim,
    relations: list[tuple[str, tuple[str, ...], MeaningSpan, bool]],
    queries: list[Query],
) -> None:
    """Match one clause against the templates; mutate accumulators or REFUSE."""
    toks = clause.strip().lower().split()
    if not toks:
        raise _Reject("empty_clause", clause)

    # --- ordering queries (keyword-led; terminator-independent) ------------- #
    if toks[0] == "compare":
        if "with" not in toks[1:]:
            raise _Reject("unreadable_compare", clause)
        with_idx = toks.index("with", 1)
        left = _chunk(toks[1:with_idx], clause)
        right = _chunk(toks[with_idx + 1:], clause)
        for item in (left, right):
            claim(item, "item", span)
        queries.append(Query("compare", (left, right), span))
        return

    order = _parse_sort(toks, clause)
    if order is not None:
        queries.append(Query("sort", (order,), span))
        return

    # --- conclusion: "therefore <categorical | propositional>" ------------- #
    if toks[0] == "therefore":
        rest = toks[1:]
        categorical = _parse_categorical(rest, clause)
        if categorical is not None:
            predicate, sub, sup = categorical
            claim(sub, "class", span)
            claim(sup, "class", span)
            queries.append(Query(predicate, (sub, sup), span))
            return
        propositional = _parse_propositional(rest, clause)
        if propositional is not None:
            predicate, atoms, negated = propositional
            for atom in atoms:
                claim(atom, "proposition", span)
            queries.append(Query(predicate, atoms, span, negated))
            return
        raise _Reject("unreadable_conclusion", clause)

    # --- membership query: "is [the] <X> a|an <Y>?" ------------------------ #
    if question and toks[0] == "is":
        rest = toks[1:]
        if rest and rest[0] == "the":
            rest = rest[1:]
        art_idx = next((i for i, t in enumerate(rest) if t in _ARTICLES), None)
        if art_idx is None or art_idx == 0 or art_idx == len(rest) - 1:
            raise _Reject("unreadable_member_query", clause)
        name = _chunk(rest[:art_idx], clause)
        cls = _chunk(rest[art_idx + 1:], clause)
        claim(name, "individual", span)
        claim(cls, "class", span)
        queries.append(Query("member", (name, cls), span))
        return

    # --- subset query: "are all <Xs> <Ys>?" -------------------------------- #
    # The two class NPs are ADJACENT with no separating function word, so a
    # multi-word split is ambiguous -> require exactly two single tokens, else
    # refuse rather than guess the boundary.
    if question and len(toks) >= 2 and toks[0] == "are" and toks[1] == "all":
        body = toks[2:]
        if len(body) != 2:
            raise _Reject("ambiguous_subset_query", clause)
        sub = _chunk_class([body[0]], clause)
        sup = _chunk_class([body[1]], clause)
        claim(sub, "class", span)
        claim(sup, "class", span)
        queries.append(Query("subset", (sub, sup), span))
        return

    # --- categorical fact: "<quant> <Xs> are [not] <Ys>" ------------------- #
    categorical = _parse_categorical(toks, clause)
    if categorical is not None:
        predicate, sub, sup = categorical
        claim(sub, "class", span)
        claim(sup, "class", span)
        relations.append((predicate, (sub, sup), span, False))
        return

    # --- membership fact: "[the] <X> is a|an <Y>" -------------------------- #
    body_toks = toks[1:] if toks[0] == "the" else toks
    if "is" in body_toks:
        is_idx = body_toks.index("is")
        after = body_toks[is_idx + 1:]
        if is_idx > 0 and len(after) > 1 and after[0] in _ARTICLES:
            name = _chunk(body_toks[:is_idx], clause)
            cls = _chunk(after[1:], clause)
            claim(name, "individual", span)
            claim(cls, "class", span)
            relations.append(("member", (name, cls), span, False))
            return

    # --- ordering fact: "<X> [is] <comp> [than] <Y>" ----------------------- #
    comparative = _parse_comparative(toks, clause)
    if comparative is not None:
        lo, hi = comparative
        claim(lo, "item", span)
        claim(hi, "item", span)
        relations.append(("less", (lo, hi), span, False))
        return

    # --- propositional fact (fallback): if/then, or, not, bare atom -------- #
    propositional = _parse_propositional(toks, clause)
    if propositional is not None:
        predicate, atoms, negated = propositional
        for atom in atoms:
            claim(atom, "proposition", span)
        relations.append((predicate, atoms, span, negated))
        return

    raise _Reject("no_template_match", clause)
