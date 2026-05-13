"""core.physics.articulation — Articulation planning from ReasoningTrajectory.

ADR-0009: Articulation is not generation. The ArticulationPlanner produces
a structured specification (ArticulationPlan) from a ReasoningTrajectory.
Surface realization is the responsibility of a downstream renderer.
Each output segment carries full field provenance.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Tuple


class OutputModality(Enum):
    NATURAL_LANGUAGE = auto()
    CODE = auto()
    STRUCTURED_DATA = auto()
    SCRIPTURE_REFERENCE = auto()
    MATHEMATICAL_EXPRESSION = auto()
    HEBREW = auto()
    KOINE_GREEK = auto()


@dataclass(frozen=True)
class ArticulationSegment:
    """A single output segment with field provenance."""
    segment_id: str
    source_frame_id: str         # BindingFrame this segment derives from
    source_region_ids: Tuple[str, ...]  # field regions expressed by this segment
    confidence: float            # derived from source frame coherence magnitude
    modality: OutputModality
    formatting_constraints: Tuple[str, ...]  # modality-specific constraints


@dataclass(frozen=True)
class ArticulationPlan:
    """Sequenced set of output segments with full field provenance."""
    plan_id: str
    segments: Tuple[ArticulationSegment, ...]
    source_trajectory_id: str
    target_modality: OutputModality
    overall_confidence: float


class ArticulationPlanner:
    """Converts a ReasoningTrajectory into an ArticulationPlan."""

    def plan(
        self,
        trajectory,
        modality: OutputModality,
    ) -> ArticulationPlan:
        raise NotImplementedError("ArticulationPlanner.plan: implement plan construction")
