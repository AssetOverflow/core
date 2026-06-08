"""Exact integer combined-rate solver (CMB-b).

Solves the queried slot of a :class:`CombinedRateProblem` over the **effective rate** —

```text
effective_rate = rate_a + rate_b            (combine_mode == "sum")
effective_rate = rate_a - rate_b            (combine_mode == "difference")
query effective_rate:  return effective_rate          (well-defined even if <= 0)
query quantity:        effective_rate × time          (exact int)
query time:            quantity ÷ effective_rate       (exact int or REFUSE)
```

Two refusals, the closed CMB solver taxonomy:

- ``non_positive_net_rate`` — a ``quantity`` or ``time`` query whose net rate is ``<= 0`` cannot
  accumulate or finish (and guards the ``eff == 0`` time query from dividing by zero). The
  ``effective_rate`` query is exempt: the net rate is a well-defined answer even when ``<= 0``.
- ``non_integer_solution`` — a ``time`` query that does not divide exactly; never rounds.

Pure integer arithmetic — **no float, no Fraction** (CMB v1 crosses no units, so no rational
conversion is needed; the reader will refuse cross-unit problems, CMB-c). Off-serving (imports no
``generate.derivation`` / ``core.reliability_gate``); deterministic. This is the runtime solver; the
oracle's ``_canonical_outcome`` is a separate gold-coherence path. Note both this solver and
``_canonical_outcome`` delegate the net-rate arithmetic to ``model.effective_rate``, so the
solver lane grades the solver against the *committed static gold*, and the hand-computed literal
tests (``test_literal_grid_values``, plus the inline ``(rate_a ± rate_b) × time`` in
``test_quantity_query_is_always_integral``) — **not** path-independence — are the anchor against a
shared ``effective_rate`` bug.
"""

from __future__ import annotations

from generate.combined_rate_comprehension.model import CombinedRateProblem
from generate.meaning_graph.reader import Refusal


def solve_combined_rate(problem: CombinedRateProblem) -> int | Refusal:
    """Solve the queried slot exactly over the effective rate, or refuse with the closed taxonomy."""
    eff = problem.effective_rate
    if problem.query == "effective_rate":
        return eff  # the net rate is the answer, well-defined even when <= 0
    if eff <= 0:
        return Refusal("non_positive_net_rate", f"effective_rate={eff}")
    if problem.query == "quantity":
        assert problem.time is not None  # guaranteed by the model's per-query slot guard
        return eff * problem.time
    # query == "time": exact integer division in the rate's denominator unit, or refuse.
    assert problem.quantity is not None
    if problem.quantity % eff != 0:
        return Refusal("non_integer_solution", f"{problem.quantity}/{eff}")
    return problem.quantity // eff


__all__ = ["solve_combined_rate"]
