"""Independent dimensional oracle — the gold for the dimensional-reasoning lane.

This is **deliberately a second, independent decision procedure** for "what is the
dimension of ``left <op> right``?". It carries its **own** unit→base-exponent table
and its **own** exponent arithmetic and canonical-string renderer, and shares
**no code** with :mod:`generate.binding_graph.units` (the system under test). Two
independent dimensional reasoners agreeing on the same cases is real evidence the
interlingua's unit algebra is correct; a shared-code "oracle" would only prove the
algebra agrees with itself (INV-25).

Base-dimension order matches the SUT's so the rendered strings are directly
comparable (the comparison is about the *decision*, not the spelling).
"""

from __future__ import annotations

from typing import Final

# Same axis order as the SUT's BASE_DIMENSIONS so canonical strings line up.
_BASE: Final[tuple[str, ...]] = ("length", "time", "mass", "money", "count", "temperature")

# An INDEPENDENT unit→base-exponent table (hand-authored; NOT the en_units_v1 pack
# the SUT reads). Only concrete base units; composites are resolved structurally.
_UNIT_DIMS: Final[dict[str, dict[str, int]]] = {
    "meter": {"length": 1}, "mile": {"length": 1}, "foot": {"length": 1},
    "second": {"time": 1}, "hour": {"time": 1}, "minute": {"time": 1}, "day": {"time": 1},
    "kilogram": {"mass": 1}, "pound": {"mass": 1},
    "dollar": {"money": 1},
    "degree": {"temperature": 1},
}


class OracleError(ValueError):
    """Unit outside the oracle's independent vocabulary — refuse, never guess."""


def _depluralize(unit: str) -> str:
    """Independent conservative plural strip (mirrors the SUT's contract, own code)."""
    if unit in _UNIT_DIMS:
        return unit
    for cand in (
        unit[:-3] + "y" if unit.endswith("ies") and len(unit) > 3 else "",
        unit[:-2] if unit.endswith("es") and len(unit) > 2 else "",
        unit[:-1] if unit.endswith("s") and len(unit) > 1 else "",
    ):
        if cand and cand in _UNIT_DIMS:
            return cand
    return unit


def _vector(unit: str) -> tuple[int, ...]:
    """Resolve a unit id (incl. plural and ``X_per_Y`` composites) to an exponent
    tuple over ``_BASE``. Raises :class:`OracleError` on anything else."""
    if not isinstance(unit, str) or not unit:
        raise OracleError(f"empty unit: {unit!r}")
    canon = _depluralize(unit)
    if canon in _UNIT_DIMS:
        dims = _UNIT_DIMS[canon]
        return tuple(dims.get(b, 0) for b in _BASE)
    if "_per_" in unit:
        num, _, denom = unit.partition("_per_")
        nv = _vector(num)
        dv = _vector(denom)
        return tuple(a - b for a, b in zip(nv, dv))
    raise OracleError(f"unknown_unit: {unit!r}")


def _render(exps: tuple[int, ...]) -> str:
    """Canonical dimension string, format-compatible with the SUT's renderer."""
    nums: list[str] = []
    dens: list[str] = []
    for dim, e in zip(_BASE, exps):
        if e > 0:
            nums.append(dim if e == 1 else f"{dim}^{e}")
        elif e < 0:
            dens.append(dim if e == -1 else f"{dim}^{-e}")
    if not nums and not dens:
        return "dimensionless"
    num_part = "*".join(nums) if nums else "1"
    return num_part if not dens else f"{num_part}/{'*'.join(dens)}"


def dimensional_result(op: str, left: str, right: str) -> str:
    """The oracle verdict: the canonical dimension of ``left <op> right``.

    ``op`` is ``"product"`` or ``"quotient"``. Returns ``"refused"`` if either
    unit is outside the oracle's vocabulary or ``op`` is unknown — the same
    refusal posture as the SUT.
    """
    try:
        lv = _vector(left)
        rv = _vector(right)
    except OracleError:
        return "refused"
    if op == "product":
        return _render(tuple(a + b for a, b in zip(lv, rv)))
    if op == "quotient":
        return _render(tuple(a - b for a, b in zip(lv, rv)))
    return "refused"
