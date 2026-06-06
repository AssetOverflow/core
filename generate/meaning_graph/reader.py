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

Multi-word noun phrases are REFUSED on purpose: the staged gold lanes canonicalize
multi-word NPs three contradictory ways ("North station"->"north", "Level one"->
"level_one", "metal objects"->"metal"), so no single general rule is wrong=0-safe.
Until the gold lanes carry a canonicalization contract, the only honest reading of
a multi-word NP is refusal.
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


def _identifier(word: str) -> str | None:
    """Normalize a content token to a clean identifier, or None to refuse."""
    w = word.strip().lower()
    return w if w.isidentifier() else None


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


def _one(words: list[str], detail: str) -> str:
    """A single content token -> identifier, or REFUSE (multi-word / non-id)."""
    if len(words) != 1:
        raise _Reject("multiword_np", detail)
    ident = _identifier(words[0])
    if ident is None:
        raise _Reject("non_identifier_filler", detail)
    return ident


def _one_class(words: list[str], detail: str) -> str:
    """A single plural content token -> singular class id, or REFUSE."""
    word = _one(words, detail)
    singular = _singularize(word)
    if singular is None:
        raise _Reject("unknown_morphology", detail)
    if not singular.isidentifier():
        raise _Reject("non_identifier_filler", detail)
    return singular


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
    sub = _one_class(subject_words, detail)
    sup = _one_class(predicate_words, detail)
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
    x = _one(left, detail)
    y = _one(right, detail)
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


def comprehend(text: str, source_id: str = "input") -> Comprehension | Refusal:
    """Comprehend *text* into a MeaningGraph + queries, or a typed Refusal."""
    if not text or not text.strip():
        return Refusal("empty")

    sentences = _split_sentences(text)
    if not sentences:
        return Refusal("empty")

    role_kind: dict[str, str] = {}
    span_for: dict[str, MeaningSpan] = {}
    relations: list[tuple[str, tuple[str, ...], MeaningSpan]] = []
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
                Relation(pred, args, sp) for pred, args, sp in relations
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
    relations: list[tuple[str, tuple[str, ...], MeaningSpan]],
    queries: list[Query],
) -> None:
    """Match one clause against the templates; mutate accumulators or REFUSE."""
    toks = clause.strip().lower().split()
    if not toks:
        raise _Reject("empty_clause", clause)

    # --- ordering queries (keyword-led; terminator-independent) ------------- #
    if toks[0] == "compare":
        if len(toks) != 4 or toks[2] != "with":
            raise _Reject("unreadable_compare", clause)
        left = _one([toks[1]], clause)
        right = _one([toks[3]], clause)
        for item in (left, right):
            claim(item, "item", span)
        queries.append(Query("compare", (left, right), span))
        return

    order = _parse_sort(toks, clause)
    if order is not None:
        queries.append(Query("sort", (order,), span))
        return

    # --- syllogism conclusion: "therefore <categorical>" ------------------- #
    if toks[0] == "therefore":
        parsed = _parse_categorical(toks[1:], clause)
        if parsed is None:
            raise _Reject("unreadable_conclusion", clause)
        predicate, sub, sup = parsed
        claim(sub, "class", span)
        claim(sup, "class", span)
        queries.append(Query(predicate, (sub, sup), span))
        return

    # --- membership query: "is [the] <X> a|an <Y>?" ------------------------ #
    if question and toks[0] == "is":
        rest = toks[1:]
        if rest and rest[0] == "the":
            rest = rest[1:]
        if len(rest) == 3 and rest[1] in _ARTICLES:
            name = _one([rest[0]], clause)
            cls = _one([rest[2]], clause)
            claim(name, "individual", span)
            claim(cls, "class", span)
            queries.append(Query("member", (name, cls), span))
            return
        raise _Reject("unreadable_member_query", clause)

    # --- subset query: "are all <Xs> <Ys>?" -------------------------------- #
    if question and len(toks) == 4 and toks[0] == "are" and toks[1] == "all":
        sub = _one_class([toks[2]], clause)
        sup = _one_class([toks[3]], clause)
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
        relations.append((predicate, (sub, sup), span))
        return

    # --- membership fact: "[the] <X> is a|an <Y>" -------------------------- #
    body_toks = toks[1:] if toks[0] == "the" else toks
    if len(body_toks) == 4 and body_toks[1] == "is" and body_toks[2] in _ARTICLES:
        name = _one([body_toks[0]], clause)
        cls = _one([body_toks[3]], clause)
        claim(name, "individual", span)
        claim(cls, "class", span)
        relations.append(("member", (name, cls), span))
        return

    # --- ordering fact: "<X> [is] <comp> [than] <Y>" ----------------------- #
    comparative = _parse_comparative(toks, clause)
    if comparative is not None:
        lo, hi = comparative
        claim(lo, "item", span)
        claim(hi, "item", span)
        relations.append(("less", (lo, hi), span))
        return

    raise _Reject("no_template_match", clause)
