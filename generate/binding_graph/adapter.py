"""ADR-0133 — Adapter: ``MathProblemGraph`` → ``SemanticSymbolicBindingGraph``.

Phase 2 of the binding-graph layer (ADR-0132). This module is a pure,
deterministic translation: it consumes a ratified
:class:`generate.math_problem_graph.MathProblemGraph` (ADR-0115) and
emits the corresponding
:class:`generate.binding_graph.SemanticSymbolicBindingGraph`. No I/O, no
parser calls, no solver calls, no algebra. The adapter is total on every
well-formed ``MathProblemGraph`` and refuses (typed :class:`AdapterError`)
otherwise.

Mapping discipline (locked at top of module — see constants):

  - each entity → one ``SymbolBinding`` with ``semantic_role='entity'``,
  - each ``InitialPossession`` → one ``SymbolBinding``
    (``semantic_role='quantity'``) + one ``BoundFact``,
  - each ``Operation`` → one fresh result ``SymbolBinding`` plus one
    ``BoundEquation`` whose ``operation_kind`` is a verbatim passthrough
    of the source op kind (closed vocab is shared by design),
  - the ``Unknown`` → one synthesized ``SymbolBinding``
    (``semantic_role='unknown'``) + one ``BoundUnknown``.

Phases 3+ deferred:

  - unit-aware equation admissibility (Phase 3, ADR-0134),
  - question-target binding refinement (Phase 4),
  - bounded-grammar / B3 integration (Phase 5).

Until Phase 3 lands, every emitted ``BoundEquation`` carries the
placeholder ``unit_proof=PHASE_2_UNIT_PROOF`` and
``admissibility_status='pending'``. This is by design — dimensional
analysis belongs in the next ADR.
"""

from __future__ import annotations

import re
from typing import Final

from generate.math_problem_graph import (
    Comparison,
    MathProblemGraph,
    Operation,
    Quantity,
    Rate,
)

from .model import (
    BindingGraphError,
    BoundEquation,
    BoundFact,
    BoundUnknown,
    SemanticSymbolicBindingGraph,
    SourceSpanLink,
    SymbolBinding,
)

# ---------------------------------------------------------------------------
# Constants — locked mapping discipline (read these before editing logic).
# ---------------------------------------------------------------------------

#: ``source_id`` stamped onto every synthesized ``SourceSpanLink``.
#: ``MathProblemGraph`` carries no native source-span information, so
#: every span the adapter emits is synthetic and shares this id.
SYNTHETIC_SOURCE_ID: Final[str] = "math_problem_graph"

#: ``introduced_by`` stamped onto every ``SymbolBinding`` the adapter
#: emits. Replaying the adapter therefore yields byte-equal symbols.
INTRODUCED_BY: Final[str] = "bind_math_problem_graph"

#: Placeholder ``unit_proof`` for every Phase 2 ``BoundEquation``.
#: Phase 3 (ADR-0134) replaces this with a real dimensional proof token.
PHASE_2_UNIT_PROOF: Final[str] = "deferred_to_phase_3"

#: Every Phase 2 ``BoundEquation`` is emitted ``pending`` — the equation
#: is structurally valid but unit-admissibility has not yet been checked.
PHASE_2_ADMISSIBILITY: Final[str] = "pending"

_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


# ---------------------------------------------------------------------------
# Public error
# ---------------------------------------------------------------------------


class AdapterError(ValueError):
    """Raised on malformed input to :func:`bind_math_problem_graph`.

    Sibling of :class:`generate.binding_graph.BindingGraphError` —
    refusal-first by design. The adapter never silently coerces an
    unrecognized input type.
    """


# ---------------------------------------------------------------------------
# Symbol-id helpers (pure)
# ---------------------------------------------------------------------------


def _slug(text: str) -> str:
    """ASCII-lowercase slug; non-alnum runs collapse to ``_``."""
    return _SLUG_NON_ALNUM.sub("_", text.strip().lower()).strip("_")


def _safe_identifier(text: str, *, prefix: str) -> str:
    """Return ``f"{prefix}_{slug}"``, defaulting to ``prefix + '_x'`` on
    empty slug. Guarantees a valid Python identifier."""
    s = _slug(text)
    if s == "":
        s = "x"
    return f"{prefix}_{s}"


