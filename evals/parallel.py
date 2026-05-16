"""Parallel case-runner helper for embarrassingly-parallel eval lanes.

The per-case lanes (provenance, calibration, symbolic-logic,
adversarial-identity) each build a fresh ``ChatRuntime`` per case with
no shared state, so they parallelize cleanly across OS processes.

Threading does not help here because the dominant per-case cost is
``ChatRuntime.__init__`` — pure-Python pack loading that holds the GIL.
``multiprocessing.Pool`` gives one runtime per worker and yields ~5–7×
wall-clock speedup on an 8-core machine.

Determinism: each case is independent and the per-case scoring is a
deterministic function of the case spec.  Parallel execution preserves
the same per-case results as serial execution; only the *order* of
returned results may differ, so callers should re-sort by case id or
by the input order before computing ordered metrics.

Usage:
    from evals.parallel import run_cases_parallel

    details = run_cases_parallel(cases, _run_case, workers=None)
    # details is a list ordered to match cases input.

The worker function ``run_case_fn`` must be importable at module level
(picklable).  Closures and lambdas will not work.
"""

from __future__ import annotations

import multiprocessing as mp
import os
from typing import Any, Callable, TypeVar

_R = TypeVar("_R")

# Use 'spawn' so worker processes get a fresh Python interpreter — avoids
# forking heavy parent state (loaded numpy/torch backends, vault caches,
# language pack manifolds) into every child.
_MP_CONTEXT = mp.get_context("spawn")


def _default_workers() -> int:
    # Cap default at a reasonable number; very high parallelism increases
    # per-worker pack-load cost without proportional speedup.
    detected = os.cpu_count() or 4
    return max(1, min(detected, 8))


def run_cases_parallel(
    cases: list[dict[str, Any]],
    run_case_fn: Callable[[dict[str, Any]], _R],
    *,
    workers: int | None = None,
) -> list[_R]:
    """Run cases in parallel using a multiprocessing.Pool.

    Parameters
    ----------
    cases
        List of case dicts.  Each is passed individually to
        ``run_case_fn``.
    run_case_fn
        Module-level (importable, picklable) function that takes one
        case dict and returns a per-case detail dict.
    workers
        Number of worker processes.  Defaults to
        ``min(os.cpu_count(), 8)``.  Set to 1 to force serial execution
        (useful for debugging).

    Returns
    -------
    list[dict]
        Per-case details, in the same order as the input ``cases``.
    """
    if not cases:
        return []

    n = workers if workers is not None else _default_workers()
    if n <= 1:
        return [run_case_fn(c) for c in cases]

    with _MP_CONTEXT.Pool(processes=n) as pool:
        # imap preserves input ordering and starts yielding before all
        # tasks finish, which keeps memory bounded on large lanes.
        return list(pool.imap(run_case_fn, cases))
