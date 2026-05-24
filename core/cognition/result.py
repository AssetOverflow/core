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
from recognition.carrier import EpistemicGraph
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

    # --- inference operators (ADR-0018) ---
    # Deterministic serialisation of any typed operator invoked during the
    # turn (e.g. transitive_walk over the teaching-store typed-relation
    # graph).  Empty string when no operator ran.  Folded into trace_hash
    # so operator invocation is a load-bearing part of replay equality.
    operator_invocation: str = ""

    # --- forward semantic control evidence (ADR-0023) ---
    # ``admissibility_trace`` is the per-transition record produced by
    # ``generate()`` (empty tuple when no admissibility ran).
    # ``admissibility_trace_hash`` is its canonical SHA-256, folded
    # into ``trace_hash`` only when non-empty so pre-ADR-0023 turn
    # hashes are byte-preserved.
    # ``ratification_outcome`` is the enum value ("ratified" /
    # "demoted" / "passthrough") from the field ratifier; empty
    # string when no ratification ran.
    # ``region_was_unconstrained`` records whether forward semantic
    # control was active on this turn — observation only, no
    # production fail-closed yet (see ADR-0023 §Out of scope).
    admissibility_trace: tuple = ()
    admissibility_trace_hash: str = ""
    ratification_outcome: str = ""
    region_was_unconstrained: bool = True

    # --- inner-loop refusal evidence (ADR-0024 Phase 2) ---
    # ``refusal_reason`` is the stable string value of a
    # ``generate.exhaustion.RefusalReason`` when the walk refused this
    # turn, or the empty string otherwise.  Empty-string default is
    # the contract for "no refusal materialised"; folding into
    # trace_hash is gated on non-emptiness so non-refused turns keep
    # byte-identical hashes relative to pre-Phase-2 (CLAUDE.md
    # determinism invariant).  Phase 2 leaves the materialisation site
    # in chat/runtime.py untouched per the ADR-0024 Phase 2 scope
    # decision — this field exists so the trace contract is already
    # in place when a future ADR wires the materialisation path.
    refusal_reason: str = ""

    # --- recognition / epistemic carrier (ADR-0144) ---
    # None when no DerivedRecognizer is attached, when recognition refused,
    # or on the very first turn before any recognizer is configured.
    # Non-None only when recognition admitted (state == EVIDENCED).
    # NOT folded into trace_hash in Phase 1 (observability only).
    epistemic_graph: EpistemicGraph | None = None

    # --- compound intent observability (ADR-0089 Phase C1) ---
    # Finding 4 (audit 2026-05-20).  ``classify_compound_intent`` returns
    # multiple parts for inputs like "What is X and how does it relate
    # to Y?" but the pipeline still routes only the dominant clause
    # through the existing single-intent path.  Pre-fix the secondary
    # clauses were silently dropped — no observability, no telemetry,
    # no trace evidence.
    #
    # Phase C1 surfaces the dropped clauses here so operators can see
    # the lost signal without changing any current behaviour.  Phase
    # C2 (opt-in, flag-gated) will route the secondary clauses through
    # a multi-node graph; that wiring is deliberately scoped to a
    # separate PR per ADR-0089 because it widens
    # ``compute_trace_hash`` and the surface resolver contract.
    #
    # Empty tuple == this turn was single-clause OR the compound
    # classifier was not consulted; ``len > 0`` == this turn dropped
    # secondary clauses that were classified but not routed.
    dropped_compound_clauses: tuple[DialogueIntent, ...] = ()

    # --- invariant bookkeeping ---
    versor_condition: float = 0.0   # must be < 1e-6
    trace_hash: str = ""            # SHA-256 over deterministic key fields
