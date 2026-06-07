"""Arithmetic word-problem comprehension -> binding_graph (Phase 2b, domain 5).

The doctrine-aligned quantity reader, and the binding-graph's FIRST comprehension
consumer. Quantities live in the ``binding_graph`` substrate — CLAUDE.md: the
``MeaningGraph`` deliberately excludes quantities — so this reader lives OUTSIDE
``generate/meaning_graph`` (which stays a numeric-free interlingua, INV-28) and
targets the binding-graph instead.

It reads arithmetic prose ("Liam has 6 stickers. Mia has 4 more stickers than
Liam.") into ``SymbolBinding`` / ``BoundFact`` / ``BoundEquation`` and runs the
REAL ``check_admissibility`` — there is NO stamped "admitted": an equation is
admitted only if its operand units actually verify, and a dimensional mismatch
REFUSES the whole reading. ``to_relational_metric`` then projects the binding-graph
into the independent ``relational_metric`` oracle for scoring.

Templates (function-word + order; digits only — a non-digit quantity REFUSES):
  - ``<X> has <N> <unit>``                 -> BoundFact(X = N [unit])
  - ``<Y> has <N> more <unit> than <X>``   -> BoundEquation(Y = X + N)   op=add
  - ``<Y> has <N> fewer <unit> than <X>``  -> BoundEquation(Y = X - N)   op=subtract
  - query ``How many <unit> does <Y> have``       -> ask Y
  - query ``How many <unit> do <X> and <Y> have`` -> total = X + Y; ask total

Refusal-first: an unparseable clause, a non-digit quantity, a non-identifier name,
a missing/duplicated query, or an admissibility refusal all return a typed
``Refusal`` — never a fabricated quantity (wrong=0 at the comprehension layer).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from generate.binding_graph.admissibility import AdmissibilityError, check_admissibility
from generate.binding_graph.model import (
    BoundEquation,
    BoundFact,
    BoundUnknown,
    SemanticSymbolicBindingGraph,
    SourceSpanLink,
    SymbolBinding,
)
from generate.binding_graph.units import UnitAlgebraError, parse_unit
from generate.meaning_graph.reader import Refusal, _split_sentences
from generate.quantitative_expr import (
    Add,
    Expr,
    Literal,
    Mul,
    Sub,
    SumOf,
    Symbol,
    dependencies,
    operation_kind,
    to_canonical_string,
    to_relation,
)

_INTRODUCED_BY = "comprehend_quantitative"

#: The generic count dimension for discrete sortal objects (an existing pack
#: lemma resolving to dimension ``count``). A noun the unit pack does not know is
#: read as a count of discrete objects, NOT faked into a physical unit.
_COUNT_UNIT = "item"


def _resolve_unit(noun: str) -> str:
    """Map a surface unit noun to a binding-graph unit the pack accepts.

    A KNOWN physical/currency/count unit (``dollars`` -> ``dollar``, ``meters``)
    is used verbatim (``parse_unit`` depluralizes). An UNKNOWN sortal noun
    (``stickers``, ``coins``) is a count of discrete objects -> ``item`` (dimension
    ``count``). This keeps admissibility a REAL check: ``count + count`` admits,
    ``count + length`` still refuses — nothing is stamped or faked.
    """
    try:
        parse_unit(noun)
    except UnitAlgebraError:
        return _COUNT_UNIT
    return noun


@dataclass(frozen=True, slots=True)
class QuantComprehension:
    """Successful arithmetic comprehension.

    The question target is no longer a sidecar field — it lives IN the graph as the
    sole :class:`BoundUnknown` (PR-1). Consumers read it via :func:`single_unknown`,
    which refuses (returns ``None``) on a graph that does not carry exactly one
    target rather than silently picking one.

    ``equation_exprs`` is the typed expression IR (PR-4) — the reader's SOURCE OF MEANING
    for each equation, as ``(lhs_symbol_id, Expr)`` pairs. ``BoundEquation.rhs_canonical``
    is the serialization of these; the projection reads the IR, never the string.
    """

    binding_graph: SemanticSymbolicBindingGraph
    equation_exprs: tuple[tuple[str, Expr], ...] = ()


def single_unknown(graph: SemanticSymbolicBindingGraph) -> BoundUnknown | None:
    """Return the graph's SOLE question target, or ``None`` if it is not exactly one.

    Zero unknowns (no question) and multiple unknowns (ambiguous target) both REFUSE
    — the caller must not pick one. ``comprehend_quantitative`` always emits exactly
    one; this guards every other construction path (wrong=0 at the consumer boundary).
    """
    return graph.unknowns[0] if len(graph.unknowns) == 1 else None


class _QReject(Exception):
    """Internal: a clause matched a shape but is not honestly readable."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.refusal = Refusal(reason, detail)


