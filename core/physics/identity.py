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
from typing import Dict, FrozenSet, Tuple


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
        raise NotImplementedError("IdentityCheck.check: implement manifold alignment check")


@dataclass(frozen=True)
class CharacterProfile:
    """Human-readable projection of the IdentityManifold.

    This is not the identity itself. The identity is geometric.
    The CharacterProfile is a representation of it — a map, not the terrain.
    """
    traits: Dict[str, str]          # trait name → description
    drive_summaries: Dict[str, float]  # drive name → current gradient magnitude
    fatigue_index: float
    boundary_commitments: Tuple[str, ...]
    theological_grounding: Dict[str, str]  # axis name → scriptural/philosophical note
