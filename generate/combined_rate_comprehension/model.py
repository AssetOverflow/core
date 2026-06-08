"""Typed model for a combined-rate problem (CMB-a).

A combined-rate problem is two explicit rates over one shared unit, combined by an explicit mode,
then single-rate algebra over the result:

```text
effective_rate = rate_a + rate_b           (combine_mode == "sum")
effective_rate = rate_a - rate_b           (combine_mode == "difference")
quantity       = effective_rate × time     (query == "quantity")
time           = quantity ÷ effective_rate (query == "time")
effective_rate                              (query == "effective_rate")
```

The two rates are **always known** (that is what makes it a combined-rate problem — two explicit
rates); ``rate_unit`` is the single source of unit truth for both. The query selects which derived
slot is asked:

- ``quantity``       — ``time`` is the known, ``quantity`` is the unknown (``None``).
- ``time``           — ``quantity`` is the known, ``time`` is the unknown (``None``).
- ``effective_rate`` — neither ``time`` nor ``quantity`` is needed; both are ``None``.

Pure data with a structural guard: the two rates must be present, and exactly the slots the query
licenses are known/unknown (illegal states — a missing rate, the wrong slot unknown, an
over-specified ``effective_rate`` query — cannot be represented).

The two rates and the known time/quantity are **positive ints** — a non-positive rate or a
non-positive duration/quantity is nonsensical and cannot be represented (so the solver can never
receive a path that yields a negative answer). The *net* rate, by contrast, MAY be ``<= 0``:
``effective_rate`` is derived (a property), and for ``difference`` mode with ``rate_a <= rate_b``
it is ``<= 0``. The model does NOT refuse that — a non-positive net rate is the *solver's* boundary
(``non_positive_net_rate``, CMB-b), not a malformed setup. Off-serving; deterministic.
No unit conversion in v1 (``time_unit`` defaults to the rate denominator and the v1 gold never
crosses units).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from generate.combined_rate_comprehension.units import RateUnit

CombineMode = Literal["sum", "difference"]
CombinedRateQuery = Literal["quantity", "time", "effective_rate"]

#: The slots each query licenses as (known, unknown). ``effective_rate`` needs neither time nor
#: quantity; the other two trade exactly one known for one unknown.
_QUERY_SLOTS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "quantity": (frozenset({"time"}), frozenset({"quantity"})),
    "time": (frozenset({"quantity"}), frozenset({"time"})),
    "effective_rate": (frozenset(), frozenset({"time", "quantity"})),
}


@dataclass(frozen=True, slots=True)
class CombinedRateProblem:
    """Two explicit rates over one unit, combined by ``combine_mode``, with one queried slot."""

    rate_a: int
    rate_b: int
    rate_unit: RateUnit
    combine_mode: CombineMode
    time: int | None
    quantity: int | None
    query: CombinedRateQuery
    #: The duration's time unit (forward-compat with conversion). Defaults to the rate denominator;
    #: v1 never crosses units, so it always equals ``rate_unit.denominator`` here.
    time_unit: str | None = None

    def __post_init__(self) -> None:
        if self.time_unit is None:
            object.__setattr__(self, "time_unit", self.rate_unit.denominator)
        for role, value in (("rate_a", self.rate_a), ("rate_b", self.rate_b)):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{role} must be a positive int (two explicit rates); got {value!r}")
        if self.combine_mode not in ("sum", "difference"):
            raise ValueError(f"combine_mode must be 'sum' or 'difference'; got {self.combine_mode!r}")
        if self.query not in _QUERY_SLOTS:
            raise ValueError(f"query must be one of {sorted(_QUERY_SLOTS)}; got {self.query!r}")
        known_slots, unknown_slots = _QUERY_SLOTS[self.query]
        slots: dict[str, int | None] = {"time": self.time, "quantity": self.quantity}
        known = {role for role, value in slots.items() if value is not None}
        if known != known_slots:
            raise ValueError(
                f"query={self.query!r} licenses knowns {sorted(known_slots)}; got {sorted(known)}"
            )
        for role in unknown_slots:
            if slots[role] is not None:
                raise ValueError(f"query={self.query!r}: slot {role!r} must be the unknown (None)")
        for role in known_slots:
            value = slots[role]
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{role} value must be a positive int; got {value!r}")

    @property
    def effective_rate(self) -> int:
        """The combined rate (pure derivation). MAY be ``<= 0`` for ``difference``; the solver,
        not the model, owns the ``non_positive_net_rate`` refusal."""
        if self.combine_mode == "sum":
            return self.rate_a + self.rate_b
        return self.rate_a - self.rate_b

    @property
    def quantity_unit(self) -> str:
        return self.rate_unit.numerator


__all__ = ["CombineMode", "CombinedRateProblem", "CombinedRateQuery"]
