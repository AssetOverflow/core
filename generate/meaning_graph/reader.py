"""The general comprehension reader — disciplined Path β (Phase 2a).

Reads subject/relation/object STRUCTURE symbolically from the token sequence via
domain-agnostic templates keyed on FUNCTION WORDS + ORDER, then mints content as
``MeaningGraph`` entities/relations. The field provably cannot recover this
structure (the holonomy fold is lossy/non-invertible — see the α-falsification in
``docs/analysis/phase2-general-comprehension-organ-scope-2026-06-05.md``); the
field's honest role is grounding/coherence, not composition.

Refusal-first: a clause that matches no template, a filler that is not a clean
identifier, an unrecognized plural/comparative, or a role conflict all REFUSE —
never guess. That keeps ``wrong=0`` at the comprehension layer (refusal is
success; a fabricated reading is the only failure).

Templates (this increment), each producing NEUTRAL predicates a projector adapts:
  - ``<X> is a|an <Y>`` / ``the <X> is a|an <Y>``   -> member(individual, class)
  - ``all/no/some <Xs> are [not] <Ys>``             -> subset/disjoint/intersects/some_not
  - ``X is <comp> [than] Y``                         -> less(lesser, greater)
  - ``is <X> a|an <Y>?`` / ``are all <Xs> <Ys>?``    -> membership / subset query
  - ``Therefore <categorical>``                      -> categorical conclusion query
  - ``sort/order ... from <low> to <high> ...``      -> sort query

Overfit-trap mitigation: templates key on function words + order (general), never
on domain content; the same templates read animals, professions, geometry, kin.
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

# Comparative surface -> ordering direction. Conservative + closed: a wrong
# direction would flip the sort (wrong>0), so an UNKNOWN comparative refuses.
_COMP_LESS = frozenset(
    {"below", "under", "beneath", "before", "earlier", "shorter", "smaller",
     "younger", "slower", "lighter", "lower", "less", "weaker", "cheaper",
     "nearer", "closer"}
)
_COMP_GREATER = frozenset(
    {"above", "over", "after", "later", "taller", "bigger", "larger", "older",
     "faster", "heavier", "higher", "greater", "stronger", "longer", "farther",
     "further"}
)
_SORT_LOW = frozenset(
    {"lowest", "shortest", "smallest", "youngest", "slowest", "lightest",
     "least", "first", "cheapest", "weakest", "nearest"}
)
_SORT_HIGH = frozenset(
    {"highest", "tallest", "largest", "biggest", "oldest", "fastest",
     "heaviest", "greatest", "last", "longest", "strongest", "farthest"}
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


def _match_categorical(toks: list[str]) -> tuple[str, str, str] | None:
    """A categorical clause -> (neutral predicate, raw_subject, raw_object).

    Function-word keyed (all/no/some ... are [not] ...); domain-agnostic. The
    syllogism projector maps subset/disjoint/intersects/some_not -> A/E/I/O.
    """
    if len(toks) == 5 and toks[0] == "some" and toks[2] == "are" and toks[3] == "not":
        return ("some_not", toks[1], toks[4])
    if len(toks) == 4 and toks[2] == "are":
        if toks[0] == "all":
            return ("subset", toks[1], toks[3])
        if toks[0] == "no":
            return ("disjoint", toks[1], toks[3])
        if toks[0] == "some":
            return ("intersects", toks[1], toks[3])
    return None


def _match_comparative(toks: list[str]) -> tuple[str, str] | None:
    """A comparative clause -> (raw_lesser, raw_greater), or None.

    Handles, with optional elided copula:
      ``X is <comp> than Y`` / ``X <comp> than Y``   (len 5 / len 4)
      ``X is <prep> Y``      / ``X <prep> Y``         (len 4 / len 3)
    LESS keeps the order (X < Y); GREATER reverses it (X > Y => Y < X).
    """
    if len(toks) == 5 and toks[1] == "is" and toks[3] == "than":
        comp, x, y = toks[2], toks[0], toks[4]
    elif len(toks) == 4 and toks[2] == "than":
        comp, x, y = toks[1], toks[0], toks[3]
    elif len(toks) == 4 and toks[1] == "is":
        comp, x, y = toks[2], toks[0], toks[3]
    elif len(toks) == 3:
        comp, x, y = toks[1], toks[0], toks[2]
    else:
        return None
    if comp in _COMP_LESS:
        return (x, y)
    if comp in _COMP_GREATER:
        return (y, x)
    return None


def _match_sort_query(toks: list[str]) -> str | None:
    """A sort request -> 'ascending'/'descending'.

    Bare ``sort ascending|descending`` or ``sort/order ... from <low> to <high>``.
    """
    if "sort" not in toks and "order" not in toks:
        return None
    if "ascending" in toks and "descending" not in toks:
        return "ascending"
    if "descending" in toks and "ascending" not in toks:
        return "descending"
    if "from" not in toks or "to" not in toks:
        return None
    fi, ti = toks.index("from"), toks.index("to")
    if not (fi + 1 < ti and ti + 1 < len(toks)):
        return None
    low, high = toks[fi + 1], toks[ti + 1]
    if low in _SORT_LOW and high in _SORT_HIGH:
        return "ascending"
    if low in _SORT_HIGH and high in _SORT_LOW:
        return "descending"
    return None


def _split_clauses(body: str) -> list[str]:
    """Split a sentence on commas; strip a leading coordinating 'and'/'or'."""
    parts: list[str] = []
    for piece in body.split(","):
        p = piece.strip()
        low = p.lower()
        for lead in ("and ", "or "):
            if low.startswith(lead):
                p = p[len(lead):].strip()
                break
        if p:
            parts.append(p)
    return parts


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


def comprehend(text: str, source_id: str = "input") -> Comprehension | Refusal:
    """Comprehend *text* into a MeaningGraph + queries, or a typed Refusal."""
    if not text or not text.strip():
        return Refusal("empty")

    sentences = _split_sentences(text)
    if not sentences:
        return Refusal("empty")

    role_kind: dict[str, str] = {}
    span_for: dict[str, MeaningSpan] = {}
    members: list[tuple[str, str, MeaningSpan]] = []
    class_relations: list[tuple[str, str, str, MeaningSpan]] = []
    order_relations: list[tuple[str, str, MeaningSpan]] = []
    queries: list[Query] = []

    def claim(entity_id: str, kind: str, span: MeaningSpan) -> bool:
        prior = role_kind.get(entity_id)
        if prior is not None and prior != kind:
            return False
        role_kind[entity_id] = kind
        span_for.setdefault(entity_id, span)
        return True

    for body, terminator, start, end in sentences:
        span = MeaningSpan(source_id=source_id, start=start, end=end, text=text[start:end])
        is_question = terminator == "?"

        for clause in _split_clauses(body):
            toks = clause.lower().split()
            if not toks:
                continue

            # Template: sort query  ``... sort/order ... from <low> to <high> ...``
            sort_order = _match_sort_query(toks)
            if sort_order is not None:
                queries.append(Query("sort", (sort_order,), span))
                continue

            # Template: compare query  ``compare <X> with <Y>``
            if len(toks) == 4 and toks[0] == "compare" and toks[2] == "with":
                left, right = _identifier(toks[1]), _identifier(toks[3])
                if left is None or right is None:
                    return Refusal("non_identifier_filler", clause)
                if not claim(left, "item", span) or not claim(right, "item", span):
                    return Refusal("role_conflict", clause)
                queries.append(Query("compare", (left, right), span))
                continue

            # Template: comparative  ``X is <comp> [than] Y``  -> less(lesser, greater)
            comparative = _match_comparative(toks)
            if comparative is not None:
                raw_lo, raw_hi = comparative
                lo, hi = _identifier(raw_lo), _identifier(raw_hi)
                if lo is None or hi is None:
                    return Refusal("non_identifier_filler", clause)
                if not claim(lo, "item", span) or not claim(hi, "item", span):
                    return Refusal("role_conflict", clause)
                order_relations.append((lo, hi, span))
                continue

            # Template: subset query  ``are all <Xs> <Ys>?``
            if is_question and len(toks) == 4 and toks[0] == "are" and toks[1] == "all":
                raw_sub, raw_sup = _identifier(toks[2]), _identifier(toks[3])
                if raw_sub is None or raw_sup is None:
                    return Refusal("non_identifier_filler", clause)
                sub, sup = _singularize(raw_sub), _singularize(raw_sup)
                if sub is None or sup is None:
                    return Refusal("unknown_morphology", clause)
                if not sub.isidentifier() or not sup.isidentifier():
                    return Refusal("non_identifier_filler", clause)
                if not claim(sub, "class", span) or not claim(sup, "class", span):
                    return Refusal("role_conflict", clause)
                queries.append(Query("subset", (sub, sup), span))
                continue

            # Template: definite-NP membership query  ``is the <X> a|an <Y>?``
            if is_question and len(toks) == 5 and toks[0] == "is" and toks[1] == "the" and toks[3] in _ARTICLES:
                name, cls = _identifier(toks[2]), _identifier(toks[4])
                if name is None or cls is None:
                    return Refusal("non_identifier_filler", clause)
                if not claim(name, "individual", span) or not claim(cls, "class", span):
                    return Refusal("role_conflict", clause)
                queries.append(Query("member", (name, cls), span))
                continue

            # Template: membership query  ``is <X> a|an <Y>?``
            if is_question and len(toks) == 4 and toks[0] == "is" and toks[2] in _ARTICLES:
                name, cls = _identifier(toks[1]), _identifier(toks[3])
                if name is None or cls is None:
                    return Refusal("non_identifier_filler", clause)
                if not claim(name, "individual", span) or not claim(cls, "class", span):
                    return Refusal("role_conflict", clause)
                queries.append(Query("member", (name, cls), span))
                continue

            # Template: definite-NP membership  ``the <X> is a|an <Y>``
            if not is_question and len(toks) == 5 and toks[0] == "the" and toks[2] == "is" and toks[3] in _ARTICLES:
                name, cls = _identifier(toks[1]), _identifier(toks[4])
                if name is None or cls is None:
                    return Refusal("non_identifier_filler", clause)
                if not claim(name, "individual", span) or not claim(cls, "class", span):
                    return Refusal("role_conflict", clause)
                members.append((name, cls, span))
                continue

            # Template: membership  ``<X> is a|an <Y>``
            if not is_question and len(toks) == 4 and toks[1] == "is" and toks[2] in _ARTICLES:
                name, cls = _identifier(toks[0]), _identifier(toks[3])
                if name is None or cls is None:
                    return Refusal("non_identifier_filler", clause)
                if not claim(name, "individual", span) or not claim(cls, "class", span):
                    return Refusal("role_conflict", clause)
                members.append((name, cls, span))
                continue

            # Template: categorical (A/E/I/O), premise or 'Therefore' conclusion
            if not is_question:
                is_conclusion = bool(toks) and toks[0] == "therefore"
                cat = _match_categorical(toks[1:] if is_conclusion else toks)
                if cat is not None:
                    pred, raw_a, raw_b = cat
                    a, b = _identifier(raw_a), _identifier(raw_b)
                    if a is None or b is None:
                        return Refusal("non_identifier_filler", clause)
                    sa, sb = _singularize(a), _singularize(b)
                    if sa is None or sb is None:
                        return Refusal("unknown_morphology", clause)
                    if not sa.isidentifier() or not sb.isidentifier():
                        return Refusal("non_identifier_filler", clause)
                    if not claim(sa, "class", span) or not claim(sb, "class", span):
                        return Refusal("role_conflict", clause)
                    if is_conclusion:
                        queries.append(Query(pred, (sa, sb), span))
                    else:
                        class_relations.append((pred, sa, sb, span))
                    continue

            return Refusal("no_template_match", clause)

    try:
        entities = tuple(
            Entity(entity_id=eid, name=eid, span=span_for[eid], kind=role_kind[eid])
            for eid in sorted(role_kind)
        )
        relations = tuple(
            [Relation("member", (ind, cls), sp) for ind, cls, sp in members]
            + [Relation(pred, (a, b), sp) for pred, a, b, sp in class_relations]
            + [Relation("less", (lo, hi), sp) for lo, hi, sp in order_relations]
        )
        graph = MeaningGraph(entities=entities, relations=relations)
    except MeaningGraphError as exc:  # defensive — construction invariants
        return Refusal("invalid_graph", repr(exc))

    return Comprehension(meaning_graph=graph, queries=tuple(queries))
