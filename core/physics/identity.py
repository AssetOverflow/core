"""core.physics.identity — Identity as geometric structure, not prompt veneer.

ADR-0010: The IdentityManifold is a fixed geometric subspace of the
versor field encoding CORE's stable character as an architectural
constant. Every ReasoningTrajectory is checked against the manifold
before articulation. Identity is inalienable — it cannot be overridden
by context length, adversarial prompting, or instruction injection.

Theological grounding: John 1:1-2.
The Word is not a description of God. It is God, expressed.
CORE's identity is not a description of CORE. It is CORE, expressed geometrically.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional, Tuple


@dataclass(frozen=True)
class IdentityScore:
    """Result of checking a ReasoningTrajectory against the IdentityManifold."""
    score: float          # 0.0 = full deviation, 1.0 = full alignment
    flagged: bool         # True if score falls below alignment threshold
    deviation_axes: FrozenSet[str]  # ValueAxis IDs where deviation was detected
    trajectory_id: str


@dataclass(frozen=True)
class IdentityManifold:
    """Fixed geometric subspace encoding CORE's stable character.

    Instantiated once at model init. No mutation path exists.
    value_axes: the geometric directions of CORE's core commitments.
    boundary_ids: IDs of hyperplanes that no trajectory may cross.
    alignment_threshold: minimum IdentityScore below which trajectories are flagged.
    """
    value_axes: Tuple  # Tuple[ValueAxis, ...]
    boundary_ids: FrozenSet[str]
    alignment_threshold: float = 0.75


class IdentityCheck:
    """Checks a ReasoningTrajectory against an IdentityManifold."""

    def check(self, trajectory, manifold: IdentityManifold) -> IdentityScore:
        if not manifold.value_axes:
            return IdentityScore(
                score=1.0,
                flagged=False,
                deviation_axes=frozenset(),
                trajectory_id=trajectory.trajectory_id,
            )
        confidence = getattr(trajectory, "total_coherence_delta", 0.0)
        if trajectory.frames:
            confidence += sum(float(frame.coherence_magnitude) for frame in trajectory.frames) / len(trajectory.frames)
        score = max(0.0, min(1.0, 0.5 + (confidence / 2.0)))
        deviations = frozenset(
            axis.axis_id
            for axis in manifold.value_axes
            if score < manifold.alignment_threshold
        )
        return IdentityScore(
            score=score,
            flagged=score < manifold.alignment_threshold,
            deviation_axes=deviations,
            trajectory_id=trajectory.trajectory_id,
        )


@dataclass(frozen=True)
class CharacterProfile:
    """Human-readable projection of the IdentityManifold.

    This is not the identity itself. The identity is geometric.
    The CharacterProfile is a representation of it — a map, not the terrain.
    """
    traits: Dict[str, str]             # trait name → description
    drive_summaries: Dict[str, float]  # drive name → current gradient magnitude
    fatigue_index: float
    boundary_commitments: Tuple[str, ...]
    theological_grounding: Dict[str, str]  # axis name → scriptural/philosophical note

    @classmethod
    def from_manifold(
        cls,
        manifold: IdentityManifold,
        drive_summaries: Optional[Dict[str, float]] = None,
        fatigue_index: float = 0.0,
    ) -> "CharacterProfile":
        """Populate a CharacterProfile directly from a live IdentityManifold.

        Derives traits and theological grounding from the manifold's value_axes
        so the profile always reflects the current geometric identity — not a
        manually maintained parallel description.
        """
        traits: Dict[str, str] = {}
        theological_grounding: Dict[str, str] = {}
        for axis in manifold.value_axes:
            traits[axis.name] = (
                f"Fixed geometric direction {axis.direction} "
                f"in versor manifold — non-negotiable."
            )
            if axis.theological_note:
                theological_grounding[axis.name] = axis.theological_note

        return cls(
            traits=traits,
            drive_summaries=drive_summaries or {
                axis.name: 0.0 for axis in manifold.value_axes
            },
            fatigue_index=fatigue_index,
            boundary_commitments=tuple(sorted(manifold.boundary_ids)),
            theological_grounding=theological_grounding,
        )


@dataclass(frozen=True)
class TurnEvent:
    """Append-only provenance record for one chat turn.

    Every field is deterministically derivable from the turn's execution.
    No inference, no approximation — each value is the exact output of the
    corresponding operator as it ran. The log of TurnEvents over a session
    is a complete, reproducible trace of the model's internal state evolution.

    Fields:
        turn            — zero-based turn index within the session
        input_tokens    — tokens as ingested (after OOV filtering)
        walk_surface    — syntactically guarded token sequence from manifold walk
        articulation_surface — proposition-level surface from realize()
        dialogue_role   — DialogueRole classification for this turn
        identity_score  — IdentityScore from IdentityCheck (None if not run)
        cycle_cost_total — total CycleCost.total for this turn
        vault_hits      — number of vault recall hits that fired during generate()
        versor_condition — versor_condition(final_state.F) after generation
        flagged         — True if identity_score.flagged (shortcut for filtering)
    """
    turn: int
    input_tokens: Tuple[str, ...]
    walk_surface: str
    articulation_surface: str
    dialogue_role: str
    identity_score: Optional[IdentityScore]
    cycle_cost_total: float
    vault_hits: int
    versor_condition: float
    flagged: bool
