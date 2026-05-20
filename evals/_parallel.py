"""Process-parallel eval runner with per-worker warm-up.

The eval lanes in this repository are deliberately embarrassingly
parallel: each case gets a fresh runtime in its own process, so there
is no shared mutable state and no race risk.  The expensive part is
worker-local pack loading, so this helper uses a ``Pool`` initializer
to warm the relevant caches once per worker before any cases run.

The builder passed to :func:`run_cases_parallel` is invoked once per
worker and must return a callable that scores a single case with a
fresh runtime.  Typical builders do two things:

1. Construct one or more warm-up runtimes to populate process-local
   caches.
2. Return a per-case function that instantiates a new runtime for each
   case and computes the case result deterministically.

The helper preserves input order in its returned list.
"""

from __future__ import annotations

import multiprocessing as mp
import os
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

_R = TypeVar("_R")
_CaseRunner = Callable[[Any], _R]
_CaseRunnerBuilder = Callable[[], Callable[[Any], _R]]

_MP_CONTEXT = mp.get_context("spawn")
_WORKER_CASE_RUNNER: _CaseRunner[Any] | None = None


def _default_workers() -> int:
    detected = os.cpu_count() or 4
    return max(1, min(detected, 8))


def normalize_workers(n_workers: int, case_count: int) -> int:
    """Clamp worker count to the active CPU budget and case count."""
    cpu_cap = os.cpu_count() or 1
    return max(1, min(int(n_workers), cpu_cap, max(1, int(case_count))))


def _worker_init(build_runtime_fn: _CaseRunnerBuilder[_R]) -> None:
    """Build the worker-local case runner after caches are warm."""
    global _WORKER_CASE_RUNNER
    _WORKER_CASE_RUNNER = build_runtime_fn()


def _run_case_in_worker(case: Any) -> _R:
    if _WORKER_CASE_RUNNER is None:  # pragma: no cover - defensive guard
        raise RuntimeError("worker case runner was not initialized")
    return _WORKER_CASE_RUNNER(case)


def run_cases_parallel(
    cases: Sequence[Any],
    build_runtime_fn: _CaseRunnerBuilder[_R],
    n_workers: int = 4,
) -> list[_R]:
    """Run ``cases`` in parallel using a worker-initialized process pool.

    ``build_runtime_fn`` is called once per worker.  It should warm any
    worker-local caches and return a callable that scores a single case
    using a fresh runtime.
    """
    if not cases:
        return []

    effective_workers = normalize_workers(n_workers, len(cases))
    if effective_workers <= 1:
        case_runner = build_runtime_fn()
        return [case_runner(case) for case in cases]

    with _MP_CONTEXT.Pool(
        processes=effective_workers,
        initializer=_worker_init,
        initargs=(build_runtime_fn,),
    ) as pool:
        return list(pool.imap(_run_case_in_worker, cases))
