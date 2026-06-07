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
  - query ``How many <unit> do <X> and <Y> have [altogether|in total]`` -> total = X + Y; ask total

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
    Div,
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


@dataclass(frozen=True, slots=True)
class _Div:
    """Divisive comparative: entity = ref / divisor (R1, "half as many"). The
    divisor is a dimensionless integer literal; the quotient keeps ref's unit."""

    entity: str
    ref: str
    divisor: int
    unit: str


@dataclass(frozen=True, slots=True)
class _Partition:
    """Aggregate-then-divide: combine all facts into a ``total`` then split that total
    equally into ``divisor`` parts (R1, "They combine their X and split them equally
    into N boxes"). The semantic source is equal PARTITION; the mathematical setup is
    ``total = sum(facts)`` + ``per_<container> = total / divisor`` — reusing ``SumOf`` +
    ``Div(Symbol, Literal)``, NO new relation kind (the divisor is exact integer
    division, the same wrong=0 boundary as PR-6c)."""

    unit: str       # the unit combined and split (hats -> item)
    divisor: int    # number of equal parts (3 boxes)
    container: str  # SINGULAR container noun (box) — must match the perquery's


def _singular(noun: str) -> str:
    """Conservative singularization for container nouns (``boxes`` -> ``box``,
    ``bags`` -> ``bag``); already-singular nouns (``box``) pass through unchanged.

    Used ONLY to canonicalize the partition container so the "split into N boxes"
    sentence and the "in each box" query name the same ``per_<container>`` symbol.
    """
    if noun.endswith("es") and noun[:-2].endswith(("x", "s", "z", "ch", "sh")):
        return noun[:-2]
    if noun.endswith("s") and len(noun) > 1:
        return noun[:-1]
    return noun


#: Word factors for "twice/double/triple ... as many" (a multiply by a dimensionless int).
_FACTOR_WORDS: dict[str, int] = {"twice": 2, "double": 2, "triple": 3, "quadruple": 4}

#: Word divisors for "half ... as many" (a divide by a dimensionless int). The divisive
#: twin of ``_FACTOR_WORDS``; both slot into the same 8-token "<WORD> as many" template.
#: 'third'/'quarter' (non-power-of-two surface forms with an article) are deferred.
_DIVISOR_WORDS: dict[str, int] = {"half": 2}


