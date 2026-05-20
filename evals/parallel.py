"""Compatibility helper for legacy parallel eval runners.

This preserves the original ``workers=`` API used by the older lanes
while the new worker-initialized helper lives in :mod:`evals._parallel`.
"""

from __future__ import annotations

import multiprocessing as mp
import os
from collections.abc import Callable
from typing import Any, TypeVar

_R = TypeVar("_R")
_MP_CONTEXT = mp.get_context("spawn")


def _default_workers() -> int:
    detected = os.cpu_count() or 4
    return max(1, min(detected, 8))


def run_cases_parallel(
    cases: list[dict[str, Any]],
    run_case_fn: Callable[[dict[str, Any]], _R],
    *,
    workers: int | None = None,
) -> list[_R]:
    """Run cases in parallel with the legacy per-case callable API."""
    if not cases:
        return []

    n = workers if workers is not None else _default_workers()
    if n <= 1:
        return [run_case_fn(c) for c in cases]

    with _MP_CONTEXT.Pool(processes=n) as pool:
        return list(pool.imap(run_case_fn, cases))


__all__ = ["run_cases_parallel"]