def _ident(tok: str, detail: str) -> str:
    w = tok.strip().lower()
    if not w.isidentifier():
        raise _QReject("non_identifier_name", detail)
    return w


def _int(tok: str, detail: str) -> int:
    if not tok.isdigit():
        raise _QReject("non_digit_quantity", detail)
    return int(tok)


@dataclass(frozen=True, slots=True)
class _Fact:
    entity: str
    value: int
    unit: str


@dataclass(frozen=True, slots=True)
class _Eq:
    entity: str
    ref: str
    delta: int
    op: str  # "add" | "subtract"
    unit: str


@dataclass(frozen=True, slots=True)
class _Mul:
    """Multiplicative comparative: entity = factor * ref (R1)."""

    entity: str
    ref: str
    factor: int
    unit: str


#: Word factors for "twice/double/triple ... as many". 'half' (a /2, the divide path)
#: is deliberately ABSENT — divide-by-literal is a separate admissibility path, deferred.
_FACTOR_WORDS: dict[str, int] = {"twice": 2, "double": 2, "triple": 3, "quadruple": 4}


def _try_multiplicative(entity: str, toks: list[str], detail: str) -> "_Mul | None":
    """Match "Y has <factor-word> as many <unit> as X" or "Y has <N> times as many
    <unit> as X" → ``_Mul``. Returns None if the clause is not multiplicative (the
    caller then tries the digit-led fact/additive templates)."""
    # [Y, has, FACTORWORD, as, many, UNIT, as, X]
    if (
        len(toks) == 8
        and toks[2] in _FACTOR_WORDS
        and toks[3] == "as"
        and toks[4] == "many"
        and toks[6] == "as"
    ):
        return _Mul(entity, _ident(toks[7], detail), _FACTOR_WORDS[toks[2]],
                    _resolve_unit(_ident(toks[5], detail)))
    # [Y, has, N, times, as, many, UNIT, as, X]
    if (
        len(toks) == 9
        and toks[2].isdigit()
        and toks[3] == "times"
        and toks[4] == "as"
        and toks[5] == "many"
        and toks[7] == "as"
    ):
        return _Mul(entity, _ident(toks[8], detail), int(toks[2]),
                    _resolve_unit(_ident(toks[6], detail)))
    return None


