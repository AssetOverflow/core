"""core.physics — Mind-physics layer for CORE cognitive architecture.

Three physics sublayers:
  allocation   — salience, attention, inhibition, coherence budget (ADR-0008)
  compositional — binding, digest, reasoning, articulation (ADR-0009)
  identity     — identity manifold, drives, exertion, character (ADR-0010)

All operators are stateless and frozen where possible.
State lives in the FieldState; operators are pure transformations.
"""

from core.physics.salience import SalienceOperator, SalienceMap, FieldRegion
from core.physics.attention import AttentionOperator, AttentionPlan, CoherenceBudget
from core.physics.inhibition import InhibitionOperator, InhibitionMask
from core.physics.binding import BindingFrame, BindingOperator
from core.physics.digest import DigestCycle, DigestOperator
from core.physics.reasoning import ReasoningTrajectory, TrajectoryOperator
from core.physics.articulation import ArticulationPlan, ArticulationPlanner, OutputModality
from core.physics.drive import DriveGradientMap, GradientField, ValueAxis
from core.physics.exertion import ExertionMeter, FatigueIndex, CycleCost
from core.physics.identity import IdentityManifold, IdentityCheck, IdentityScore, CharacterProfile

__all__ = [
    "SalienceOperator", "SalienceMap", "FieldRegion",
    "AttentionOperator", "AttentionPlan", "CoherenceBudget",
    "InhibitionOperator", "InhibitionMask",
    "BindingFrame", "BindingOperator",
    "DigestCycle", "DigestOperator",
    "ReasoningTrajectory", "TrajectoryOperator",
    "ArticulationPlan", "ArticulationPlanner", "OutputModality",
    "DriveGradientMap", "GradientField", "ValueAxis",
    "ExertionMeter", "FatigueIndex", "CycleCost",
    "IdentityManifold", "IdentityCheck", "IdentityScore", "CharacterProfile",
]
