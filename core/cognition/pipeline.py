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


class CognitiveTurnPipeline:
    """Thin pipeline wrapper over ChatRuntime.

    Phase 1 goal: extract the observability path so downstream modules have
    a place to plug in.  No new intelligence is added here.
    """

    def __init__(self, runtime) -> None:  # runtime: ChatRuntime (no import cycle)
        self.runtime = runtime

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, text: str, max_tokens: int | None = None) -> CognitiveTurnResult:
        """Execute one full cognitive turn and return a complete result record."""

        # 1. LISTEN — capture pre-turn field state
        field_state_before: FieldState | None = self._capture_field_state()

        # 2–7. INGEST / UNDERSTAND / RECALL / THINK / ARTICULATE / LEARN
        #       Delegated to ChatRuntime.chat() in Phase 1.
        #       ChatResponse is the stable contract surface.
        response = self.runtime.chat(text, max_tokens=max_tokens)

        # 8. CAPTURE post-turn field state
        field_state_after: FieldState = self.runtime.session.state

        # 9. Reconstruct input-layer tokens from the turn log
        #    (turn_log is appended inside chat(); last entry matches this turn)
        last_turn = self.runtime.turn_log[-1]
        input_tokens = last_turn.input_tokens          # already filtered
        filtered_tokens = last_turn.input_tokens       # same at Phase 1

        # Raw tokenization is identical to filtered for Phase 1 — the
        # runtime's _tokenize() runs before _apply_oov_policy().  We
        # expose input_tokens separately so Phase 2 can diverge them.
        raw_tokens = tuple(self.runtime.tokenize(text))

        # 10. TRACE — deterministic hash
        trace_hash = compute_trace_hash(
            input_text=text,
            filtered_tokens=filtered_tokens,
            surface=response.surface,
            walk_surface=response.walk_surface,
            articulation_surface=response.articulation_surface,
            dialogue_role=str(response.dialogue_role),
            versor_condition=response.versor_condition,
            vault_hits=response.vault_hits,
        )

        return CognitiveTurnResult(
            input_text=text,
            input_tokens=raw_tokens,
            filtered_tokens=filtered_tokens,
            field_state_before=field_state_before,
            field_state_after=field_state_after,
            proposition=response.proposition,
            articulation=response.articulation,
            surface=response.surface,
            walk_surface=response.walk_surface,
            articulation_surface=response.articulation_surface,
            dialogue_role=response.dialogue_role,
            identity_score=response.identity_score,
            vault_hits=response.vault_hits,
            versor_condition=response.versor_condition,
            trace_hash=trace_hash,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _capture_field_state(self) -> FieldState | None:
        """Return current session field state, or None if not yet initialised."""
        try:
            state = self.runtime.session.state
            # SessionContext.state may be None before the first ingest
            return state if state is not None else None
        except AttributeError:
            return None