def _try_multiplicative(entity: str, toks: list[str], detail: str) -> "_Mul | _Div | None":
    """Match the comparative templates → ``_Mul`` (multiply) or ``_Div`` (divide).

    - "Y has <factor-word> as many <unit> as X"  → ``_Mul`` (twice/double/triple/quadruple)
    - "Y has <divisor-word> as many <unit> as X" → ``_Div`` (half)
    - "Y has <N> times as many <unit> as X"      → ``_Mul``

    Returns None if the clause is not comparative (the caller then tries the digit-led
    fact/additive templates)."""
    # [Y, has, WORD, as, many, UNIT, as, X] — factor and divisor words share this shape.
    if (
        len(toks) == 8
        and toks[3] == "as"
        and toks[4] == "many"
        and toks[6] == "as"
    ):
        ref = _ident(toks[7], detail)
        unit = _resolve_unit(_ident(toks[5], detail))
        if toks[2] in _FACTOR_WORDS:
            return _Mul(entity, ref, _FACTOR_WORDS[toks[2]], unit)
        if toks[2] in _DIVISOR_WORDS:
            return _Div(entity, ref, _DIVISOR_WORDS[toks[2]], unit)
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

    if len(toks) >= 5 and toks[0] == "how" and toks[1] == "many":
        unit = _resolve_unit(_ident(toks[2], detail))
        # "How many <unit> are in each <container>?" -> the partition per-container target.
        if len(toks) == 7 and toks[3] == "are" and toks[4] == "in" and toks[5] == "each":
            return ("perquery", _singular(_ident(toks[6], detail)), unit)
        # An aggregate query may close with a qualifier AFTER "have":
        # "... have altogether?" or "... have in total?". Strip it so the
        # "have"-terminal templates apply; the qualifier is honored ONLY for the
        # multi-part aggregate (sumquery) form, never the single-entity query
        # ("does X have altogether?" is nonsensical -> refuses). It adds no new
        # relation kind: the parts still flow through sum_of, and an ungrounded or
        # unit-incompatible part is refused downstream by admissibility
        # (unit_unbound / unit_mismatch), so the recognizer cannot over-read.
        core, aggregate = toks, False
        if toks[-1] == "altogether":
            core, aggregate = toks[:-1], True
        elif toks[-1] == "total" and toks[-2] == "in":
            core, aggregate = toks[:-2], True
        if core[-1] == "have":
            rest = core[3:-1]  # between "<unit>" and "have"
            if not aggregate and rest and rest[0] == "does" and len(rest) == 2:
                return ("query", _ident(rest[1], detail), unit)
            if rest and rest[0] == "do":
                parts = [_ident(t, detail) for t in rest[1:] if t != "and"]
                if len(parts) >= 2:
                    return ("sumquery", tuple(parts), unit)
        raise _QReject("unreadable_quantity_query", detail)

    # Partition: "They combine their <unit> and split them equally into <N> <container>."
    if (
        len(toks) == 11
        and toks[0] == "they"
        and toks[1] == "combine"
        and toks[2] == "their"
        and toks[4] == "and"
        and toks[5] == "split"
        and toks[6] == "them"
        and toks[7] == "equally"
        and toks[8] == "into"
        and toks[9].isdigit()
    ):
        return _Partition(
            unit=_resolve_unit(_ident(toks[3], detail)),
            divisor=_int(toks[9], detail),
            container=_singular(_ident(toks[10], detail)),
        )

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
    divs: list[_Div] = []
    partitions: list[_Partition] = []
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
            elif isinstance(spec, _Div):
                divs.append(spec)
            elif isinstance(spec, _Partition):
                partitions.append(spec)
            else:
                queries.append(spec)
    except _QReject as rej:
        return rej.refusal

    if len(queries) != 1 or not facts:
        return Refusal("no_single_quantity_query")
    if len(partitions) > 1:
        return Refusal("multiple_partitions")
    partition = partitions[0] if partitions else None

    unit_of: dict[str, str] = {}
    role_of: dict[str, str] = {}
    for f in facts:
        unit_of[f.entity], role_of[f.entity] = f.unit, "count"
    for e in eqs:
        unit_of[e.entity], role_of[e.entity] = e.unit, "count"
    for m in muls:
        unit_of[m.entity], role_of[m.entity] = m.unit, "count"
    for d in divs:
        unit_of[d.entity], role_of[d.entity] = d.unit, "count"

    query = queries[0]
    # A partition is read ONLY together with its "in each <container>" query, and vice
    # versa — a partition without that target, or that target without a partition, refuses.
    if (partition is not None) != (query[0] == "perquery"):
        return Refusal("partition_query_mismatch")

    sum_eq: tuple[str, tuple[str, ...]] | None = None
    partition_eq: tuple[str, str, int] | None = None  # (per_box, total, divisor)
    if query[0] == "query":
        ask_entity, ask_unit = query[1], query[2]
    elif query[0] == "perquery":
        # Aggregate-then-divide: total = sum(all facts); per_<container> = total / divisor.
        container, ask_unit = query[1], query[2]
        assert partition is not None  # guaranteed by the mismatch guard above
        if partition.container != container:
            return Refusal("partition_container_mismatch")
        ask_entity = "per_" + container
        unit_of.setdefault("total", partition.unit)
        role_of["total"] = "total"
        unit_of.setdefault(ask_entity, partition.unit)
        role_of[ask_entity] = "count"
        sum_eq = ("total", tuple(f.entity for f in facts))
        partition_eq = (ask_entity, "total", partition.divisor)
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
    for d in divs:
        referenced.update((d.entity, d.ref))
    if sum_eq is not None:
        referenced.add(sum_eq[0])
        referenced.update(sum_eq[1])
    if partition_eq is not None:
        referenced.add(partition_eq[0])
        referenced.add(partition_eq[1])
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
    expr_specs.extend(
        (d.entity, Div(Symbol(d.ref), Literal(d.divisor))) for d in divs
    )
    if sum_eq is not None:
        lhs, parts = sum_eq
        expr_specs.append((lhs, SumOf(tuple(Symbol(p) for p in parts))))
    # The partition divide is appended AFTER the sum so ``total`` is forward-resolved
    # before ``per_<container> = total / divisor`` (the oracle substitutes in this order).
    if partition_eq is not None:
        lhs, ref, divisor = partition_eq
        expr_specs.append((lhs, Div(Symbol(ref), Literal(divisor))))

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
