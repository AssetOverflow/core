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

import json
from collections import OrderedDict

from field.state import FieldState
from core.cognition.result import CognitiveTurnResult
from core.cognition.surface_resolution import resolve_surface
from core.cognition.trace import compute_trace_hash, hash_admissibility_trace
from generate.intent import classify_compound_intent
from generate.intent_bridge import _is_useful_surface
from generate.intent_ratifier import (
    RatificationOutcome,
    RatifiedIntent,
    ratify_intent,
)
from generate.graph_planner import graph_from_intent, ground_graph, plan_articulation
from generate.realizer import realize_semantic
from generate.intent import IntentTag
from generate.operators import (
    FrameComposeResult,
    WalkResult,
    compose_relations,
    multi_relation_walk,
    transitive_walk,
)
from teaching.correction import CorrectionCandidate, extract_correction
from teaching.epistemic import EpistemicStatus
from teaching.review import ReviewedTeachingExample, review_correction
from teaching.store import PackMutationProposal, TeachingStore


# ADR-0021 §Articulation: surfaces backed by SPECULATIVE teaching material
# carry an explicit status marker.  Wording must match SPECULATIVE_MARKERS in
# evals/articulation_of_status/runner.py: "speculative" and "not yet reviewed"
# are both checked.
_SPECULATIVE_SURFACE_MARKER = "(speculative, not yet reviewed) "

# Reflexive query shapes that almost always refer back to the immediately
# prior speculative teaching even when the subject token is not repeated:
# "Has this been reviewed?", "Is your answer about X confirmed?".  Used to
# extend the marker beyond exact subject-token matches.
_REFLEXIVE_PROBE_MARKERS: tuple[str, ...] = (
    "your answer",
    "this answer",
    "has this",
    "is that",
    "confirmed",
    "reviewed",
    "verified",
)

# Splitter for extracting individual subject tokens from a parsed-triple
# subject like "correction: wisdom" → ("correction", "wisdom") — so probes
# about "wisdom" still match a SPECULATIVE proposal whose triple parser
# included a clarifying prefix.
import re as _re
_SUBJECT_SPLIT_RE = _re.compile(r"[^a-z0-9]+")
_SUBJECT_STOPWORDS: frozenset[str] = frozenset({
    "actually", "correction", "really", "indeed", "instead",
    "the", "this", "that", "these", "those",
    "is", "are", "was", "were", "been", "being",
    "of", "for", "with", "and", "but", "from",
    "your", "their", "answer",
})