def _entity_symbol_id(entity: str) -> str:
    return _safe_identifier(entity, prefix="entity")


def _quantity_symbol_id(entity: str, unit: str, tick: int) -> str:
    return f"q_{_slug(entity) or 'x'}_{_slug(unit) or 'x'}_t{tick}"


def _op_result_symbol_id(idx: int) -> str:
    return f"op_{idx:03d}_result"


def _unknown_symbol_id(entity: str | None, unit: str) -> str:
    scope = _slug(entity) if entity is not None else "total"
    if scope == "":
        scope = "total"
    unit_slug = _slug(unit) or "x"
    return f"unknown_{scope}_{unit_slug}"


def _span(text: str) -> SourceSpanLink:
    """Synthesize a deterministic ``SourceSpanLink`` for ``text``.

    ``MathProblemGraph`` carries no native span information; Phase 2
    therefore stamps every binding with a synthetic span anchored to
    the rendered surface text. The span is byte-stable per input.
    """
    if not isinstance(text, str) or text == "":
        # Defensive: every caller passes non-empty text. Refuse rather
        # than silently substitute.
        raise AdapterError("synthetic span text must be a non-empty str")
    return SourceSpanLink(
        source_id=SYNTHETIC_SOURCE_ID, start=0, end=len(text), text=text
    )


# ---------------------------------------------------------------------------
# RHS canonicalization (deterministic, string-only — no Polynomial coupling)
# ---------------------------------------------------------------------------


def _format_quantity(q: Quantity) -> str:
    return f"{q.value} {q.unit}"


def _format_rate(r: Rate) -> str:
    return f"{r.value} {r.numerator_unit}/{r.denominator_unit}"


def _format_comparison(c: Comparison) -> str:
    if c.delta is not None:
        return (
            f"{c.direction}({c.reference_actor}, "
            f"delta={_format_quantity(c.delta)})"
        )
    return f"{c.direction}({c.reference_actor}, factor={c.factor})"


def _format_operand(operand: Quantity | Rate | Comparison) -> str:
    if isinstance(operand, Quantity):
        return _format_quantity(operand)
    if isinstance(operand, Rate):
        return _format_rate(operand)
    return _format_comparison(operand)


def _format_rhs(op: Operation) -> str:
    head = f"{op.kind}({op.actor}"
    if op.target is not None:
        head += f"->{op.target}"
    return head + f", {_format_operand(op.operand)})"


def _operand_unit_hint(operand: Quantity | Rate | Comparison) -> str | None:
    """The most relevant unit a dependency lookup should key on.

    Used only for wiring deterministic ``BoundEquation.dependencies``
    against pre-existing t0 symbols. Unit-aware *admissibility* is
    Phase 3.
    """
    if isinstance(operand, Quantity):
        return operand.unit
    if isinstance(operand, Rate):
        return operand.denominator_unit
    if operand.delta is not None:
        return operand.delta.unit
    return None


# ---------------------------------------------------------------------------
# Public adapter
# ---------------------------------------------------------------------------


