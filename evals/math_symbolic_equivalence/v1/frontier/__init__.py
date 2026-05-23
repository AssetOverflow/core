"""Frontier-baseline comparison harness for B1 (ADR-0131.1.F).

This package pairs CORE's symbolic-equivalence lane result with
frontier-LLM baselines under a deterministic, replay-equivalent
comparison contract. The architecture-aligned claim is not "highest
accuracy" — frontier models score high on canonical polynomial
equivalence — but **refusal correctness** (CORE refuses out-of-scope
inputs with a typed reason; frontier models confabulate) and
**determinism** (CORE produces byte-equal outputs across runs;
frontier outputs vary).

Public entry points:

- :data:`PROVIDERS` — registry of provider adapters.
- :func:`run_frontier` — execute one provider against the B1 dataset.
- :func:`build_comparison` — join CORE + frontier results into the
  comparison JSON shape.
- :data:`ADJACENT_BENCHMARK_CITATIONS` — frozen citations for
  published frontier scores on adjacent benchmarks (MATH-Algebra,
  MATH-500, MMLU mathematics) used as additional context.
"""

from __future__ import annotations

from .baselines import ADJACENT_BENCHMARK_CITATIONS
from .comparison import build_comparison, write_comparison
from .frontier_runner import (
    FrontierRunError,
    PROVIDERS,
    ProviderSpec,
    parse_provider_verdict,
    run_frontier,
)

__all__ = [
    "ADJACENT_BENCHMARK_CITATIONS",
    "FrontierRunError",
    "PROVIDERS",
    "ProviderSpec",
    "build_comparison",
    "parse_provider_verdict",
    "run_frontier",
    "write_comparison",
]
