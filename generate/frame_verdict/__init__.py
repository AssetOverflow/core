"""generate.frame_verdict — the sealed, off-serving closed-world FrameVerdict envelope.

ADR-0222 (ratified #780). The closed-world verdict type + the isolated text-frame
evaluator. Firewalled out of the open-world runtime by INV-31; the open-world spine
(``chat/runtime``, ``session/context``, ``vault/store``) must NEVER reach this package.
This package's own re-exports are its public API; it must NOT be re-exported through
``generate/proof_chain`` or a shared ``generate/__init__`` (INV-31 A3).
"""

from generate.frame_verdict.evaluate import evaluate_frame_verdict
from generate.frame_verdict.perception_adapter import (
    frame_verdict_from_perception_falsification,
)
from generate.frame_verdict.types import (
    ClosedFrame,
    ClosedWorldProof,
    FrameKind,
    FrameVerdict,
    FrameVerdictKind,
    PositiveRefutationKind,
    WorldAssumption,
)

__all__ = [
    "ClosedFrame",
    "ClosedWorldProof",
    "FrameKind",
    "FrameVerdict",
    "FrameVerdictKind",
    "PositiveRefutationKind",
    "WorldAssumption",
    "evaluate_frame_verdict",
    "frame_verdict_from_perception_falsification",
]
