"""ProblemFrame skeleton — intermediate representation (IR) skeleton.

Tranche 1 — broad base-layer foundations.

Defines the target IR shape for future cognitive and math derivation organs.
Allows representing problem state and candidate structures without triggering
arithmetic solvers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from generate.kernel_facts import (
        GroundedScalar,
        GroundedUnit,
        CandidateRelation,
        KernelHazard,
        KernelProvenance,
    )
    from language_packs.scalar_equivalence import ScalarCandidate
    from generate.process_frames import ProcessFrame


@dataclass(frozen=True, slots=True)
class QuestionTarget:
    """Declared question target of a problem."""
    surface: str
    target_type: str  # "quantity" | "count" | "comparison" | "unknown"
    unit: str | None = None

    def __post_init__(self) -> None:
        valid_types = {"quantity", "count", "comparison", "unknown"}
        if self.target_type not in valid_types:
            raise ValueError(
                f"QuestionTarget.target_type must be one of {sorted(valid_types)}, "
                f"got {self.target_type!r}"
            )


@dataclass(frozen=True, slots=True)
class ProblemFrame:
    """Immutable target representation of a mathematical word problem.

    Accumulates facts, units, actors, objects, candidate relations,
    process frames, hazards, and question targets.
    """
    quantities: tuple[GroundedScalar, ...]
    scalars: tuple[ScalarCandidate, ...]
    units: tuple[GroundedUnit, ...]
    actors: tuple[str, ...]
    objects: tuple[str, ...]
    candidate_relations: tuple[CandidateRelation, ...]
    process_frames: tuple[ProcessFrame, ...]
    question_target: QuestionTarget | None
    hazards: tuple[KernelHazard, ...]
    provenance: tuple[KernelProvenance, ...]


class ProblemFrameBuilder:
    """Mutable builder that produces an immutable ProblemFrame."""

    def __init__(self) -> None:
        self._quantities: list[GroundedScalar] = []
        self._scalars: list[ScalarCandidate] = []
        self._units: list[GroundedUnit] = []
        self._actors: list[str] = []
        self._objects: list[str] = []
        self._candidate_relations: list[CandidateRelation] = []
        self._process_frames: list[ProcessFrame] = []
        self._question_target: QuestionTarget | None = None
        self._hazards: list[KernelHazard] = []
        self._provenance: list[KernelProvenance] = []

    def add_quantity(self, scalar: GroundedScalar) -> None:
        """Add a GroundedScalar to the frame, collecting hazards and provenance."""
        self._quantities.append(scalar)
        if scalar.provenance:
            self._provenance.append(scalar.provenance)
        for h in scalar.hazards:
            self._hazards.append(h)

    def add_scalar(self, scalar: ScalarCandidate) -> None:
        """Add a ScalarCandidate to the frame."""
        self._scalars.append(scalar)

    def add_unit(self, unit: GroundedUnit) -> None:
        """Add a GroundedUnit to the frame, collecting its provenance."""
        self._units.append(unit)
        if unit.provenance:
            self._provenance.append(unit.provenance)

    def add_actor(self, actor: str) -> None:
        """Add an actor to the frame."""
        self._actors.append(actor)

    def add_object(self, obj: str) -> None:
        """Add an object to the frame."""
        self._objects.append(obj)

    def add_relation(self, rel: CandidateRelation) -> None:
        """Add a CandidateRelation, collecting its hazards and provenance."""
        self._candidate_relations.append(rel)
        if rel.provenance:
            self._provenance.append(rel.provenance)
        for h in rel.hazards:
            self._hazards.append(h)

    def add_process_frame(self, frame: ProcessFrame) -> None:
        """Add a ProcessFrame to the frame."""
        self._process_frames.append(frame)

    def set_question_target(self, target: QuestionTarget) -> None:
        """Set the question target of the frame."""
        self._question_target = target

    def add_hazard(self, hazard: KernelHazard) -> None:
        """Add a hazard annotation directly to the frame."""
        self._hazards.append(hazard)

    def add_provenance(self, provenance: KernelProvenance) -> None:
        """Add a provenance record directly to the frame."""
        self._provenance.append(provenance)

    def build(self) -> ProblemFrame:
        """Produce the immutable ProblemFrame."""
        return ProblemFrame(
            quantities=tuple(self._quantities),
            scalars=tuple(self._scalars),
            units=tuple(self._units),
            actors=tuple(self._actors),
            objects=tuple(self._objects),
            candidate_relations=tuple(self._candidate_relations),
            process_frames=tuple(self._process_frames),
            question_target=self._question_target,
            hazards=tuple(self._hazards),
            provenance=tuple(self._provenance),
        )
