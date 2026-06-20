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
        BoundRelation,
        GroundedScalar,
        GroundedMention,
        GroundedUnit,
        MentionBinding,
        CandidateRelation,
        KernelHazard,
        KernelProvenance,
        SourceSpan,
    )
    from language_packs.scalar_equivalence import ScalarCandidate
    from generate.process_frames import ProcessFrame
    from generate.construction_affordances import ConstructionProposal


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
class BoundQuestionTarget:
    """Question target grounded to a mention, or explicitly unresolved."""

    target_type: str
    requested_surface: str
    target_mention_id: str | None
    unknown_slot: str
    evidence_spans: tuple[SourceSpan, ...]
    target_operator: str = "unknown"
    target_state: str = "unknown"
    target_direction: str = "unknown"

    def __post_init__(self) -> None:
        valid_types = {"count", "difference", "remaining", "total", "unknown"}
        valid_operators = {"count", "difference", "comparison", "unknown"}
        valid_states = {"aggregate", "current", "delta", "final", "initial", "unknown"}
        valid_directions = {"decrease", "forward", "inverse", "remaining", "unknown"}
        if self.target_type not in valid_types:
            raise ValueError(
                f"BoundQuestionTarget.target_type must be one of {sorted(valid_types)}, "
                f"got {self.target_type!r}"
            )
        if self.target_operator not in valid_operators:
            raise ValueError(
                "BoundQuestionTarget.target_operator must be one of "
                f"{sorted(valid_operators)}, got {self.target_operator!r}"
            )
        if self.target_state not in valid_states:
            raise ValueError(
                "BoundQuestionTarget.target_state must be one of "
                f"{sorted(valid_states)}, got {self.target_state!r}"
            )
        if self.target_direction not in valid_directions:
            raise ValueError(
                "BoundQuestionTarget.target_direction must be one of "
                f"{sorted(valid_directions)}, got {self.target_direction!r}"
            )
        if self.target_operator == "difference" and self.target_state != "delta":
            raise ValueError("difference targets must bind a delta target_state")
        if self.target_state == "delta" and self.target_operator != "difference":
            raise ValueError("delta targets must use the difference operator")
        if self.target_direction == "decrease" and self.target_operator != "difference":
            raise ValueError("decrease-directed targets must use the difference operator")

    @property
    def grounded(self) -> bool:
        return self.target_mention_id is not None


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
    mentions: tuple[GroundedMention, ...] = ()
    bindings: tuple[MentionBinding, ...] = ()
    bound_relations: tuple[BoundRelation, ...] = ()
    bound_question_target: BoundQuestionTarget | None = None
    proposals: tuple[ConstructionProposal, ...] = ()


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
        self._mentions: list[GroundedMention] = []
        self._bindings: list[MentionBinding] = []
        self._bound_relations: list[BoundRelation] = []
        self._bound_question_target: BoundQuestionTarget | None = None
        self._proposals: list[ConstructionProposal] = []

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

    def add_mention(self, mention: GroundedMention) -> None:
        self._mentions.append(mention)

    def add_binding(self, binding: MentionBinding) -> None:
        self._bindings.append(binding)

    def add_bound_relation(self, relation: BoundRelation) -> None:
        self._bound_relations.append(relation)

    def set_bound_question_target(self, target: BoundQuestionTarget) -> None:
        self._bound_question_target = target

    def add_proposal(self, proposal: ConstructionProposal) -> None:
        self._proposals.append(proposal)

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
            mentions=tuple(self._mentions),
            bindings=tuple(self._bindings),
            bound_relations=tuple(self._bound_relations),
            bound_question_target=self._bound_question_target,
            proposals=tuple(self._proposals),
        )