def _parse_sentence(body: str, detail: str):
    """Return a (_Fact | _Eq | _Mul | ('query', entity, unit) | ('sumquery', parts, unit))
    spec, or None if the sentence matches no arithmetic template."""
    toks = body.strip().lower().rstrip("?.!").split()
    if not toks:
        return None

    if len(toks) >= 5 and toks[0] == "how" and toks[1] == "many" and toks[-1] == "have":
        unit = _resolve_unit(_ident(toks[2], detail))
        rest = toks[3:-1]  # between "<unit>" and "have"
        if rest and rest[0] == "does" and len(rest) == 2:
            return ("query", _ident(rest[1], detail), unit)
        if rest and rest[0] == "do":
            parts = [_ident(t, detail) for t in rest[1:] if t != "and"]
            if len(parts) >= 2:
                return ("sumquery", tuple(parts), unit)
        raise _QReject("unreadable_quantity_query", detail)

    if len(toks) >= 4 and toks[1] == "has":
        entity = _ident(toks[0], detail)
        # Multiplicative comparative is checked BEFORE the digit gate (its factor may be
        # a word like "twice", which is not a digit).
        mul = _try_multiplicative(entity, toks, detail)
        if mul is not None:
            return mul
        value = _int(toks[2], detail)
        if len(toks) == 4:
            return _Fact(entity, value, _resolve_unit(_ident(toks[3], detail)))
        if len(toks) == 7 and toks[3] in ("more", "fewer") and toks[5] == "than":
            op = "add" if toks[3] == "more" else "subtract"
            return _Eq(
                entity, _ident(toks[6], detail), value, op, _resolve_unit(_ident(toks[4], detail))
            )
        raise _QReject("unreadable_quantity_clause", detail)

    return None


def _span(text: str) -> SourceSpanLink:
    return SourceSpanLink(source_id="input", start=0, end=max(1, len(text)), text=text or " ")


