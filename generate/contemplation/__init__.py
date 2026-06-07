"""Contemplation v0 (N6) — a single bounded read -> classify -> terminal -> maybe-emit pass.

Off-serving growth organ over the R1/R2 setup compilers: it turns an unsolved problem into a
typed terminal state and, for genuine coverage gaps only, a proposal-only artifact (N5). No loops,
no daemon, no L10 runtime, no self-modification.
"""

from __future__ import annotations

from generate.contemplation.findings import Finding, Terminal
from generate.contemplation.pass_manager import ContemplationResult, contemplate

__all__ = ["ContemplationResult", "Finding", "Terminal", "contemplate"]
