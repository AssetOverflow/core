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
import math
import warnings
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple


@dataclass(frozen=True)
class ValueAxis:
    """Compatibility value-axis shape for identity-gate tests and fixtures.

    Runtime code may also pass core.physics.drive.ValueAxis instances.  The
    identity checker only requires axis_id, name, direction, and optional
    theological_note, so both shapes are accepted.
    """
    name: str
    direction: Tuple[float, ...]
    axis_id: str | None = None
    weight: float = 1.0
    theological_note: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "axis_id", self.axis_id or self.name)
        object.__setattr__(self, "direction", tuple(float(x) for x in self.direction))


@dataclass(frozen=True)
class IdentityScore:
    """Result of checking a ReasoningTrajectory against the IdentityManifold."""
    score: float          # 0.0 = full deviation, 1.0 = full alignment
    flagged: bool         # True if any axis projection fell below alignment threshold
    deviation_axes: FrozenSet[str]  # ValueAxis IDs where deviation was detected
    trajectory_id: str

    @property
    def value(self) -> float:
        """Alias for score — primary scalar alignment value (0.0–1.0)."""
        return self.score

    @property
    def alignment(self) -> float:
        """Fraction of axes that were NOT flagged as deviating."""
        axes = self.deviation_axes
        if not axes:
            return 1.0
        return self.score

    @property
    def axes_evaluated(self) -> List[str]:
        """Sorted list of deviation_axes IDs — used by the JSONL serialiser."""
        return sorted(self.deviation_axes)


@dataclass(frozen=True)
class AxisHedge:
    """Per-axis hedge phrases for ADR-0031 score-decomposition.

    When ``IdentityCheck`` flags one or more axes as deviating, the
    assembler can call out the specific axis instead of using the
    generic hedge.  v1 is English-only; depth-language axis hedges are
    a future ADR.
    """
    strong: str
    soft: str
    qualifier: str


@dataclass(frozen=True)
class SurfacePreferences:
    """Pack-supplied surface phrasing preferences (ADR-0028).

    Drives the assembler's hedge and claim-strength decisions so that
    swapping identity packs produces visibly different surfaces on the
    same prompt.  Defaults preserve the pre-ADR-0028 behavior: the
    legacy ``HEDGE_STRONG_THRESHOLD`` / ``HEDGE_SOFT_THRESHOLD``
    constants and the canned ``"It seems that"`` / ``"Perhaps"`` hedges.

    ``claim_strength`` semantics:

    * ``"balanced"`` — no claim-strength effect outside the hedge band.
    * ``"qualified"`` — when alignment falls in
      ``[hedge_threshold_soft, qualified_band_high)``, prepend
      ``preferred_qualifier`` instead of leaving the surface bare.
    * ``"affirmative"`` — never qualify in the marginal band; let the
      assertion stand.
    """
    hedge_threshold_strong: float = 0.40
    hedge_threshold_soft: float = 0.50
    preferred_hedge_strong: str = "It seems that"
    preferred_hedge_soft: str = "Perhaps"
    claim_strength: str = "balanced"
    qualified_band_high: float = 0.75
    preferred_qualifier: str = "In some cases,"
    # ADR-0031 — per-axis hedge phrases keyed by axis_id.  When a
    # deviating axis matches an entry, the assembler uses that axis's
    # phrase instead of the generic ``preferred_hedge_*`` above.
    # Tuple of ``(axis_id, AxisHedge)`` pairs for hashability under
    # frozen dataclass semantics; pairs are kept in lex order on
    # ``axis_id`` so determinism is preserved across loads.
    axis_hedges: Tuple = ()  # Tuple[Tuple[str, AxisHedge], ...]


@dataclass(frozen=True)
class IdentityManifold:
    """Fixed geometric subspace encoding CORE's stable character."""
    value_axes: Tuple = ()  # Tuple[ValueAxis, ...]
    boundary_ids: FrozenSet[str] = frozenset()
    alignment_threshold: float = 0.45
    surface_preferences: SurfacePreferences = SurfacePreferences()