def comprehend_quantitative(text: str, source_id: str = "input") -> QuantComprehension | Refusal:
    """Comprehend arithmetic prose into a binding_graph + asked entity, or refuse."""
    if not text or not text.strip():
        return Refusal("empty")
    sentences = _split_sentences(text)
    if not sentences:
        return Refusal("empty")

    facts: list[_Fact] = []
    eqs: list[_Eq] = []
    muls: list[_Mul] = []
    queries: list[tuple] = []

    try:
        for body, _terminator, _start, _end in sentences:
            spec = _parse_sentence(body, body)
            if spec is None:
                return Refusal("no_quantity_template", body)
            if isinstance(spec, _Fact):
                facts.append(spec)
            elif isinstance(spec, _Eq):
                eqs.append(spec)
            elif isinstance(spec, _Mul):
                muls.append(spec)
            else:
                queries.append(spec)
    except _QReject as rej:
        return rej.refusal

    if len(queries) != 1 or not facts:
        return Refusal("no_single_quantity_query")

    unit_of: dict[str, str] = {}
    role_of: dict[str, str] = {}
    for f in facts:
        unit_of[f.entity], role_of[f.entity] = f.unit, "count"
    for e in eqs:
        unit_of[e.entity], role_of[e.entity] = e.unit, "count"
    for m in muls:
        unit_of[m.entity], role_of[m.entity] = m.unit, "count"

    query = queries[0]
    sum_eq: tuple[str, tuple[str, ...]] | None = None
    if query[0] == "query":
        ask_entity, ask_unit = query[1], query[2]
    else:  # sumquery -> synthesize a total symbol + sum equation
        parts, ask_unit = query[1], query[2]
        ask_entity = "total"
        unit_of.setdefault(ask_entity, ask_unit)
        role_of[ask_entity] = "total"
        sum_eq = (ask_entity, parts)

    referenced: set[str] = set()
    for f in facts:
        referenced.add(f.entity)
    for e in eqs:
        referenced.update((e.entity, e.ref))
    for m in muls:
        referenced.update((m.entity, m.ref))
    if sum_eq is not None:
        referenced.add(sum_eq[0])
        referenced.update(sum_eq[1])
    referenced.add(ask_entity)

    symbols = [
        SymbolBinding(
            symbol_id=sid,
            name=sid,
            semantic_role=role_of.get(sid, "count"),
            source_span=_span(sid),
            introduced_by=_INTRODUCED_BY,
            entity=sid,
            unit=unit_of.get(sid),
        )
        for sid in sorted(referenced)
    ]
    symbols_by_id = {s.symbol_id: s for s in symbols}

    bound_facts = tuple(
        BoundFact(symbol_id=f.entity, value=str(f.value), source_span=_span(f.entity), unit=f.unit)
        for f in facts
    )

    # The typed expression IR (PR-4) is the SOURCE OF MEANING; rhs_canonical / dependencies
    # / operation_kind are all derived from it, never recovered by re-parsing the string.
    expr_specs: list[tuple[str, Expr]] = [
        (e.entity, (Add if e.op == "add" else Sub)(Symbol(e.ref), Literal(e.delta)))
        for e in eqs
    ]
    expr_specs.extend(
        (m.entity, Mul(Symbol(m.ref), Literal(m.factor))) for m in muls
    )
    if sum_eq is not None:
        lhs, parts = sum_eq
        expr_specs.append((lhs, SumOf(tuple(Symbol(p) for p in parts))))

    # equations: shell -> REAL admissibility -> rebuild (NEVER stamp "admitted").
    equations: list[BoundEquation] = []
    for lhs, expr in expr_specs:
        rhs = to_canonical_string(expr)
        deps = dependencies(expr)
        op = operation_kind(expr)
        shell = BoundEquation(
            lhs_symbol_id=lhs,
            rhs_canonical=rhs,
            dependencies=deps,
            operation_kind=op,
            unit_proof="pending",
            admissibility_status="pending",
            source_span=_span(lhs),
        )
        try:
            proof = check_admissibility(shell, symbols=symbols_by_id)
        except AdmissibilityError as exc:
            return Refusal("admissibility_refused", f"{lhs}: {exc.reason}")
        equations.append(
            BoundEquation(
                lhs_symbol_id=lhs,
                rhs_canonical=rhs,
                dependencies=deps,
                operation_kind=op,
                unit_proof=proof.to_canonical_string(),
                admissibility_status="admitted",
                source_span=_span(lhs),
            )
        )

    # The question target lives INSIDE the graph (ADR-0135): a BoundUnknown bound to
    # the asked symbol at the terminal state. The form is "total" for an aggregate
    # query ("how many do X and Y have"), else "count". ``query`` is retained as a
    # consistent-by-construction convenience for the existing relational_metric
    # projection + realize path; a follow-up collapses it onto graph.unknowns.
    unknown = BoundUnknown(
        symbol_id=ask_entity,
        question_span=_span(ask_entity),
        state_index="terminal",
        question_form="total" if sum_eq is not None else "count",
        expected_unit=ask_unit,
    )

    try:
        graph = SemanticSymbolicBindingGraph(
            symbols=tuple(symbols),
            facts=bound_facts,
            equations=tuple(equations),
            unknowns=(unknown,),
        )
    except Exception as exc:  # noqa: BLE001 — surface construction refusal
        return Refusal("invalid_binding_graph", repr(exc))

    return QuantComprehension(binding_graph=graph, equation_exprs=tuple(expr_specs))


def to_relational_metric(
    comp: QuantComprehension,
) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    """Project the comprehension into ``(relations, query)`` for
    ``evals.relational_metric.oracle.oracle_answer``.

    Reads the typed expression IR (``comp.equation_exprs``) directly — meaning is NEVER
    recovered by re-parsing ``rhs_canonical`` (PR-4). Facts are emitted before equations
    and equations in dependency order, so the oracle's forward substitution never hits an
    unresolved reference. A relation shape the projection does not handle REFUSES.
    """
    graph = comp.binding_graph
    relations: list[dict[str, Any]] = [
        {"kind": "fact", "entity": f.symbol_id, "value": int(f.value)} for f in graph.facts
    ]
    for lhs, expr in comp.equation_exprs:
        rel = to_relation(lhs, expr)
        if rel is None:
            return None  # unhandled equation shape -> refuse
        relations.append(rel)
    if not relations:
        return None
    target = single_unknown(graph)
    if target is None:
        return None  # no/ambiguous question target -> refuse (never pick one)
    return relations, {"entity": target.symbol_id, "unit": target.expected_unit}