def bind_math_problem_graph(
    g: object,
) -> SemanticSymbolicBindingGraph:
    """Translate a ``MathProblemGraph`` into a ``SemanticSymbolicBindingGraph``.

    Pure function. Deterministic: ``bind_math_problem_graph(g) ==
    bind_math_problem_graph(g)`` byte-for-byte, and two graphs that
    compare equal (``g1 == g2``) produce two binding graphs that compare
    equal. Input is never mutated (cannot be — ``MathProblemGraph`` is
    frozen — but the contract is asserted by tests).

    Raises :class:`AdapterError` if ``g`` is not a
    :class:`MathProblemGraph`. Every well-formed ``MathProblemGraph``
    produces a well-formed ``SemanticSymbolicBindingGraph`` — the
    adapter is total on the input type's image.
    """
    if not isinstance(g, MathProblemGraph):
        raise AdapterError(
            "bind_math_problem_graph requires a MathProblemGraph; "
            f"got {type(g).__name__}"
        )

    symbols: list[SymbolBinding] = []
    facts: list[BoundFact] = []
    equations: list[BoundEquation] = []
    seen_ids: set[str] = set()

    def _add(sym: SymbolBinding) -> None:
        if sym.symbol_id in seen_ids:
            # Idempotent — same symbol re-emitted from a different
            # construction path collapses cleanly.
            return
        seen_ids.add(sym.symbol_id)
        symbols.append(sym)

    # ---- Entities (order of introduction) ---------------------------------
    for entity in g.entities:
        _add(
            SymbolBinding(
                symbol_id=_entity_symbol_id(entity),
                name=entity,
                semantic_role="entity",
                source_span=_span(entity),
                introduced_by=INTRODUCED_BY,
                entity=entity,
            )
        )

    # ---- Initial state → t0 quantity symbols + grounded facts -------------
    t0_index: dict[tuple[str, str], str] = {}
    for poss in g.initial_state:
        sid = _quantity_symbol_id(poss.entity, poss.quantity.unit, 0)
        span_text = f"{poss.entity}|{poss.quantity.unit}|t0"
        _add(
            SymbolBinding(
                symbol_id=sid,
                name=f"{poss.entity}.{poss.quantity.unit}@t0",
                semantic_role="quantity",
                source_span=_span(span_text),
                introduced_by=INTRODUCED_BY,
                entity=poss.entity,
                unit=poss.quantity.unit,
            )
        )
        facts.append(
            BoundFact(
                symbol_id=sid,
                value=str(poss.quantity.value),
                source_span=_span(span_text),
                unit=poss.quantity.unit,
            )
        )
        t0_index[(poss.entity, poss.quantity.unit)] = sid

    # ---- Operations → fresh result symbol + bound equation ----------------
    for idx, op in enumerate(g.operations):
        result_sid = _op_result_symbol_id(idx)
        op_span_text = f"op{idx:03d}|{op.kind}|{op.actor}"
        _add(
            SymbolBinding(
                symbol_id=result_sid,
                name=f"op{idx}.{op.kind}.{op.actor}",
                semantic_role="quantity",
                source_span=_span(op_span_text),
                introduced_by=INTRODUCED_BY,
                entity=op.actor,
            )
        )

        deps: set[str] = set()
        unit_hint = _operand_unit_hint(op.operand)
        if unit_hint is not None:
            actor_sid = t0_index.get((op.actor, unit_hint))
            if actor_sid is not None:
                deps.add(actor_sid)
            if op.target is not None:
                target_sid = t0_index.get((op.target, unit_hint))
                if target_sid is not None:
                    deps.add(target_sid)
            if isinstance(op.operand, Comparison):
                ref_sid = t0_index.get(
                    (op.operand.reference_actor, unit_hint)
                )
                if ref_sid is not None:
                    deps.add(ref_sid)

        equations.append(
            BoundEquation(
                lhs_symbol_id=result_sid,
                rhs_canonical=_format_rhs(op),
                dependencies=frozenset(deps),
                operation_kind=op.kind,  # passthrough — shared closed vocab
                unit_proof=PHASE_2_UNIT_PROOF,
                admissibility_status=PHASE_2_ADMISSIBILITY,
                source_span=_span(op_span_text),
            )
        )

    # ---- Unknown → synthesized unknown symbol + BoundUnknown --------------
    unk = g.unknown
    unk_sid = _unknown_symbol_id(unk.entity, unk.unit)
    unk_text = (
        f"{unk.entity}|{unk.unit}" if unk.entity is not None else f"total|{unk.unit}"
    )
    _add(
        SymbolBinding(
            symbol_id=unk_sid,
            name=unk_text,
            semantic_role="unknown",
            source_span=_span(unk_text),
            introduced_by=INTRODUCED_BY,
            entity=unk.entity,
            unit=unk.unit,
        )
    )
    unknowns = (
        BoundUnknown(
            symbol_id=unk_sid,
            question_span=_span(unk_text),
            expected_unit=unk.unit,
        ),
    )

    try:
        return SemanticSymbolicBindingGraph(
            symbols=tuple(symbols),
            facts=tuple(facts),
            equations=tuple(equations),
            unknowns=unknowns,
        )
    except BindingGraphError as exc:
        # Cross-collection invariants of ``SemanticSymbolicBindingGraph``
        # are stricter than ``MathProblemGraph``'s own checks. Surface
        # any such failure as an ``AdapterError`` so callers see a single
        # refusal type at the adapter boundary.
        raise AdapterError(
            f"adapter produced an invalid binding graph: {exc}"
        ) from exc