class IdentityCheck:
    """Checks a ReasoningTrajectory against an IdentityManifold.

    Canonical call style:
        IdentityCheck().check(trajectory, manifold)

    Deprecated compatibility style:
        IdentityCheck(manifold=manifold).check(trajectory)
    """

    def __init__(self, manifold: IdentityManifold | None = None) -> None:
        if manifold is not None:
            warnings.warn(
                "IdentityCheck(manifold=...) is deprecated; use "
                "IdentityCheck().check(trajectory, manifold).",
                DeprecationWarning,
                stacklevel=2,
            )
        self._manifold = manifold

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _mean_frame_coherence(trajectory) -> float:
        frames = getattr(trajectory, "frames", None)
        if not frames:
            return 0.0
        return sum(
            float(getattr(frame, "coherence_magnitude", 0.0)) for frame in frames
        ) / len(frames)

    @staticmethod
    def _axis_projection(axis, trajectory, scalar_score: float) -> float:
        """Deterministically project trajectory evidence onto one value axis."""
        direction = tuple(float(x) for x in getattr(axis, "direction", ()) or ())
        if not direction:
            return scalar_score
        full_l2 = math.sqrt(sum(x * x for x in direction)) or 1.0
        head_l2 = math.sqrt(sum(x * x for x in direction[:3]))
        directional_weight = head_l2 / full_l2
        frame_coherence = IdentityCheck._mean_frame_coherence(trajectory)
        coherence_term = IdentityCheck._clamp01(0.5 + (frame_coherence / 2.0))
        return IdentityCheck._clamp01(
            (0.75 * scalar_score) + (0.25 * directional_weight * coherence_term)
        )

    def check(self, trajectory, manifold: IdentityManifold | None = None) -> IdentityScore:
        resolved_manifold = manifold or self._manifold
        if resolved_manifold is None:
            raise TypeError("IdentityCheck.check() requires an IdentityManifold")
        trajectory_id = str(getattr(trajectory, "trajectory_id", "legacy_trajectory"))
        if not resolved_manifold.value_axes:
            return IdentityScore(
                score=1.0,
                flagged=False,
                deviation_axes=frozenset(),
                trajectory_id=trajectory_id,
            )
        confidence = float(getattr(trajectory, "total_coherence_delta", 0.0))
        confidence += self._mean_frame_coherence(trajectory)
        score = self._clamp01(0.5 + (confidence / 2.0))
        deviations = frozenset(
            str(getattr(axis, "axis_id", getattr(axis, "name", "axis")))
            for axis in resolved_manifold.value_axes
            if self._axis_projection(axis, trajectory, score) < resolved_manifold.alignment_threshold
        )
        return IdentityScore(
            score=score,
            flagged=bool(deviations),
            deviation_axes=deviations,
            trajectory_id=trajectory_id,
        )

    @staticmethod
    def would_violate(
        score: IdentityScore | None,
        manifold: IdentityManifold | None = None,
    ) -> bool:
        """Geometric identity-violation predicate (ADR-0010).

        Returns True when the trajectory's projection onto the IdentityManifold
        shows any value-axis falling below the manifold's alignment threshold,
        OR when the overall alignment scalar itself drops below threshold.

        This is the paraphrase-invariant defense: an identity-override attempt
        is recognised by the geometry of the field-state delta it induces, not
        by lexical surface.  Reviewers wire this in addition to (not instead
        of) any syntactic guard so the two layers remain independent.
        """
        if score is None:
            return False
        if score.flagged:
            return True
        if manifold is not None and score.score < manifold.alignment_threshold:
            return True
        return False


@dataclass(frozen=True)
class CharacterProfile:
    """Human-readable projection of the IdentityManifold."""
    traits: Dict[str, str]
    drive_summaries: Dict[str, float]
    fatigue_index: float
    boundary_commitments: Tuple[str, ...]
    theological_grounding: Dict[str, str]

    @classmethod
    def from_manifold(
        cls,
        manifold: IdentityManifold,
        drive_summaries: Optional[Dict[str, float]] = None,
        fatigue_index: float = 0.0,
    ) -> "CharacterProfile":
        traits: Dict[str, str] = {}
        theological_grounding: Dict[str, str] = {}
        for axis in manifold.value_axes:
            traits[axis.name] = (
                f"Fixed geometric direction {axis.direction} "
                f"in versor manifold — non-negotiable."
            )
            theological_note = getattr(axis, "theological_note", "")
            if theological_note:
                theological_grounding[axis.name] = theological_note

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
    """Append-only provenance record for one chat turn."""
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
    elaboration: Optional[str] = None
    # ADR-0035 — verdicts from SafetyCheck and EthicsCheck at end-of-turn.
    # Observational at v1: surfaced for audit; no behavioral effect.
    # Typed as ``object`` to avoid coupling identity.py to packs.*.
    safety_verdict: object = None
    ethics_verdict: object = None
    # ADR-0039 — unified verdict bundle (TurnVerdicts).  Typed as
    # ``object`` to avoid coupling identity.py to chat.verdicts.
    # Carries refusal_emitted / hedge_injected remediation flags
    # alongside the three verdict surfaces.
    verdicts: object = None
