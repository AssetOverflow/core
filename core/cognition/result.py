"""
CognitiveTurnResult — the complete record of one cognitive turn.

This is the canonical output of CognitiveTurnPipeline.run().  It is
frozen and slot-based so it can be passed safely across module boundaries
without mutation risk.
"""

from __future__ import annotations

from dataclasses import dataclass

from field.state import FieldState
from generate.articulation import ArticulationPlan
from generate.dialogue import DialogueRole
from generate.graph_planner import ArticulationTarget, PropositionGraph
from generate.intent import DialogueIntent
from generate.proposition import Proposition
from core.physics.identity import IdentityScore
from teaching.correction import CorrectionCandidate
from teaching.review import ReviewedTeachingExample
from teaching.store import PackMutationProposal


@dataclass(frozen=True, slots=True)
class CognitiveTurnResult:
    """Full observability record for a single pipeline turn."""

    # --- input layer ---
    input_text: str
    input_tokens: tuple[str, ...]
    filtered_tokens: tuple[str, ...]

    # --- field layer ---
    field_state_before: FieldState | None   # None on the very first turn
    field_state_after: FieldState

    # --- understanding / recall layer ---
    proposition: Proposition
    articulation: ArticulationPlan

    # --- output surfaces ---
    surface: str                # final voiced surface (what the user sees)
    walk_surface: str           # sentence-assembled walk surface
    articulation_surface: str   # bare articulation surface before assembly

    # --- dialogue ---
    dialogue_role: DialogueRole

    # --- identity telemetry ---
    identity_score: IdentityScore | None

    # --- vault / memory ---
    vault_hits: int

    # --- intent / graph telemetry ---
    intent: DialogueIntent | None = None
    proposition_graph: PropositionGraph | None = None
    articulation_target: ArticulationTarget | None = None

    # --- teaching loop ---
    teaching_candidate: CorrectionCandidate | None = None
    reviewed_teaching_example: ReviewedTeachingExample | None = None
    pack_mutation_proposal: PackMutationProposal | None = None

    # --- invariant bookkeeping ---
    versor_condition: float = 0.0   # must be < 1e-6
    trace_hash: str = ""            # SHA-256 over deterministic key fields
