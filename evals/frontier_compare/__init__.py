"""Wave-1 frontier comparison benchmarks for CORE.

The package is intentionally provider-free: it benchmarks CORE's native
runtime on deterministic, traceable tasks and emits a stable JSON report
that later provider adapters can match.
"""

from .runner import run_suite, run_all

__all__ = ["run_suite", "run_all"]
