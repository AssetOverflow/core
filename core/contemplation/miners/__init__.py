"""Read-only contemplation miners."""

from .contradiction_detection import mine_contradiction_detection_report
from .frontier_compare import mine_frontier_compare_report

__all__ = [
    "mine_contradiction_detection_report",
    "mine_frontier_compare_report",
]