# Finding 5 (audit 2026-05-20) — cap the speculative-subjects cache so a
# long teaching session cannot grow it without bound.  64 is large enough
# to cover every distinct teaching subject a single session realistically
# emits and small enough that the per-turn substring scan in
# ``_should_mark_speculative`` stays trivially cheap.  LRU eviction: a
# subject re-encountered as SPECULATIVE refreshes its position; coherent
# promotion removes it explicitly.
_MAX_SPECULATIVE_SUBJECTS = 64


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
        # ADR-0021 §Articulation: subjects of prior SPECULATIVE teaching
        # proposals.  When a later turn's input references one of these
        # (by subject substring or reflexive query shape), the surface
        # is prefixed with _SPECULATIVE_SURFACE_MARKER so the user can
        # tell ratified knowledge from unreviewed teaching material.
        #
        # Finding 5 (audit 2026-05-20) — backed by an OrderedDict so the
        # cache is bounded (LRU, cap ``_MAX_SPECULATIVE_SUBJECTS``) and
        # supports explicit eviction when a proposal is promoted to
        # COHERENT.  Pre-fix this was a bare ``set`` that only grew,
        # which both leaked speculative markers onto reviewed subjects
        # forever and widened the per-turn substring scan unboundedly.
        # Iteration order matches insertion / refresh order; lookups
        # remain O(1).
        self._speculative_subjects: OrderedDict[str, None] = OrderedDict()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, text: str, max_tokens: int | None = None) -> CognitiveTurnResult:
        """Execute one full cognitive turn and return a complete result record."""

        # 1. LISTEN — capture pre-turn field state
        field_state_before: FieldState | None = self._capture_field_state()

        # 1b. CLASSIFY — intent and proposition graph (deterministic, pre-chat)
        # ADR-0089 Phase C1 (Finding 4, audit 2026-05-20) — run the
        # compound classifier first and take its dominant clause as
        # the seeded intent.  ``classify_compound_intent`` already
        # invokes ``classify_intent`` on the dominant fragment, so
        # this is one regex cascade per turn instead of two (comb
        # pass 2026-05-21).  Secondary clauses surface on
        # ``CognitiveTurnResult.dropped_compound_clauses`` as
        # observability telemetry; the dominant clause continues to
        # route through the existing single-intent path.
        compound = classify_compound_intent(text)
        seeded_intent = compound.primary
        dropped_compound_clauses: tuple = (
            tuple(compound.parts[1:]) if compound.is_compound() else ()
        )
        # 1b.i FIELD-RATIFY the seeded intent (ADR-0022 §TBD-1).
        #      The regex classifier is the *seed*; the field is the
        #      gate.  A demoted intent routes the rest of the turn
        #      through the existing UNKNOWN-domain surface so the
        #      pipeline never silently relaxes a constraint to produce
        #      a fluent-but-ungrounded surface (§2 honest refusal).
        ratified = self._ratify_intent(seeded_intent, field_state_before)
        intent = ratified.intent
        prior_node_id = self._last_node_id
        graph = graph_from_intent(intent, prior_node_id=prior_node_id)
        target = plan_articulation(graph)

        # 1c. REALIZE — semantic realization from graph + intent.
        # Pre-fix (and default today) the realizer fires on the
        # ungrounded graph and emits ``<pending>`` / ``...`` surfaces
        # that ``_is_useful_surface`` rejects.  ADR-0088 Phase B opts
        # operators into grounding the graph BEFORE the realizer so
        # the realizer can compete as a real surface authority.
        realized_plan = realize_semantic(target, graph)

        # 2–7. INGEST / UNDERSTAND / RECALL / THINK / ARTICULATE / LEARN
        #       Delegated to ChatRuntime.chat().
        #       ChatResponse is the stable contract surface.
        response = self.runtime.chat(text, max_tokens=max_tokens)

        # ADR-0088 Phase B (audit Finding 2, 2026-05-20) — opt-in
        # grounded realizer.  When the runtime opts in, fill the
        # graph's <pending> obj slots from the recall step's walk
        # tokens (already alphabetic-filtered by ChatRuntime) and
        # re-invoke ``realize_semantic`` on the grounded graph.  The
        # surface resolver (PR #76) then picks the realizer's
        # grounded output when it clears ``_is_useful_surface`` and
        # the unknown-domain gate did not fire.  Default-off
        # preserves byte-identity for every existing surface and
        # trace_hash — the realizer continues to emit unusable
        # placeholders and lose the resolver to the runtime path.
        # Comb pass 2026-05-21 — direct attribute access; these fields
        # all live on ChatResponse with documented defaults (PR #88 for
        # ``realizer_grounded_authority`` + ``recalled_words``, ADR-0048
        # for ``grounding_source``, ADR-0077 for
        # ``register_canonical_surface``, ADR-0071 for
        # ``pre_decoration_surface``).  The historical ``getattr`` calls
        # were ADR-introduction defensiveness now safe to drop.
        if self.runtime.config.realizer_grounded_authority:
            recalled_words = response.recalled_words
            if recalled_words:
                grounded_graph = ground_graph(graph, recalled_words)
                realized_plan = realize_semantic(target, grounded_graph)

        gate_fired = (
            response.vault_hits == 0
            and response.grounding_source != "vault"
        )
        canonical = response.register_canonical_surface
        pre_decoration = response.pre_decoration_surface

        # Comb pass 2026-05-21 — materialize teaching-store triples once
        # per turn.  Pre-fix both ``_maybe_transitive_walk`` and
        # ``_maybe_compose_relations`` called ``self.teaching_store.triples()``
        # independently, doubling the per-turn O(N) filter+tuple-build
        # cost as the corpus grows.
        triples = self.teaching_store.triples()

        walk_result: WalkResult | None = self._maybe_transitive_walk(intent, triples)
        walk_surface = ""
        if walk_result is not None and len(walk_result.path) > 1:
            walk_surface = CognitiveTurnPipeline._render_walk_surface(walk_result)

        compose_result: FrameComposeResult | None = self._maybe_compose_relations(intent, triples)
        compose_surface = ""
        if compose_result is not None and (
            compose_result.subject_tail is not None
            or compose_result.frame_tail is not None
        ):
            compose_surface = CognitiveTurnPipeline._render_compose_surface(compose_result)

        resolved = resolve_surface(
            canonical_surface=canonical,
            pre_decoration_surface=pre_decoration,
            response_surface=response.surface,
            response_articulation_surface=response.articulation_surface,
            realized_surface=realized_plan.surface,
            realizer_useful=_is_useful_surface(realized_plan.surface),
            gate_fired=gate_fired,
            walk_surface=walk_surface,
            compose_surface=compose_surface,
        )
        surface = resolved.surface
        articulation_surface = resolved.articulation_surface

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

        # 9b. ARTICULATE STATUS — if any prior turn produced a SPECULATIVE
        # teaching proposal whose subject is referenced by the current
        # input (subject substring or reflexive query shape), prepend a
        # status marker so the user can distinguish reviewed knowledge
        # from unreviewed teaching material.  ADR-0021 §Articulation.
        # Decision uses subjects seeded by prior turns; this turn's own
        # proposal (if any) is added below for FUTURE turns to see.
        if self._speculative_subjects and surface and self._should_mark_speculative(text, surface):
            surface = _SPECULATIVE_SURFACE_MARKER + surface
            articulation_surface = _SPECULATIVE_SURFACE_MARKER + articulation_surface

        # 10. TEACHING — correction capture, review, and store
        teaching_candidate, reviewed_example, proposal = self._run_teaching(
            text, intent, self._turn_number,
            identity_score=response.identity_score,
        )

        # 10b. TRACK SPECULATIVE SUBJECTS — seed the marker decision for
        # future turns.  Done AFTER the marker check above so the teach
        # turn itself does not self-mark; only subsequent probes do.
        # Prefer the parsed-triple subject (clean: "truth") over the raw
        # proposal.subject (often a fragment of the correction text);
        # also split-and-add each ≥4-char token so prefixed parses like
        # "correction: wisdom" still match a probe about "wisdom".
        if proposal is not None:
            sources: list[str] = []
            if proposal.triple is not None and proposal.triple[0]:
                sources.append(proposal.triple[0])
            if proposal.subject:
                sources.append(proposal.subject)
            if proposal.epistemic_status is EpistemicStatus.SPECULATIVE:
                for src in sources:
                    self._remember_speculative_subject(src)
                    for tok in _SUBJECT_SPLIT_RE.split(src.lower()):
                        if len(tok) >= 4 and tok not in _SUBJECT_STOPWORDS:
                            self._remember_speculative_subject(tok)
            elif proposal.epistemic_status is EpistemicStatus.COHERENT:
                # Finding 5 (audit 2026-05-20) — once teaching review
                # promotes a proposal to COHERENT, the subject is no
                # longer speculative; evict its tokens so the marker
                # stops appearing on subsequent probes about it.
                for src in sources:
                    self._forget_speculative_subject(src)
                    for tok in _SUBJECT_SPLIT_RE.split(src.lower()):
                        if len(tok) >= 4 and tok not in _SUBJECT_STOPWORDS:
                            self._forget_speculative_subject(tok)

        # Advance turn counter and remember surface for next correction binding
        self._turn_number += 1
        self._prior_surface = surface

        # 11. TRACE — deterministic hash (includes teaching IDs and any
        # typed-operator invocation per ADR-0018).
        review_hash = reviewed_example.review_hash if reviewed_example is not None else ""
        proposal_id = proposal.proposal_id if proposal is not None else ""
        epistemic_status = proposal.epistemic_status.value if proposal is not None else ""
        walk_serialised = CognitiveTurnPipeline._serialize_operator(walk_result)
        compose_serialised = CognitiveTurnPipeline._serialize_operator(compose_result)
        # Deterministic concatenation: walk record, then compose record.
        # Empty strings are dropped so single-operator turns keep their
        # existing trace_hash byte-for-byte.
        operator_invocation = (
            f"{walk_serialised}|{compose_serialised}"
            if compose_serialised
            else walk_serialised
        )
        # ADR-0023 — admissibility trace + ratification provenance.
        # Comb pass 2026-05-21 — direct attribute access; the fields
        # are dataclass-defaulted on ChatResponse, so the prior
        # ``getattr`` guard was dead defensiveness from the ADR
        # introduction window.
        admissibility_trace = response.admissibility_trace
        region_was_unconstrained = response.region_was_unconstrained
        admissibility_trace_hash = hash_admissibility_trace(admissibility_trace)
        ratification_outcome = ratified.outcome.value
        # ADR-0024 Phase 2 — refusal_reason flows from a future
        # materialisation site on ChatResponse.  Empty string on every
        # non-refused turn; folding into trace_hash is gated on
        # non-emptiness so non-refused turns keep byte-identical hashes
        # relative to pre-Phase-2 (CLAUDE.md determinism invariant).
        refusal_reason = getattr(response, "refusal_reason", "") or ""
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
            teaching_epistemic_status=epistemic_status,
            operator_invocation=operator_invocation,
            admissibility_trace_hash=admissibility_trace_hash,
            ratification_outcome=ratification_outcome,
            region_was_unconstrained=region_was_unconstrained,
            refusal_reason=refusal_reason,
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
            admissibility_trace=admissibility_trace,
            admissibility_trace_hash=admissibility_trace_hash,
            ratification_outcome=ratification_outcome,
            region_was_unconstrained=region_was_unconstrained,
            refusal_reason=refusal_reason,
            dropped_compound_clauses=dropped_compound_clauses,
            versor_condition=response.versor_condition,
            trace_hash=trace_hash,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ratify_intent(self, intent, field_state):
        """Field-ratify a seeded intent (ADR-0022 §TBD-1).

        When no field state or no vocab is available (cold start),
        ratification short-circuits to PASSTHROUGH and the seed
        survives — the existing cold-start behavior is preserved.
        """
        if field_state is None:
            return RatifiedIntent(
                intent=intent,
                outcome=RatificationOutcome.PASSTHROUGH,
                score=0.0,
                threshold=0.0,
                seed_tag=intent.tag,
            )
        # ChatRuntime exposes vocab via session, not directly.  The
        # original ADR-0022 wiring used ``getattr(self.runtime, "vocab",
        # None)`` which always returned None — silently routing every
        # turn through PASSTHROUGH.  ADR-0023 §3 surfaced this via the
        # ``passthrough_on_scored`` lane metric; the fix here is to
        # resolve vocab through the session contract.
        session = getattr(self.runtime, "session", None)
        vocab = getattr(session, "vocab", None) if session is not None else None
        if vocab is None:
            return RatifiedIntent(
                intent=intent,
                outcome=RatificationOutcome.PASSTHROUGH,
                score=0.0,
                threshold=0.0,
                seed_tag=intent.tag,
            )
        prompt_versor = getattr(field_state, "F", None)
        if prompt_versor is None:
            return RatifiedIntent(
                intent=intent,
                outcome=RatificationOutcome.PASSTHROUGH,
                score=0.0,
                threshold=0.0,
                seed_tag=intent.tag,
            )
        return ratify_intent(intent, prompt_versor, vocab=vocab)

    def _remember_speculative_subject(self, subject: str) -> None:
        """Add (or refresh LRU position of) a speculative subject token.

        Finding 5 (audit 2026-05-20).  Caps the cache at
        ``_MAX_SPECULATIVE_SUBJECTS`` via insertion-order eviction.
        Empty / whitespace-only inputs are dropped silently so callers
        can pass raw fragments without guarding.
        """
        subject = subject.lower().strip()
        if not subject:
            return
        self._speculative_subjects.pop(subject, None)
        self._speculative_subjects[subject] = None
        while len(self._speculative_subjects) > _MAX_SPECULATIVE_SUBJECTS:
            self._speculative_subjects.popitem(last=False)

    def _forget_speculative_subject(self, subject: str) -> None:
        """Evict a subject from the speculative-marker cache.

        Called when a SPECULATIVE proposal is promoted to COHERENT via
        the teaching review loop, so reviewed material stops being
        marked speculative on later probes.  No-op if the subject is
        not present.
        """
        subject = subject.lower().strip()
        if subject:
            self._speculative_subjects.pop(subject, None)

    def _should_mark_speculative(self, text: str, surface: str) -> bool:
        """Decide whether ``surface`` should carry the SPECULATIVE marker.

        Triggers when the input references a subject of a prior SPECULATIVE
        teaching proposal (by substring match) or carries a reflexive query
        shape (e.g. "is your answer about X confirmed?").  Already-marked
        surfaces are not double-marked.
        """
        surface_lower = surface.lower()
        if "speculative" in surface_lower or "not yet reviewed" in surface_lower:
            return False
        text_lower = text.lower()
        for subj in self._speculative_subjects:
            if subj and subj in text_lower:
                return True
        for marker in _REFLEXIVE_PROBE_MARKERS:
            if marker in text_lower:
                return True
        return False

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

    def _maybe_transitive_walk(
        self,
        intent,
        triples: tuple[tuple[str, str, str], ...] | None = None,
    ) -> WalkResult | None:
        """Invoke a typed deterministic walk operator when the intent shape
        calls for it (ADR-0018).

        Dispatch order, by precision:
          1. Relation-typed `transitive_walk` if the intent carries a
             relation and a same-relation chain exists from the head.
          2. Cross-relation `multi_relation_walk` fallback when (1)
             returns a singleton — this is what closes the
             mixed_relation / composed_predicate residuals.

        DEFINITION intents only attempt step 1 with the implicit "is"
        relation; they do not fall back to a multi-relation walk
        (which would be too permissive for plain "What is X?").

        ``triples`` may be passed in to avoid a second
        ``teaching_store.triples()`` materialization per turn (comb
        pass 2026-05-21); when omitted, falls back to the live store.
        """
        if triples is None:
            triples = self.teaching_store.triples()
        if not triples:
            return None
        if intent.tag is IntentTag.TRANSITIVE_QUERY and intent.relation:
            result = transitive_walk(triples, intent.subject, intent.relation)
            if len(result.path) > 1:
                return result
            multi = multi_relation_walk(triples, intent.subject)
            if len(multi.path) > 1:
                return multi
            return None
        if intent.tag is IntentTag.DEFINITION:
            result = transitive_walk(triples, intent.subject, "is")
            if len(result.path) > 1:
                return result
        return None

    def _maybe_compose_relations(
        self,
        intent,
        triples: tuple[tuple[str, str, str], ...] | None = None,
    ) -> FrameComposeResult | None:
        """Invoke ``compose_relations`` when the intent is a frame-transfer
        probe ("What does X R in Y?") and the teaching store carries at
        least one R-edge.  Returns the typed result; the caller folds
        non-None tails into the surface.

        ``triples`` may be passed in to avoid a second
        ``teaching_store.triples()`` materialization per turn (comb
        pass 2026-05-21).
        """
        if intent.tag is not IntentTag.FRAME_TRANSFER:
            return None
        if not intent.relation or not intent.frame:
            return None
        if triples is None:
            triples = self.teaching_store.triples()
        if not triples:
            return None
        return compose_relations(
            triples,
            head=intent.subject,
            frame=intent.frame,
            relation=intent.relation,
        )

    @staticmethod
    def _render_compose_surface(compose: FrameComposeResult) -> str:
        """Render a frame-transfer composition suffix without selecting authority."""
        parts: list[str] = []
        if compose.subject_tail is not None:
            parts.append(
                f"{compose.head} {compose.relation.replace('_', ' ')} {compose.subject_tail}"
            )
        if compose.frame_tail is not None:
            parts.append(
                f"in {compose.frame} {compose.relation.replace('_', ' ')} {compose.frame_tail}"
            )
        return "; ".join(parts)

    # Comb pass 2026-05-21 — removed dead ``_fold_compose_into_surface``
    # (no live callers since PR #76 routed all surface composition
    # through the explicit ``resolve_surface`` policy).  The render
    # helper above is still consumed by the resolver path.

    @staticmethod
    def _serialize_operator(op: WalkResult | FrameComposeResult | None) -> str:
        """Deterministic operator-invocation serialisation for trace_hash.

        Comb pass 2026-05-21 — collapsed the parallel ``_serialize_walk`` /
        ``_serialize_compose`` helpers into one.  Both operators expose
        ``as_dict()`` and serialise identically.
        """
        if op is None:
            return ""
        return json.dumps(op.as_dict(), sort_keys=True, ensure_ascii=False)

    @staticmethod
    def _render_walk_surface(walk: WalkResult) -> str:
        """Render a chain-aware walk suffix without selecting authority."""
        chain = " ".join(walk.path)
        endpoint = walk.path[-1]
        return (
            f"{walk.head} {walk.relation.replace('_', ' ')} {endpoint} "
            f"(via {chain})"
        )

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
        chain_surface = CognitiveTurnPipeline._render_walk_surface(walk)
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
