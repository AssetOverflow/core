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
from typing import Dict, FrozenSet, List, Optional, Tuple


@dataclass(frozen=True)
class IdentityScore:
    """Result of checking a ReasoningTrajectory against the IdentityManifold."""
    score: float          # 0.0 = full deviation, 1.0 = full alignment
    flagged: bool         # True if score falls below alignment threshold
    deviation_axes: FrozenSet[str]  # ValueAxis IDs where deviation was detected
    trajectory_id: str

    # --- Convenience aliases used by runtime, serialiser, and review_trace ---

    @property
    def value(self) -> float:
        """Alias for score — primary scalar alignment value (0.0–1.0)."""
        return self.score

    @property
    def alignment(self) -> float:
        """Fraction of axes that were NOT flagged as deviating.

        1.0 = all axes aligned; 0.0 = all axes deviated.
        When deviation_axes is empty alignment is always 1.0.
        """
        axes = self.deviation_axes
        if not axes:
            return 1.0
        # deviation_axes only contains axes that deviated, but we don't
        # independently track total axis count here.  Use score as proxy:
        # high score → high alignment.
        return self.score

    @property
    def axes_evaluated(self) -> List[str]:
        """Sorted list of deviation_axes IDs — used by the JSONL serialiser."""
        return sorted(self.deviation_axes)


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
    alignment_threshold: float = 0.45


class IdentityCheck:
    """Checks a ReasoningTrajectory against an IdentityManifold.

    The current runtime feeds this checker with lightweight binding frames
    derived from generation field states. Low micro-pack energy should not
    mechanically trip every identity axis. The score remains conservative,
    but axis deviations are now assigned by axis projection rather than by
    bulk-flagging every axis whenever the scalar score misses threshold.
    """

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _mean_frame_coherence(trajectory) -> float:
        if not getattr(trajectory, "frames", None):
            return 0.0
        return sum(
            float(frame.coherence_magnitude) for frame in trajectory.frames
        ) / len(trajectory.frames)

    @staticmethod
    def _axis_projection(axis, trajectory, scalar_score: float) -> float:
        """Deterministically project trajectory evidence onto one value axis.

        Until full geometric value-axis measurement is wired, use available
        trajectory telemetry without pretending every axis was measured the
        same way. Axis directions deterministically weight coherence evidence,
        so traces expose which axis caused a flag rather than listing all axes
        by default.
        """
        direction = tuple(float(x) for x in getattr(axis, "direction", ()) or ())
        if not direction:
            return scalar_score
        direction_norm = sum(abs(x) for x in direction) or 1.0
        directional_weight = sum(abs(x) for x in direction[:3]) / direction_norm
        frame_coherence = IdentityCheck._mean_frame_coherence(trajectory)
        coherence_term = IdentityCheck._clamp01(0.5 + (frame_coherence / 2.0))
        return IdentityCheck._clamp01(
            (0.75 * scalar_score) + (0.25 * directional_weight * coherence_term)
        )

    def check(self, trajectory, manifold: IdentityManifold) -> IdentityScore:
        if not manifold.value_axes:
            return IdentityScore(
                score=1.0,
                flagged=False,
                deviation_axes=frozenset(),
                trajectory_id=trajectory.trajectory_id,
            )
        confidence = float(getattr(trajectory, "total_coherence_delta", 0.0))
        confidence += self._mean_frame_coherence(trajectory)
        score = self._clamp01(0.5 + (confidence / 2.0))
        deviations = frozenset(
            axis.axis_id
            for axis in manifold.value_axes
            if self._axis_projection(axis, trajectory, score) < manifold.alignment_threshold
        )
        return IdentityScore(
            score=score,
            flagged=bool(deviations),
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
        turn                 — zero-based turn index within the session
        input_tokens         — tokens as ingested (after OOV filtering)
        surface              — emitted response surface after runtime selection
        walk_surface         — syntactically guarded token sequence from manifold walk
        articulation_surface — proposition-level surface from realize()
        dialogue_role        — DialogueRole classification for this turn
        identity_score       — IdentityScore from IdentityCheck (None if not run)
        cycle_cost_total     — total CycleCost.total for this turn
        vault_hits           — number of vault recall hits that fired during generate()
        versor_condition     — versor_condition(final_state.F) after generation
        flagged              — True if identity_score.flagged (shortcut for filtering)
        elaboration          — woven walk tokens used in elaborate role (None otherwise)
    """
    turn: int
    input_tokens: Tuple[str, ...]
    surface: str
    walk_surface: str
    articulation_surface: str
    dialogue_role: str
    identity_score: Optional[IdentityScore]
    cycle_cost_total: float
    vault_hits: int
    versor_condition: float
    flagged: bool
    elaboration: Optional[str] = None  # woven walk tokens; populated by SentenceAssembler
