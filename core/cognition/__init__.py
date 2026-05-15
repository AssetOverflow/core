"""
core.cognition — the cognitive spine.

Exports the public surface of the pipeline layer.
"""

from core.cognition.pipeline import CognitiveTurnPipeline
from core.cognition.result import CognitiveTurnResult
from core.cognition.trace import compute_trace_hash

__all__ = [
    "CognitiveTurnPipeline",
    "CognitiveTurnResult",
    "compute_trace_hash",
]
