"""
CognitiveTurnPipeline — the cognitive spine.

Architecture:
    listen -> ingest -> understand -> recall -> think -> articulate
           -> learn_proposal -> trace

This first-pass implementation delegates to ChatRuntime internals so
future intelligence modules (IntentPropositionGraph, ArticulationRealizerV2,
ReviewedTeachingLoop, CognitiveEvalHarness) have a clean plug-in surface
without requiring a full ChatRuntime rewrite.

Constraint: ChatRuntime.chat() and ChatResponse contract are unchanged.
"""

from __future__ import annotations

from field.state import FieldState
from core.cognition.result import CognitiveTurnResult
from core.cognition.trace import compute_trace_hash
from generate.intent import classify_intent
from generate.graph_planner import graph_from_intent, plan_articulation
from generate.realizer import realize_semantic
from teaching.correction import CorrectionCandidate, extract_correction
from teaching.review import ReviewedTeachingExample, review_correction
from teaching.store import PackMutationProposal, TeachingStore


class CognitiveTurnPipeline:
    """Thin pipeline wrapper over ChatRuntime.

    Phase 1 goal: extract the observability path so downstream modules have
    a place to plug in.  No new intelligence is added here.
    """

    def __init__(self, runtime, teaching_store: TeachingStore | None = None) -> None:  # runtime: ChatRuntime (no import cycle)
        self.runtime = runtime
        self._last_node_id: str | None = None
        self.teaching_store = teaching_store or TeachingStore()
        self._prior_surface: str | None = None
        self._turn_number: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, text: str, max_tokens: int | None = None) -> CognitiveTurnResult:
        """Execute one full cognitive turn and return a complete result record."""

        # 1. LISTEN — capture pre-turn field state
        field_state_before: FieldState | None = self._capture_field_state()

        # 1b. CLASSIFY — intent and proposition graph (deterministic, pre-chat)
        intent = classify_intent(text)
        prior_node_id = self._last_node_id
        graph = graph_from_intent(intent, prior_node_id=prior_node_id)
        target = plan_articulation(graph)

        # 1c. REALIZE — semantic realization from graph + intent
        realized_plan = realize_semantic(target, graph)

        # 2–7. INGEST / UNDERSTAND / RECALL / THINK / ARTICULATE / LEARN
        #       Delegated to ChatRuntime.chat().
        #       ChatResponse is the stable contract surface.
        response = self.runtime.chat(text, max_tokens=max_tokens)

        # Override surfaces when semantic realizer produced a result.
        # The ChatResponse contract fields are preserved; we select
        # the better articulation surface from the semantic path.
        surface = response.surface
        articulation_surface = response.articulation_surface
        if realized_plan.surface:
            surface = realized_plan.surface
            articulation_surface = realized_plan.surface

        # Track last node id for correction-intent chaining
        if graph.nodes:
            self._last_node_id = graph.nodes[-1].node_id

        # 8. CAPTURE post-turn field state
        field_state_after: FieldState = self.runtime.session.state

        # 9. Reconstruct input-layer tokens from the turn log
        #    (turn_log is appended inside chat(); last entry matches this turn)
        last_turn = self.runtime.turn_log[-1]
        filtered_tokens = last_turn.input_tokens

        # Raw tokenization is identical to filtered for Phase 1 — the
        # runtime's _tokenize() runs before _apply_oov_policy().  We
        # expose input_tokens separately so Phase 2 can diverge them.
        raw_tokens = tuple(self.runtime.tokenize(text))

        # 10. TEACHING — correction capture, review, and store
        teaching_candidate, reviewed_example, proposal = self._run_teaching(
            text, intent, self._turn_number,
        )

        # Advance turn counter and remember surface for next correction binding
        self._turn_number += 1
        self._prior_surface = surface

        # 11. TRACE — deterministic hash (includes teaching IDs when present)
        review_hash = reviewed_example.review_hash if reviewed_example is not None else ""
        proposal_id = proposal.proposal_id if proposal is not None else ""
        trace_hash = compute_trace_hash(
            input_text=text,
            filtered_tokens=filtered_tokens,
            surface=surface,
            walk_surface=response.walk_surface,
            articulation_surface=articulation_surface,
            dialogue_role=str(response.dialogue_role),
            versor_condition=response.versor_condition,
            vault_hits=response.vault_hits,
            intent_tag=intent.tag.value,
            teaching_review_hash=review_hash,
            teaching_proposal_id=proposal_id,
        )

        return CognitiveTurnResult(
            input_text=text,
            input_tokens=raw_tokens,
            filtered_tokens=filtered_tokens,
            field_state_before=field_state_before,
            field_state_after=field_state_after,
            proposition=response.proposition,
            articulation=response.articulation,
            surface=surface,
            walk_surface=response.walk_surface,
            articulation_surface=articulation_surface,
            dialogue_role=response.dialogue_role,
            identity_score=response.identity_score,
            vault_hits=response.vault_hits,
            intent=intent,
            proposition_graph=graph,
            articulation_target=target,
            teaching_candidate=teaching_candidate,
            reviewed_teaching_example=reviewed_example,
            pack_mutation_proposal=proposal,
            versor_condition=response.versor_condition,
            trace_hash=trace_hash,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_teaching(
        self,
        text: str,
        intent: object,
        turn_number: int,
    ) -> tuple[
        CorrectionCandidate | None,
        ReviewedTeachingExample | None,
        PackMutationProposal | None,
    ]:
        """Run correction capture → review → store if this turn is a CORRECTION."""
        if self._prior_surface is None:
            return None, None, None

        candidate = extract_correction(
            correction_text=text,
            intent=intent,  # type: ignore[arg-type]
            prior_surface=self._prior_surface,
            prior_turn=turn_number - 1,
        )
        if candidate is None:
            return None, None, None

        reviewed = review_correction(candidate)
        proposal = self.teaching_store.add(reviewed)
        return candidate, reviewed, proposal

    def _capture_field_state(self) -> FieldState | None:
        """Return current session field state, or None if not yet initialised."""
        try:
            state = self.runtime.session.state
            # SessionContext.state may be None before the first ingest
            return state if state is not None else None
        except AttributeError:
            return None
