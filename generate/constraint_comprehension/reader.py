"""Two-category constraint-problem reader (R2 C5–C9): prose -> ``ConstraintProblem``.

Recognizes the four pieces of a finite-integer two-category problem and assembles the typed
setup, REFUSING (never mis-assembling) when a piece is missing or there are not exactly two
categories. Off-serving; deterministic. The reader does NOT solve — solvability (singular /
non-integer / negative systems) is the solver's boundary (C3): an equal-coefficient problem
(e.g. 4 wheels each) still reads setup_correct and is refused *downstream* by the solver. (This
reconciles the design sketch's "no equal coefficients" note: equal coefficients are a SOLVER
refusal, ``indistinguishable_weights``, not a reader refusal — the gold classifies that fixture
``solver_refuses``, so the reader must read it.)

Recognizers and their wrong=0 guards:
  C5 category pair  — the two categories come from the per-category coefficient clauses (exactly
                      two distinct; >2 -> ``too_many_categories``).
  C6 coefficient    — ``Each <cat> (holds|has|costs|is worth) <N> <measured_unit>``; the two
                      coefficients must share one measured unit (else ``coefficient_unit_mismatch``).
  C7 total count    — a ``<N> <collective>`` sentence whose unit is the collective (not the
                      measured unit) -> ``x + y = N``; absent -> ``missing_total_count``.
  C8 weighted total — a ``<T> <measured_unit>`` sentence -> ``a·x + b·y = T`` (coefficients from
                      C6); absent -> ``missing_weighted_total``.
  C9 query target   — ``How many <category> are there?`` -> the asked unknown (one of the two;
                      else ``query_target_not_a_category``).

``too_many_categories`` / ``missing_total_count`` / ``missing_weighted_total`` are the gold's
closed ``reader_reason`` set (ADR-0211). ``coefficient_unit_mismatch`` / ``category_pair_not_found``
/ ``query_target_not_a_category`` are defensive guards with no gold fixture (tested by
construction); they never fire on the gold corpus.
"""

from __future__ import annotations

from generate.constraint_comprehension.expr import LinearConstraint, LinearExpr
from generate.constraint_comprehension.model import (
    AttributeFact,
    ConstraintProblem,
    ConstraintQuery,
    Unknown,
)
from generate.meaning_graph.reader import Refusal, _split_sentences

#: Coefficient-clause verbs. The category words sit between the article and the first of these;
#: ``worth`` follows ``is`` and is skipped. Totals use other verbs (rents/buys/carry/…) and are
#: classified separately by their noun, so they never reach coefficient parsing.
_COEFF_VERBS = frozenset({"holds", "hold", "has", "have", "costs", "cost", "is", "are"})

#: Tokens that close the noun phrase after a count/weighted digit.
_NP_STOP = frozenset({"in", "for", "all", "some", "and", "to", "of", "with", "that"})

_DOMAIN = "nonnegative_integer"


def _singular(noun: str) -> str:
    """Conservative singularization (``buses``->``bus``, ``boxes``->``box``, ``legs``->``leg``)."""
    noun = noun.strip(".,?!")
    if noun.endswith("es") and noun[:-2].endswith(("x", "s", "z", "ch", "sh")):
        return noun[:-2]
    if noun.endswith("s") and len(noun) > 1:
        return noun[:-1]
    return noun


def _parse_coefficient_clause(clause: str) -> tuple[str, list[str], str, int] | None:
    """``(symbol, category_words, measured_unit, value)`` for a coefficient clause, else ``None``.

    A coefficient clause starts with ``each`` (any category) or with ``a`` **and** contains
    ``worth`` (``A nickel is worth 5 cents``). The ``a``-without-``worth`` form is a framing /
    total sentence (``A jar holds 20 coins``) and is rejected here so it is classified as a total.
    """
    toks = clause.lower().split()
    if not toks or toks[0] not in ("each", "a"):
        return None
    if toks[0] == "a" and "worth" not in toks:
        return None
    verb_i = next((i for i in range(1, len(toks)) if toks[i] in _COEFF_VERBS), None)
    if verb_i is None or verb_i == 1:
        return None
    category_words = toks[1:verb_i]
    digit_i = next((j for j in range(verb_i + 1, len(toks)) if toks[j].strip(".,").isdigit()), None)
    if digit_i is None or digit_i + 1 >= len(toks):
        return None
    value = int(toks[digit_i].strip(".,"))
    measured_unit = _singular(toks[digit_i + 1])
    return "_".join(category_words), category_words, measured_unit, value


