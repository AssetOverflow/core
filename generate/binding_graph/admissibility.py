"""ADR-0134 — Unit-aware equation admissibility check.

Operates on a single :class:`generate.binding_graph.BoundEquation` plus the
surrounding :class:`generate.binding_graph.SymbolBinding` map. Returns a
:class:`UnitProof` on success; raises :class:`AdmissibilityError` (with a
typed ``reason`` drawn from :data:`ADMISSIBILITY_REASONS`) on refusal.

Refusal-first: unit mismatches **never** silently coerce. The caller (adapter
or hand-built equation pipeline) is expected to translate the typed refusal
into ``BoundEquation.admissibility_status='refused'`` + ``refusal_reason``.

The check is operation-kind dispatched. Operand units are read from dep
:class:`SymbolBinding.unit` strings via :func:`generate.binding_graph.units.parse_unit`
— composite ``X_per_Y`` rate units resolve recursively through the closed
vocabulary. No I/O, no solver, no algebra beyond the integer exponent vector.

Adapter naming conventions (consumed by the divide / apply_rate dispatchers):

  - ``divide``: the dividend dep keeps the actor-quantity id
    (e.g. ``q_sam_dollar_t0``); the divisor dep is a synthesized literal
    whose ``symbol_id`` ends in ``__divisor``.
  - ``apply_rate``: the rate dep is a synthesized symbol with
    ``semantic_role == 'rate'``; the duration dep is the actor's t0
    quantity. Composite rate units (``"<num>_per_<denom>"``) parse via
    :func:`parse_unit`'s composite fallback.

These conventions live in this module's docstring (not adapter.py) because
they are part of the verifier's contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from .model import BoundEquation, SymbolBinding
from .units import (
    DIMENSIONLESS,
    UnitAlgebraError,
    UnitVector,
    parse_unit,
    unit_product,
    unit_quotient,
    units_equal,
)


# ---------------------------------------------------------------------------
# Closed refusal-reason vocabulary
# ---------------------------------------------------------------------------

#: Every :class:`AdmissibilityError` carries a ``reason`` drawn from this
#: closed set. New reasons require an ADR-level decision.
ADMISSIBILITY_REASONS: Final[frozenset[str]] = frozenset(
    {
        "unit_mismatch",
        "unknown_unit",
        "unit_unbound",
        "unknown_symbol",
        "unknown_operation",
        "operand_arity",
        "rate_form_invalid",
    }
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AdmissibilityError(ValueError):
    """Typed refusal raised by :func:`check_admissibility`.

    ``reason`` is one of :data:`ADMISSIBILITY_REASONS`; ``detail`` is a short
    human-readable annotation (symbol_id, conflicting unit, etc.) — never
    secret data.
    """

    __slots__ = ("reason", "detail")

    def __init__(self, reason: str, detail: str = "") -> None:
        if reason not in ADMISSIBILITY_REASONS:
            raise ValueError(
                f"AdmissibilityError.reason must be one of "
                f"{sorted(ADMISSIBILITY_REASONS)}; got {reason!r}"
            )
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


# ---------------------------------------------------------------------------
# UnitProof
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UnitProof:
    """Immutable witness of dimensional consistency for one equation.

    ``lhs_unit`` is the dimensional vector of the result; ``operand_units``
    is the per-dep vector in sorted-symbol-id order; ``operation_kind`` is
    the verbatim equation kind for back-reference.
    """

    operation_kind: str
    lhs_unit: UnitVector
    operand_units: tuple[UnitVector, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.operation_kind, str) or self.operation_kind == "":
            raise ValueError(
                "UnitProof.operation_kind must be a non-empty str"
            )
        if not isinstance(self.lhs_unit, UnitVector):
            raise ValueError("UnitProof.lhs_unit must be a UnitVector")
        if not isinstance(self.operand_units, tuple):
            raise ValueError("UnitProof.operand_units must be a tuple")
        for u in self.operand_units:
            if not isinstance(u, UnitVector):
                raise ValueError(
                    "UnitProof.operand_units entries must be UnitVector"
                )

    def to_canonical_string(self) -> str:
        """Stable, deterministic string for storage in ``BoundEquation.unit_proof``."""
        operands = ",".join(u.to_canonical_string() for u in self.operand_units)
        return (
            f"{self.operation_kind}: "
            f"[{operands}] -> {self.lhs_unit.to_canonical_string()}"
        )


# ---------------------------------------------------------------------------
# Dispatch helpers
# ---------------------------------------------------------------------------


def _resolve_dep_units(
    equation: BoundEquation, symbols: Mapping[str, SymbolBinding]
) -> list[tuple[SymbolBinding, UnitVector]]:
    """Resolve every dep symbol's unit to a :class:`UnitVector`, sorted.

    Sorted by ``symbol_id`` for determinism. Refuses with
    ``unknown_symbol`` / ``unit_unbound`` / ``unknown_unit`` as appropriate.
    """
    resolved: list[tuple[SymbolBinding, UnitVector]] = []
    for dep_id in sorted(equation.dependencies):
        sym = symbols.get(dep_id)
        if sym is None:
            raise AdmissibilityError("unknown_symbol", dep_id)
        if sym.unit is None:
            raise AdmissibilityError("unit_unbound", dep_id)
        try:
            vec = parse_unit(sym.unit)
        except UnitAlgebraError as exc:
            raise AdmissibilityError("unknown_unit", sym.unit) from exc
        resolved.append((sym, vec))
    return resolved


def _check_additive(
    kind: str, dep_units: list[tuple[SymbolBinding, UnitVector]]
) -> UnitProof:
    """All operand units must be equal; lhs unit equals that shared unit."""
    if not dep_units:
        raise AdmissibilityError("operand_arity", f"{kind} requires >=1 operand")
    pivot = dep_units[0][1]
    for sym, vec in dep_units[1:]:
        if not units_equal(vec, pivot):
            raise AdmissibilityError(
                "unit_mismatch",
                f"{sym.symbol_id} != {dep_units[0][0].symbol_id}",
            )
    return UnitProof(
        operation_kind=kind,
        lhs_unit=pivot,
        operand_units=tuple(v for _, v in dep_units),
    )


def _check_compare_multiplicative(
    dep_units: list[tuple[SymbolBinding, UnitVector]],
) -> UnitProof:
    """Ratio of like units. lhs is dimensionless; deps must all cancel."""
    if dep_units:
        pivot = dep_units[0][1]
        for sym, vec in dep_units[1:]:
            if not units_equal(vec, pivot):
                raise AdmissibilityError(
                    "unit_mismatch",
                    f"{sym.symbol_id} != {dep_units[0][0].symbol_id}",
                )
    return UnitProof(
        operation_kind="compare_multiplicative",
        lhs_unit=DIMENSIONLESS,
        operand_units=tuple(v for _, v in dep_units),
    )


def _check_multiply(
    dep_units: list[tuple[SymbolBinding, UnitVector]],
) -> UnitProof:
    if not dep_units:
        raise AdmissibilityError("operand_arity", "multiply requires >=1 operand")
    lhs = DIMENSIONLESS
    for _, v in dep_units:
        lhs = unit_product(lhs, v)
    return UnitProof(
        operation_kind="multiply",
        lhs_unit=lhs,
        operand_units=tuple(v for _, v in dep_units),
    )


def _check_divide(
    dep_units: list[tuple[SymbolBinding, UnitVector]],
) -> UnitProof:
    """Dividend / divisor. Divisor identified by ``__divisor`` suffix.

    Refuses with ``operand_arity`` if dep set is not exactly one dividend
    + one ``*__divisor`` literal. The adapter is responsible for naming.
    """
    if len(dep_units) != 2:
        raise AdmissibilityError(
            "operand_arity", f"divide requires exactly 2 deps; got {len(dep_units)}"
        )
    dividend: UnitVector | None = None
    divisor: UnitVector | None = None
    for sym, vec in dep_units:
        if sym.symbol_id.endswith("__divisor"):
            divisor = vec
        else:
            dividend = vec
    if dividend is None or divisor is None:
        raise AdmissibilityError(
            "operand_arity",
            "divide requires one dividend + one '*__divisor' literal",
        )
    return UnitProof(
        operation_kind="divide",
        lhs_unit=unit_quotient(dividend, divisor),
        operand_units=tuple(v for _, v in dep_units),
    )


def _check_apply_rate(
    dep_units: list[tuple[SymbolBinding, UnitVector]],
) -> UnitProof:
    """Rate (X/Y) × duration (Y) → X. Rate dep identified by semantic_role.

    The rate's denominator dimension must match the duration's dimension;
    otherwise refuse with ``rate_form_invalid``. The lhs is the rate × duration
    product (the Y components cancel by construction when the form is valid).
    """
    if len(dep_units) != 2:
        raise AdmissibilityError(
            "operand_arity",
            f"apply_rate requires exactly 2 deps; got {len(dep_units)}",
        )
    rate_vec: UnitVector | None = None
    duration_vec: UnitVector | None = None
    rate_sym: SymbolBinding | None = None
    for sym, vec in dep_units:
        if sym.semantic_role == "rate":
            rate_vec = vec
            rate_sym = sym
        else:
            duration_vec = vec
    if rate_vec is None or duration_vec is None or rate_sym is None:
        raise AdmissibilityError(
            "rate_form_invalid",
            "apply_rate requires one rate dep + one duration dep",
        )
    # lhs is rate * duration; verify the denominator cancels (i.e. lhs has
    # at most as many negative exponents as rate alone) — otherwise the
    # duration's dimension doesn't line up with rate's denominator.
    lhs = unit_product(rate_vec, duration_vec)
    for rate_e, lhs_e in zip(rate_vec.exponents, lhs.exponents, strict=True):
        if rate_e < 0 and lhs_e < 0:
            # rate carried a negative exponent that the duration failed to
            # cancel — the units don't form ``X/Y * Y = X``.
            raise AdmissibilityError(
                "rate_form_invalid",
                f"duration {duration_vec.to_canonical_string()} does not cancel "
                f"rate denominator in {rate_vec.to_canonical_string()}",
            )
    return UnitProof(
        operation_kind="apply_rate",
        lhs_unit=lhs,
        operand_units=tuple(v for _, v in dep_units),
    )


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def check_admissibility(
    equation: BoundEquation,
    *,
    symbols: Mapping[str, SymbolBinding],
) -> UnitProof:
    """Verify ``equation`` is dimensionally admissible against ``symbols``.

    Dispatches on :attr:`BoundEquation.operation_kind`. Raises
    :class:`AdmissibilityError` (with one of :data:`ADMISSIBILITY_REASONS`)
    on any refusal; returns a :class:`UnitProof` otherwise.

    Pure / deterministic / no I/O. The verifier never mutates ``equation``
    or ``symbols``.
    """
    if not isinstance(equation, BoundEquation):
        raise TypeError(
            f"check_admissibility requires a BoundEquation; "
            f"got {type(equation).__name__}"
        )

    dep_units = _resolve_dep_units(equation, symbols)
    kind = equation.operation_kind

    if kind in ("add", "subtract", "compare_additive", "transfer"):
        return _check_additive(kind, dep_units)
    if kind == "compare_multiplicative":
        return _check_compare_multiplicative(dep_units)
    if kind == "multiply":
        return _check_multiply(dep_units)
    if kind == "divide":
        return _check_divide(dep_units)
    if kind == "apply_rate":
        return _check_apply_rate(dep_units)

    raise AdmissibilityError("unknown_operation", kind)


__all__ = (
    "ADMISSIBILITY_REASONS",
    "AdmissibilityError",
    "UnitProof",
    "check_admissibility",
)
