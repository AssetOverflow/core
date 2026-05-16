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
from generate.intent import IntentTag
from generate.operators import WalkResult, transitive_walk
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

        # 7b. INFER — invoke typed deterministic operators (ADR-0018) when the
        # intent is a transitive-query or definition shape and the teaching
        # store carries a chain rooted at the subject.  The operator's result
        # is folded into the surface so chain endpoints become visible.
        walk_result: WalkResult | None = self._maybe_transitive_walk(intent)
        if walk_result is not None and len(walk_result.path) > 1:
            surface, articulation_surface = self._fold_walk_into_surface(
                walk_result, surface, articulation_surface,
            )

        # Track last node id for correction-intent chaining
        if graph.nodes:
            self._last_node_id = graph.nodes[-1].node_id

        # 8. CAPTURE post-turn field state
        field_state_after: FieldState = self.runtime.session.state

        # 9. Reconstruct input-layer tokens from the turn log
        #    (turn_log is appended inside chat(); last entry matches this turn)
        #    When the unknown-domain gate fires, chat() returns a stub without
        #    appending to turn_log — fall back to the tokenizer.
        raw_tokens = tuple(self.runtime.tokenize(text))
        if self.runtime.turn_log:
            last_turn = self.runtime.turn_log[-1]
            filtered_tokens = last_turn.input_tokens
        else:
            filtered_tokens = raw_tokens

        # 10. TEACHING — correction capture, review, and store
        teaching_candidate, reviewed_example, proposal = self._run_teaching(
            text, intent, self._turn_number,
            identity_score=response.identity_score,
        )

        # Advance turn counter and remember surface for next correction binding
        self._turn_number += 1
        self._prior_surface = surface

        # 11. TRACE — deterministic hash (includes teaching IDs and any
        # typed-operator invocation per ADR-0018).
        review_hash = reviewed_example.review_hash if reviewed_example is not None else ""
        proposal_id = proposal.proposal_id if proposal is not None else ""
        operator_invocation = self._serialize_walk(walk_result)
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
            operator_invocation=operator_invocation,
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
            operator_invocation=operator_invocation,
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
        *,
        identity_score: object = None,
    ) -> tuple[
        CorrectionCandidate | None,
        ReviewedTeachingExample | None,
        PackMutationProposal | None,
    ]:
        """Run correction capture → review → store if this turn is a CORRECTION.

        ``identity_score`` is the trajectory's projection onto the runtime
        IdentityManifold (already computed by ChatRuntime for this turn); the
        review gate uses it as a geometric (paraphrase-invariant) defense
        layer alongside the syntactic check.
        """
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

        manifold = getattr(self.runtime, "identity_manifold", None)
        reviewed = review_correction(
            candidate,
            identity_score=identity_score,  # type: ignore[arg-type]
            identity_manifold=manifold,
        )
        proposal = self.teaching_store.add(reviewed)
        return candidate, reviewed, proposal

    def _maybe_transitive_walk(self, intent) -> WalkResult | None:
        """Invoke ``transitive_walk`` when the intent shape calls for it.

        Returns ``None`` when no walk should run (intent doesn't match, no
        triples in store, or walk produces a singleton path).  Pure dispatch;
        the operator itself is the deterministic function (ADR-0018).
        """
        triples = self.teaching_store.triples()
        if not triples:
            return None
        if intent.tag is IntentTag.TRANSITIVE_QUERY and intent.relation:
            return transitive_walk(triples, intent.subject, intent.relation)
        if intent.tag is IntentTag.DEFINITION:
            # "What is X?" → walk the "is" relation if any chain exists.
            result = transitive_walk(triples, intent.subject, "is")
            if len(result.path) > 1:
                return result
        return None

    @staticmethod
    def _serialize_walk(walk: WalkResult | None) -> str:
        """Deterministic operator-invocation serialisation for trace_hash."""
        if walk is None:
            return ""
        import json
        return json.dumps(walk.as_dict(), sort_keys=True, ensure_ascii=False)

    @staticmethod
    def _fold_walk_into_surface(
        walk: WalkResult,
        surface: str,
        articulation_surface: str,
    ) -> tuple[str, str]:
        """Compose a chain-aware surface from a non-trivial walk result.

        Deterministic.  Replay-safe: identical (walk, prior surfaces) produce
        identical output.  The chain endpoint is the load-bearing token for
        the inference-closure / multi-step-reasoning eval lanes.
        """
        chain = " ".join(walk.path)
        endpoint = walk.path[-1]
        chain_surface = (
            f"{walk.head} {walk.relation.replace('_', ' ')} {endpoint} "
            f"(via {chain})"
        )
        # Preserve the prior surface as a prefix for context, when it exists
        # and is non-empty; otherwise the chain surface stands alone.
        if surface:
            new_surface = f"{surface} — {chain_surface}"
        else:
            new_surface = chain_surface
        if articulation_surface:
            new_articulation = f"{articulation_surface} — {chain_surface}"
        else:
            new_articulation = chain_surface
        return new_surface, new_articulation

    def _capture_field_state(self) -> FieldState | None:
        """Return current session field state, or None if not yet initialised."""
        try:
            state = self.runtime.session.state
            # SessionContext.state may be None before the first ingest
            return state if state is not None else None
        except AttributeError:
            return None
