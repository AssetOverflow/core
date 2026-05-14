"""core.physics.articulation — Articulation planning from ReasoningTrajectory.

ADR-0009: Articulation is not generation. The ArticulationPlanner produces
a structured specification (ArticulationPlan) from a ReasoningTrajectory.
Surface realization is the responsibility of a downstream renderer.
Each output segment carries full field provenance.
"""

from __future__ import annotations
import hashlib
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
        segments: list[ArticulationSegment] = []
        for idx, frame in enumerate(trajectory.frames):
            confidence = max(0.0, min(1.0, float(frame.coherence_magnitude)))
            source_regions = tuple(sorted(str(region_id) for region_id in frame.region_ids))
            segment_id = _segment_id(trajectory.trajectory_id, frame.frame_id, idx)
            segments.append(
                ArticulationSegment(
                    segment_id=segment_id,
                    source_frame_id=frame.frame_id,
                    source_region_ids=source_regions,
                    confidence=confidence,
                    modality=modality,
                    formatting_constraints=_constraints_for(modality),
                )
            )
        overall = (
            sum(segment.confidence for segment in segments) / len(segments)
            if segments
            else 0.0
        )
        return ArticulationPlan(
            plan_id=_plan_id(trajectory.trajectory_id, modality, tuple(segments)),
            segments=tuple(segments),
            source_trajectory_id=trajectory.trajectory_id,
            target_modality=modality,
            overall_confidence=overall,
        )


def _constraints_for(modality: OutputModality) -> Tuple[str, ...]:
    if modality is OutputModality.CODE:
        return ("preserve_syntax", "monospace")
    if modality is OutputModality.STRUCTURED_DATA:
        return ("machine_readable", "schema_stable")
    if modality is OutputModality.HEBREW:
        return ("rtl", "preserve_script")
    if modality is OutputModality.KOINE_GREEK:
        return ("polytonic", "preserve_script")
    return ("plain_text",)


def _segment_id(trajectory_id: str, frame_id: str, idx: int) -> str:
    return hashlib.sha256(f"{trajectory_id}:{frame_id}:{idx}".encode("utf-8")).hexdigest()


def _plan_id(trajectory_id: str, modality: OutputModality, segments: Tuple[ArticulationSegment, ...]) -> str:
    h = hashlib.sha256()
    h.update(trajectory_id.encode("utf-8"))
    h.update(modality.name.encode("ascii"))
    for segment in segments:
        h.update(segment.segment_id.encode("utf-8"))
    return h.hexdigest()