def _split_coeff_clauses(sentence: str) -> list[str]:
    """Split a coefficient sentence into clauses on commas and ``and`` (``Each X … and each Y …``)."""
    parts: list[str] = []
    for chunk in sentence.split(","):
        parts.extend(chunk.split(" and "))
    return [p.strip() for p in parts if p.strip()]


def _digit_and_head(sentence: str) -> tuple[str | None, int | None]:
    """The first integer in *sentence* and the singular head noun of the phrase that follows it."""
    toks = sentence.lower().rstrip("?.!").split()
    for i, tok in enumerate(toks):
        if tok.strip(".,").isdigit():
            value = int(tok.strip(".,"))
            phrase: list[str] = []
            for nxt in toks[i + 1:]:
                if nxt.endswith(","):
                    phrase.append(nxt[:-1])
                    break
                if nxt in _NP_STOP:
                    break
                phrase.append(nxt)
            if not phrase:
                return None, None
            return _singular(phrase[-1]), value
    return None, None


def _query_symbol(toks: list[str]) -> str | None:
    """``How many <category> are there?`` -> the (singularized, joined) category symbol."""
    if "are" not in toks:
        return None
    words = toks[2 : toks.index("are")]
    if not words:
        return None
    return "_".join(words[:-1] + [_singular(words[-1])])


def read_constraint_problem(text: str) -> ConstraintProblem | Refusal:
    """Comprehend two-category constraint prose into a typed :class:`ConstraintProblem`, or refuse."""
    if not text or not text.strip():
        return Refusal("empty")

    coefficients: list[tuple[str, list[str], str, int]] = []
    query_words: str | None = None
    leftover: list[str] = []

    for body, _term, _start, _end in _split_sentences(text):
        toks = body.lower().rstrip("?.!").split()
        if len(toks) >= 2 and toks[0] == "how" and toks[1] == "many":
            query_words = _query_symbol(toks)
            continue
        parsed_any = False
        for clause in _split_coeff_clauses(body):
            pc = _parse_coefficient_clause(clause)
            if pc is not None:
                coefficients.append(pc)
                parsed_any = True
        if not parsed_any:
            leftover.append(body)

    # C5 — exactly two distinct categories (order preserved).
    coeff_value: dict[str, int] = {}
    coeff_unit: dict[str, str] = {}
    entity: dict[str, str] = {}
    order: list[str] = []
    for symbol, words, mu, value in coefficients:
        if symbol in coeff_value and coeff_value[symbol] != value:
            return Refusal("coefficient_conflict", symbol)
        if symbol not in coeff_value:
            order.append(symbol)
        coeff_value[symbol], coeff_unit[symbol], entity[symbol] = value, mu, " ".join(words)
    if len(order) > 2:
        return Refusal("too_many_categories", f"{order}")
    if len(order) != 2:
        return Refusal("category_pair_not_found", f"{order}")

    # C6 — the two coefficients must share one measured unit.
    if len({coeff_unit[s] for s in order}) != 1:
        return Refusal("coefficient_unit_mismatch", f"{[coeff_unit[s] for s in order]}")
    measured_unit = coeff_unit[order[0]]

    # C7 / C8 — classify the leftover digit sentences: collective unit -> count; measured -> weighted.
    total_count: int | None = None
    collective: str | None = None
    weighted_total: int | None = None
    for sentence in leftover:
        head, value = _digit_and_head(sentence)
        if value is None:
            continue
        if head == measured_unit:
            weighted_total = value
        else:
            total_count, collective = value, head
    if total_count is None or collective is None:
        return Refusal("missing_total_count")
    if weighted_total is None:
        return Refusal("missing_weighted_total")

    # C9 — the query must name one of the two categories.
    if query_words is None or query_words not in order:
        return Refusal("query_target_not_a_category", f"{query_words}")

    s0, s1 = order
    unknowns = tuple(
        Unknown(symbol=s, entity=entity[s], unit=collective, domain=_DOMAIN) for s in order
    )
    facts = tuple(
        AttributeFact(category=s, measured_unit=measured_unit, value=coeff_value[s]) for s in order
    )
    constraints = (
        LinearConstraint(LinearExpr(((s0, 1), (s1, 1))), "eq", total_count),
        LinearConstraint(
            LinearExpr(((s0, coeff_value[s0]), (s1, coeff_value[s1]))), "eq", weighted_total
        ),
    )
    return ConstraintProblem(unknowns, facts, constraints, ConstraintQuery(query_words, collective))


__all__ = ["read_constraint_problem"]
