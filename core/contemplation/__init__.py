"""Read-only contemplation loop primitives.

ADR-0080: contemplation can emit speculative findings about current
substrate/report evidence, but it cannot ratify, promote, or mutate packs.
"""

from .runner import contemplate_frontier_reports, run_contemplation
from .schema import (
    ContemplationEvidenceRef,
    ContemplationFinding,
    ContemplationRun,
    FindingKind,
)
from .snapshot import ContemplationSubstrate

__all__ = [
    "ContemplationEvidenceRef",
    "ContemplationFinding",
    "ContemplationRun",
    "ContemplationSubstrate",
    "FindingKind",
    "contemplate_frontier_reports",
    "run_contemplation",
]
