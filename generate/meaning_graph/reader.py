"""The general comprehension reader — disciplined Path β (Phase 2a).

Reads subject/relation/object STRUCTURE symbolically from the token sequence via
domain-agnostic templates keyed on FUNCTION WORDS + ORDER, then mints content as
``MeaningGraph`` entities/relations. The field provably cannot recover this
structure (the holonomy fold is lossy/non-invertible — see the α-falsification in
``docs/analysis/phase2-general-comprehension-organ-scope-2026-06-05.md``); the
field's honest role is grounding/coherence, not composition.

Refusal-first: a clause that matches no template, a filler that is not a clean
identifier, an unrecognized plural, or a role conflict all REFUSE — never guess.
That keeps ``wrong=0`` at the comprehension layer (refusal is success; a fabricated
reading is the only failure).

Templates (this increment):
  - ``<X> is a|an <Y>``        -> member(individual=X, class=Y)
  - ``all <Xs> are <Ys>``      -> subset(subclass=sing(X), superclass=sing(Y))
  - ``is <X> a|an <Y>?``       -> Query member(X, Y)

Overfit-trap mitigation: templates key on function words + order (general), never
on domain content; the same templates read animals, professions, geography, kin.
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
    subsets: list[tuple[str, str, MeaningSpan]] = []
    queries: list[Query] = []

    def claim(entity_id: str, kind: str, span: MeaningSpan) -> bool:
        prior = role_kind.get(entity_id)
        if prior is not None and prior != kind:
            return False
        role_kind[entity_id] = kind
        span_for.setdefault(entity_id, span)
        return True

    for body, terminator, start, end in sentences:
        toks = body.lower().split()
        span = MeaningSpan(source_id=source_id, start=start, end=end, text=text[start:end])
        is_question = terminator == "?"

        # Template: subset query  ``are all <Xs> <Ys>?``
        if is_question and len(toks) == 4 and toks[0] == "are" and toks[1] == "all":
            raw_sub, raw_sup = _identifier(toks[2]), _identifier(toks[3])
            if raw_sub is None or raw_sup is None:
                return Refusal("non_identifier_filler", body)
            sub, sup = _singularize(raw_sub), _singularize(raw_sup)
            if sub is None or sup is None:
                return Refusal("unknown_morphology", body)
            if not sub.isidentifier() or not sup.isidentifier():
                return Refusal("non_identifier_filler", body)
            if not claim(sub, "class", span) or not claim(sup, "class", span):
                return Refusal("role_conflict", body)
            queries.append(Query("subset", (sub, sup), span))
            continue

        # Template: definite-NP membership query  ``is the <X> a|an <Y>?``
        if is_question and len(toks) == 5 and toks[0] == "is" and toks[1] == "the" and toks[3] in _ARTICLES:
            name, cls = _identifier(toks[2]), _identifier(toks[4])
            if name is None or cls is None:
                return Refusal("non_identifier_filler", body)
            if not claim(name, "individual", span) or not claim(cls, "class", span):
                return Refusal("role_conflict", body)
            queries.append(Query("member", (name, cls), span))
            continue

        # Template: query  ``is <X> a|an <Y>?``
        if is_question and len(toks) == 4 and toks[0] == "is" and toks[2] in _ARTICLES:
            name, cls = _identifier(toks[1]), _identifier(toks[3])
            if name is None or cls is None:
                return Refusal("non_identifier_filler", body)
            if not claim(name, "individual", span) or not claim(cls, "class", span):
                return Refusal("role_conflict", body)
            queries.append(Query("member", (name, cls), span))
            continue

        # Template: definite-NP membership  ``the <X> is a|an <Y>``
        if not is_question and len(toks) == 5 and toks[0] == "the" and toks[2] == "is" and toks[3] in _ARTICLES:
            name, cls = _identifier(toks[1]), _identifier(toks[4])
            if name is None or cls is None:
                return Refusal("non_identifier_filler", body)
            if not claim(name, "individual", span) or not claim(cls, "class", span):
                return Refusal("role_conflict", body)
            members.append((name, cls, span))
            continue

        # Template: membership  ``<X> is a|an <Y>``
        if not is_question and len(toks) == 4 and toks[1] == "is" and toks[2] in _ARTICLES:
            name, cls = _identifier(toks[0]), _identifier(toks[3])
            if name is None or cls is None:
                return Refusal("non_identifier_filler", body)
            if not claim(name, "individual", span) or not claim(cls, "class", span):
                return Refusal("role_conflict", body)
            members.append((name, cls, span))
            continue

        # Template: subsumption  ``all <Xs> are <Ys>``
        if not is_question and len(toks) == 4 and toks[0] == "all" and toks[2] == "are":
            raw_sub, raw_sup = _identifier(toks[1]), _identifier(toks[3])
            if raw_sub is None or raw_sup is None:
                return Refusal("non_identifier_filler", body)
            sub, sup = _singularize(raw_sub), _singularize(raw_sup)
            if sub is None or sup is None:
                return Refusal("unknown_morphology", body)
            if not sub.isidentifier() or not sup.isidentifier():
                return Refusal("non_identifier_filler", body)
            if not claim(sub, "class", span) or not claim(sup, "class", span):
                return Refusal("role_conflict", body)
            subsets.append((sub, sup, span))
            continue

        return Refusal("no_template_match", body)

    try:
        entities = tuple(
            Entity(entity_id=eid, name=eid, span=span_for[eid], kind=role_kind[eid])
            for eid in sorted(role_kind)
        )
        relations = tuple(
            [Relation("member", (ind, cls), sp) for ind, cls, sp in members]
            + [Relation("subset", (sub, sup), sp) for sub, sup, sp in subsets]
        )
        graph = MeaningGraph(entities=entities, relations=relations)
    except MeaningGraphError as exc:  # defensive — construction invariants
        return Refusal("invalid_graph", repr(exc))

    return Comprehension(meaning_graph=graph, queries=tuple(queries))
