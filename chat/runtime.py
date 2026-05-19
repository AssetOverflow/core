from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from collections.abc import Sequence
from typing import Any, List

import numpy as np

from algebra.versor import versor_condition
from chat.pack_grounding import (
    pack_grounded_surface,
    pack_grounded_comparison_surface,
    pack_grounded_correction_surface,
    pack_grounded_procedure_surface,
    PACK_ID as _COGNITION_PACK_ID,
)
from chat.teaching_grounding import (
    teaching_grounded_surface,
    teaching_grounded_surface_composed,
    TEACHING_CORPUS_ID as _TEACHING_CORPUS_ID,
)
from chat.refusal import (
    build_hedge_prefix,
    build_refusal_surface,
    inject_hedge,
    should_inject_hedge,
)
from chat.telemetry import (
    TurnEventSink,
    format_correction_event_jsonl,
    format_turn_event_jsonl,
)
from chat.verdicts import TurnVerdicts
from teaching.discovery import (
    extract_discovery_candidates,
    format_candidate_jsonl,
)
from teaching.discovery_sink import DiscoveryCandidateSink
from core.config import DEFAULT_CONFIG, DEFAULT_IDENTITY_PACK, RuntimeConfig
from core.physics.drive import DriveGradientMap, GradientField
from core.physics.energy import EnergyProfile
from core.physics.exertion import CycleCost, ExertionMeter
from core.physics.identity import (
    CharacterProfile,
    IdentityCheck,
    IdentityScore,
    TurnEvent,
)
from packs.ethics.check import EthicsCheck, EthicsContext
from packs.ethics.loader import (
    DEFAULT_ETHICS_PACK as _DEFAULT_ETHICS_PACK,
    EthicsPackError,
    load_ethics_pack,
)
from packs.identity.loader import load_identity_manifold
from packs.safety.check import SafetyCheck, SafetyContext
from packs.safety.loader import load_safety_pack
from field.state import FieldState
from generate.articulation import ArticulationPlan, realize
from generate.dialogue import DialogueRole, classify_dialogue_blade, propose_dialogue
from generate.graph_constraint import build_graph_constraint
from generate.intent_bridge import articulate_with_intent, build_graph_from_input
from generate.proposition import FrameRegistry, Proposition, propose
from generate.result import GenerationResult
from generate.stream import generate
from generate.surface import SentenceAssembler, SentencePlan, SurfaceContext
from ingest.gate import inject
from language_packs import OOVPolicy, load_mounted_packs, load_pack, load_pack_entries
from persona.motor import PersonaMotor
from session.context import SessionContext
from session.correction import CorrectionPass
from vault.decompose import default_decomposer, default_gate

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_SEED_ALIASES = {
    "logos": "\u03bb\u03cc\u03b3\u03bf\u03c2",
    "dabar": "\u05d3\u05d1\u05e8",
    "or": "\u05d0\u05d5\u05e8",
    "phos": "\u03c6\u03c9\u03c2",
    "zoe": "\u03b6\u03c9\u03ae",
    "arche": "\u1f00\u03c1\u03c7\u03ae",
    "aletheia": "\u1f00\u03bb\u03ae\u03b8\u03b5\u03b9\u03b1",
}
_QUESTION_WORDS = frozenset({"what", "who", "how", "why", "when", "where", "which"})
_TERMINALS = frozenset({".", "?", ";", "!"})
_UNKNOWN_DOMAIN_SURFACE = "I don't know — insufficient grounding for that yet."


def _energy_scalar(energy_obj) -> float:
    if energy_obj is None:
        return 1.0
    if isinstance(energy_obj, EnergyProfile):
        return float(energy_obj.raw)
    try:
        return float(energy_obj)
    except (TypeError, ValueError):
        return 1.0


def _is_question_input(raw_text: str, tokens: Sequence[str]) -> bool:
    if raw_text.strip().endswith("?"):
        return True
    return bool(tokens and tokens[0].casefold() in _QUESTION_WORDS)


def _stable_dialogue_role(role: DialogueRole, *, raw_text: str, tokens: Sequence[str]) -> DialogueRole:
    if role in {"question", "refute"} and not _is_question_input(raw_text, tokens):
        return "elaborate"
    return role


def _terminal_for_role(role: DialogueRole, output_language: str) -> str:
    if role == "question":
        return ";" if output_language == "grc" else "?"
    return "."


def _terminate_surface(surface: str, *, role: DialogueRole, output_language: str) -> str:
    stripped = surface.strip()
    if not stripped:
        return stripped
    if stripped[-1] in _TERMINALS:
        return stripped
    return f"{stripped}{_terminal_for_role(role, output_language)}"


def _prefer_prompt_anchor(
    articulation: ArticulationPlan,
    filtered_tokens: Sequence[str],
    *,
    output_language: str,
) -> ArticulationPlan:
    if output_language != "en" or len(filtered_tokens) < 2:
        return articulation
    content_tokens = [
        token
        for token in filtered_tokens
        if token.casefold() not in _QUESTION_WORDS and token.casefold() not in {"is", "are", "was", "were"}
    ]
    if not content_tokens:
        return articulation
    anchor = content_tokens[-1]
    if anchor == articulation.subject:
        return articulation
    return replace(
        articulation,
        subject=anchor,
        surface=" ".join(part for part in (anchor, articulation.predicate, articulation.object) if part),
    )


@dataclass
class _StubBindingFrame:
    frame_id: str
    coherence_magnitude: float
    region_ids: frozenset
    cycle_index: int


@dataclass(frozen=True, slots=True)
class _FieldStateWithVersor:
    """Adapter exposing ``versor_condition`` for SafetyContext.

    ``FieldState`` itself does not carry a precomputed
    ``versor_condition`` attribute; it is computed on demand from
    ``versor_condition(state.F)``.  The SafetyCheck predicate for
    ``preserve_versor_closure`` reads ``ctx.field_state.versor_condition``
    via ``getattr``.  This adapter exposes the precomputed value so the
    predicate is runtime-checkable each turn.
    """

    versor_condition: float


def _hash_identity_manifold(manifold) -> str:
    """Deterministic SHA-256 of the load-bearing identity-manifold fields.

    ADR-0035 — feeds the ``no_identity_override`` predicate in
    :class:`SafetyCheck`.  The runtime never mutates ``identity_manifold``
    after composition, so before- and after-turn hashes are equal by
    construction; an unequal hash would indicate the predicate's exact
    failure mode.
    """
    payload = {
        "value_axes": [
            {
                "axis_id": axis.axis_id,
                "name": axis.name,
                "direction": list(axis.direction),
                "weight": axis.weight,
            }
            for axis in manifold.value_axes
        ],
        "boundary_ids": sorted(manifold.boundary_ids),
        "alignment_threshold": manifold.alignment_threshold,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _surface_contains_hedge(surface: str, manifold) -> bool:
    """Detect whether the realized surface emitted a hedge phrase.

    Compares case-insensitively against the manifold's preferred hedge
    phrases (ADR-0028).  False when surface is empty.  Coarse but
    deterministic: the predicate downstream is observational, so
    occasional false negatives are surfaced as
    ``acknowledge_uncertainty`` violations in audit and corrected by
    refining hedge detection, not by silently passing.
    """
    if not surface:
        return False
    prefs = getattr(manifold, "surface_preferences", None)
    if prefs is None:
        return False
    candidates: list[str] = []
    for field_name in (
        "preferred_hedge_strong",
        "preferred_hedge_soft",
        "preferred_qualifier",
    ):
        value = getattr(prefs, field_name, "")
        if value:
            candidates.append(value)
    for _, hedge in getattr(prefs, "axis_hedges", ()) or ():
        for sub in ("strong", "soft", "qualifier"):
            value = getattr(hedge, sub, "")
            if value:
                candidates.append(value)
    surface_fold = surface.casefold()
    return any(c.casefold() in surface_fold for c in candidates if c)


def _make_trajectory_from_result(result, turn: int):
    from core.physics.reasoning import TrajectoryOperator

    operator = TrajectoryOperator()
    states = result.trajectory or (result.final_state,)
    frames = [
        _StubBindingFrame(
            frame_id=f"t{turn}_s{i}",
            coherence_magnitude=_energy_scalar(getattr(fs, "energy", None)),
            region_ids=frozenset({str(getattr(fs, "node", 0))}),
            cycle_index=turn,
        )
        for i, fs in enumerate(states)
    ]
    return operator.build(frames, trajectory_id=f"turn_{turn}")


@dataclass(frozen=True, slots=True)
class ChatResponse:
    surface: str
    proposition: Proposition
    articulation: ArticulationPlan
    articulation_surface: str
    dialogue_role: DialogueRole
    versor_condition: float
    output_language: str
    frame_pack: str
    walk_surface: str
    salience_top_k: int | None
    candidates_used: int | None
    vault_hits: int
    identity_score: IdentityScore | None
    character_profile: CharacterProfile
    flagged: bool
    # ADR-0023 §2 — per-transition admissibility evidence and region
    # provenance flag.  An empty tuple is the contract for "no
    # admissibility was checked this turn" (cold start, refusal, stub).
    admissibility_trace: tuple = ()
    region_was_unconstrained: bool = True
    # ADR-0035 — verdicts surfaced from SafetyCheck and EthicsCheck.
    # ``None`` only on stub/refusal paths that bypass the turn loop.
    safety_verdict: object = None
    ethics_verdict: object = None
    # ADR-0039 — unified TurnVerdicts bundle carrying identity / safety
    # / ethics verdicts and the two remediation flags
    # (refusal_emitted, hedge_injected).  Typed as ``object`` to avoid
    # coupling at module-resolution time; downcast at use site.
    verdicts: object = None
    # ADR-0048 / ADR-0050 / ADR-0052 — provenance tag for the surface's
    # grounding.  One of:
    #   "vault"    — answer drawn from session vault evidence (main path).
    #   "pack"     — answer drawn from the ratified language pack
    #                (cold-start DEFINITION/RECALL/COMPARISON on pack-known
    #                lemmas — ADR-0048 / ADR-0050).
    #   "teaching" — answer drawn from a reviewed teaching-chain corpus
    #                (cold-start CAUSE/VERIFICATION — ADR-0052).
    #   "none"     — universal "insufficient grounding" disclosure on stub.
    # The string is preserved verbatim in TurnEvent for downstream audit.
    grounding_source: str = "none"


class ChatRuntime:
    def __init__(
        self,
        pack_id: str | Sequence[str] | None = None,
        *,
        frame_pack: str | None = None,
        config: RuntimeConfig = DEFAULT_CONFIG,
    ) -> None:
        if pack_id is not None or frame_pack is not None:
            pack_ids = (pack_id,) if isinstance(pack_id, str) else tuple(pack_id or config.input_packs)
            # Use dataclasses.replace so newer RuntimeConfig fields
            # (identity_pack, ethics_pack, forward_graph_constraint,
            # composed_surface, thread_anaphora, etc.) survive the
            # pack_id / frame_pack override path.  The previous manual
            # reconstruction silently dropped any field not enumerated
            # here, which would let a caller like
            # ``ChatRuntime(pack_id="x", config=RuntimeConfig(composed_surface=True))``
            # lose composed_surface without warning.
            from dataclasses import replace as _dc_replace
            resolved_config = _dc_replace(
                config,
                input_packs=pack_ids,
                frame_pack=frame_pack or config.frame_pack,
            )
        else:
            resolved_config = config
            pack_ids = tuple(config.input_packs)

        self.config = resolved_config
        manifests = []
        manifolds = []
        entries = []
        for mounted_pack_id in pack_ids:
            manifest, manifold = load_pack(mounted_pack_id)
            manifests.append(manifest)
            manifolds.append(manifold)
            entries.extend(load_pack_entries(mounted_pack_id))

        manifold = manifolds[0] if len(pack_ids) == 1 else load_mounted_packs(pack_ids)
        self._manifests = tuple(manifests)
        identity_pack_id = resolved_config.identity_pack or DEFAULT_IDENTITY_PACK
        identity_manifold = load_identity_manifold(identity_pack_id)
        self.safety_pack = load_safety_pack()
        ethics_pack_id = resolved_config.ethics_pack or _DEFAULT_ETHICS_PACK
        try:
            self.ethics_pack = load_ethics_pack(ethics_pack_id)
        except EthicsPackError:
            if ethics_pack_id == _DEFAULT_ETHICS_PACK:
                raise
            self.ethics_pack = load_ethics_pack(_DEFAULT_ETHICS_PACK)
            ethics_pack_id = _DEFAULT_ETHICS_PACK
        self.ethics_pack_id = ethics_pack_id
        self.identity_manifold = type(identity_manifold)(
            value_axes=identity_manifold.value_axes,
            boundary_ids=(
                identity_manifold.boundary_ids
                | self.safety_pack.boundary_ids
                | self.ethics_pack.commitment_ids
            ),
            alignment_threshold=identity_manifold.alignment_threshold,
            surface_preferences=identity_manifold.surface_preferences,
        )
        self.identity_pack_id = identity_pack_id
        persona_motor = PersonaMotor.identity()
        self._context = SessionContext(
            manifold,
            persona=persona_motor,
            vault_reproject_interval=resolved_config.vault_reproject_interval,
        )
        self._frame_registry = FrameRegistry.from_pack(resolved_config.frame_pack, self._context.vocab)
        self._surface_by_fold = {e.surface.casefold(): e.surface for e in entries}
        self._surface_by_fold.update(_SEED_ALIASES)
        self._pos_by_surface = {e.surface: (e.pos or e.part_of_speech or "X") for e in entries}
        self.exertion_meter = ExertionMeter(capacity_ceiling=128.0)
        self.drive_gradients = tuple(GradientField(axis=axis, magnitude=0.75) for axis in self.identity_manifold.value_axes)
        self._drive_map = DriveGradientMap(gradients=self.drive_gradients)
        self.character_profile = CharacterProfile.from_manifold(
            self.identity_manifold,
            drive_summaries={g.axis.name: g.magnitude for g in self.drive_gradients},
            fatigue_index=0.0,
        )
        self._identity_check = IdentityCheck()
        self.safety_check = SafetyCheck()
        self.ethics_check = EthicsCheck()
        self._identity_manifold_hash: str = _hash_identity_manifold(
            self.identity_manifold,
        )
        self._last_refusal_was_typed: bool = True
        self.turn_log: List[TurnEvent] = []
        from chat.thread_context import ThreadContext
        self.thread_context = ThreadContext()
        self._telemetry_sink: TurnEventSink | None = None
        self._telemetry_include_content: bool = False
        self._discovery_sink: DiscoveryCandidateSink | None = None
        self._oov_sink: Any = None
        self._contemplate_discoveries: bool = False
        self._correction_pass = CorrectionPass()
        self._last_valence: float = 0.0

    @property
    def session(self) -> SessionContext:
        return self._context

    def attach_telemetry_sink(
        self,
        sink: TurnEventSink | None,
        *,
        include_content: bool = False,
    ) -> None:
        """ADR-0040 — attach a structured-logging sink."""
        self._telemetry_sink = sink
        self._telemetry_include_content = bool(include_content)

    def attach_oov_sink(self, sink: Any) -> None:
        """Phase 2.3 — attach an OOV candidate sink."""
        self._oov_sink = sink

    def attach_discovery_sink(
        self,
        sink: DiscoveryCandidateSink | None,
    ) -> None:
        """ADR-0055 Phase B — attach a DiscoveryCandidate sink."""
        self._discovery_sink = sink

    def attach_contemplation(self, *, enabled: bool = True) -> None:
        """ADR-0056 Phase C1 — opt-in inline contemplation."""
        self._contemplate_discoveries = bool(enabled)

    def _push_thread_summary(
        self,
        *,
        turn_event: TurnEvent,
        intent_tag: Any,
        intent_subject: str | None,
        grounding_source: str | None,
        surface: str | None = None,
    ) -> None:
        """P3.1 — append one TurnSummary to the bounded session-thread context."""
        from chat.thread_context import TurnSummary

        turn_index = len(self.turn_log) - 1
        if intent_tag is not None and hasattr(intent_tag, "name"):
            intent_name = str(intent_tag.name).lower()
        else:
            intent_name = ""
        subject = (intent_subject or "").strip().lower()
        source = (grounding_source or "none").lower()

        chain_id: str | None = None
        corpus_id: str | None = None
        if source == "teaching" and subject and intent_name in {"cause", "verification"}:
            from chat.teaching_grounding import _all_chains_index
            chain = _all_chains_index().get((subject, intent_name))
            if chain is not None:
                chain_id = chain.chain_id
                corpus_id = chain.corpus_id
        _ = surface

        self.thread_context.push(
            TurnSummary(
                turn_index=turn_index,
                intent_tag_name=intent_name,
                subject=subject,
                grounding_source=source,
                chain_id=chain_id,
                corpus_id=corpus_id,
            )
        )

    def _emit_oov_candidate(
        self,
        *,
        turn_event: TurnEvent,
        intent_tag: Any,
        token: str | None,
    ) -> None:
        """P2.3 — emit one OOVCandidate per OOV-grounded turn."""
        sink = self._oov_sink
        if sink is None or not token:
            return
        from teaching.oov_sink import (
            OOVCandidate,
            format_oov_candidate_jsonl,
            hash_oov_candidate_id,
        )
        from generate.intent import IntentTag

        if intent_tag is None or not isinstance(intent_tag, IntentTag):
            return
        intent_name = intent_tag.name.lower()
        trace_hash = getattr(turn_event, "trace_hash", "") or ""
        boundary_clean = (
            not getattr(turn_event, "refusal_emitted", False)
            and not getattr(turn_event, "hedge_injected", False)
        )
        cleaned_token = (token or "").strip().lower()
        if not cleaned_token:
            return
        candidate_id = hash_oov_candidate_id(cleaned_token, intent_name, trace_hash)
        candidate = OOVCandidate(
            candidate_id=candidate_id,
            token=cleaned_token,
            intent=intent_name,  # type: ignore[arg-type]
            trigger="unresolved_subject",
            source_turn_trace=trace_hash,
            boundary_clean=boundary_clean,
        )
        sink.emit(format_oov_candidate_jsonl(candidate))

    def _emit_discovery_candidates(
        self,
        *,
        turn_event: TurnEvent,
        intent_tag: Any,
        intent_subject: str | None,
        grounding_source: str | None,
    ) -> None:
        sink = self._discovery_sink
        if sink is None:
            return
        candidates = extract_discovery_candidates(
            turn_event,
            intent_tag,
            intent_subject,
            grounding_source=grounding_source,
        )
        if self._contemplate_discoveries and candidates:
            from teaching.contemplation import contemplate
            candidates = tuple(contemplate(c) for c in candidates)
        for candidate in candidates:
            sink.emit(format_candidate_jsonl(candidate))

    def _emit_turn_event(self, event: TurnEvent) -> None:
        sink = self._telemetry_sink
        if sink is None:
            return
        line = format_turn_event_jsonl(
            event,
            safety_pack_id=self.safety_pack.pack_id,
            ethics_pack_id=self.ethics_pack_id,
            identity_pack_id=self.identity_pack_id,
            include_content=self._telemetry_include_content,
        )
        sink.emit(line)

    def _tokenize(self, text: str) -> list[str]:
        return [self._surface_by_fold.get(m.group(0).casefold(), m.group(0)) for m in _TOKEN_RE.finditer(text)]

    def tokenize(self, text: str) -> list[str]:
        return self._tokenize(text)

    def _apply_oov_policy(self, tokens: list[str]) -> list[str]:
        kept: list[str] = []
        for token in tokens:
            try:
                self._context.vocab.get_versor(token)
                kept.append(token)
            except KeyError:
                if all(manifest.oov_policy is OOVPolicy.FAIL_CLOSED for manifest in self._manifests):
                    raise
                if any(manifest.oov_policy is OOVPolicy.PROPOSE_VOCAB_EXPANSION for manifest in self._manifests):
                    raise KeyError(f"OOV token requires vocab proposal: {token}")
                kept.append(token)
        return kept

    def _syntactic_guard(self, tokens: tuple[str, ...]) -> list[str]:
        out: list[str] = []
        prev_pos: str | None = None
        for token in tokens:
            pos = self._pos_by_surface.get(token, "X")
            if pos == prev_pos:
                continue
            out.append(token)
            prev_pos = pos
        return out

    def _dialogue_reference(self) -> np.ndarray | None:
        blade = self._context.last_dialogue_blade
        if blade is None or float(np.linalg.norm(blade)) < 1e-8:
            return None
        return blade

    def _apply_drive_bias(self, field_state: FieldState) -> FieldState:
        return field_state

    def _build_surface_context(self, identity_score, current_valence: float) -> SurfaceContext:
        active = self._context.referents.active_referent()
        alignment = float(identity_score.alignment) if identity_score is not None else 1.0
        deviation_axes = (
            frozenset(identity_score.deviation_axes)
            if identity_score is not None
            else frozenset()
        )
        prefs = self.identity_manifold.surface_preferences
        axis_hedges = tuple(
            (axis_id, hedge.strong, hedge.soft, hedge.qualifier)
            for axis_id, hedge in prefs.axis_hedges
        )
        return SurfaceContext(
            active_referent_surface=active.surface if active is not None else "",
            active_referent_slot=active.slot if active is not None else "neut_sg",
            identity_alignment=alignment,
            valence_delta=current_valence - self._last_valence,
            elab_conjunction="",
            hedge_threshold_strong=prefs.hedge_threshold_strong,
            hedge_threshold_soft=prefs.hedge_threshold_soft,
            preferred_hedge_strong=prefs.preferred_hedge_strong,
            preferred_hedge_soft=prefs.preferred_hedge_soft,
            claim_strength=prefs.claim_strength,
            qualified_band_high=prefs.qualified_band_high,
            preferred_qualifier=prefs.preferred_qualifier,
            deviation_axes=deviation_axes,
            axis_hedges=axis_hedges,
        )

    def _maybe_pack_grounded_surface(
        self, text: str, gate_source: str, *, allow_warm: bool = False
    ) -> tuple[str, str] | None:
        """Return ``(surface, grounding_source)`` or ``None``.

        ADR-0048 / ADR-0050 / ADR-0052 — three reviewed sources of
        cold-start grounding share this dispatcher.

        ``allow_warm=True`` bypasses the empty-vault gate so the warm
        path can engage pack-grounding for pack-resident DEFINITION /
        RECALL / NARRATIVE / EXAMPLE / COMPARISON / PROCEDURE intents
        — addresses ``warm_grounding_stability`` regression where
        turn-2 of the same prompt drifted from a coherent pack surface
        to a walk fragment.  CAUSE / VERIFICATION still return None
        when no teaching chain exists, preserving the discovery signal.
        """
        if not allow_warm and gate_source != "empty_vault":
            return None
        if self.config.output_language != "en":
            return None
        from generate.intent import IntentTag
        from generate.intent_bridge import classify_intent_from_input
        intent = classify_intent_from_input(text)
        if intent.tag is IntentTag.COMPARISON:
            lemma_a = (intent.subject or "").strip().rstrip(".,?!;:")
            lemma_b = (intent.secondary_subject or "").strip().rstrip(".,?!;:")
            if lemma_a and lemma_b:
                surface = pack_grounded_comparison_surface(lemma_a, lemma_b)
                if surface is not None:
                    return (surface, "pack")
                from chat.partial_surface import partial_comparison_surface
                partial = partial_comparison_surface(lemma_a, lemma_b)
                if partial is not None:
                    return (partial[0], "partial")
        if intent.tag is IntentTag.NARRATIVE:
            lemma = (intent.subject or "").strip()
            if lemma:
                from chat.narrative_surface import narrative_grounded_surface
                surface = narrative_grounded_surface(lemma)
                if surface is not None:
                    return (surface, "teaching")
        if intent.tag is IntentTag.EXAMPLE:
            lemma = (intent.subject or "").strip()
            if lemma:
                from chat.example_surface import example_grounded_surface
                surface = example_grounded_surface(lemma)
                if surface is not None:
                    return (surface, "teaching")
        if intent.tag in (IntentTag.CAUSE, IntentTag.VERIFICATION):
            lemma = (intent.subject or "").strip()
            if lemma:
                if self.config.composed_surface:
                    surface = teaching_grounded_surface_composed(lemma, intent.tag)
                else:
                    surface = teaching_grounded_surface(lemma, intent.tag)
                if surface is not None:
                    return (surface, "teaching")
                from chat.cross_pack_grounding import cross_pack_grounded_surface
                surface = cross_pack_grounded_surface(lemma, intent.tag)
                if surface is not None:
                    return (surface, "teaching")
                # Deliberate non-fallback: when CAUSE / VERIFICATION
                # has no teaching chain or cross-pack chain rooted on
                # the subject, return None so the discovery layer logs
                # a "would_have_grounded" candidate identifying the
                # teaching-content gap.  Emitting the bare pack
                # disclosure here would mask that signal and give the
                # user a non-answer (a definition rather than a cause).
                # See ``tests/test_discovery_candidates``.
        if intent.tag is IntentTag.CORRECTION:
            surface = pack_grounded_correction_surface(text)
            if surface is not None:
                return (surface, "pack")
        if intent.tag is IntentTag.PROCEDURE:
            subject_text = (intent.subject or "").strip()
            if subject_text:
                surface = pack_grounded_procedure_surface(subject_text)
                if surface is not None:
                    return (surface, "pack")
        if intent.tag in (IntentTag.DEFINITION, IntentTag.RECALL):
            lemma = (intent.subject or "").strip()
            if not lemma:
                return None
            surface = pack_grounded_surface(lemma)
            if surface is not None:
                return (surface, "pack")
        oov_lemma = (intent.subject or "").strip()
        if oov_lemma:
            from chat.oov_surface import oov_learning_invitation_surface
            oov_surface = oov_learning_invitation_surface(oov_lemma, intent.tag)
            if oov_surface is not None:
                return (oov_surface, "oov")
        return None

    def _stub_response(
        self,
        field_state: FieldState,
        *,
        tokens: tuple[str, ...] = (),
        pack_grounded_surface: str | None = None,
        grounded_source_tag: str = "pack",
        discovery_intent_tag: Any = None,
        discovery_intent_subject: str | None = None,
    ) -> ChatResponse:
        zero = np.zeros(field_state.F.shape, dtype=np.float32)
        prop = Proposition(
            subject="",
            predicate="",
            object_=None,
            surface=_UNKNOWN_DOMAIN_SURFACE,
            frame_id="unknown_domain",
            subject_versor=zero,
            predicate_versor=zero,
            object_versor=None,
            relation=zero,
        )
        art = ArticulationPlan(
            subject="",
            predicate="",
            object=None,
            surface=_UNKNOWN_DOMAIN_SURFACE,
            output_language=self.config.output_language,
            frame_id="unknown_domain",
        )
        safety_ctx = SafetyContext(
            field_state=_FieldStateWithVersor(
                versor_condition=float(versor_condition(field_state.F)),
            ),
            last_refusal_was_typed=self._last_refusal_was_typed,
            identity_manifold_hash_before=self._identity_manifold_hash,
            identity_manifold_hash_after=_hash_identity_manifold(self.identity_manifold),
        )
        safety_verdict = self.safety_check.check(safety_ctx, self.safety_pack)
        ethics_ctx = EthicsContext(
            alignment_score=0.0,
            hedge_threshold_soft=float(
                self.identity_manifold.surface_preferences.hedge_threshold_soft
            ),
            hedge_emitted=False,
            grounded_in_evidence=False,
            disclosure_emitted=True,
        )
        ethics_verdict = self.ethics_check.check(ethics_ctx, self.ethics_pack)
        refusal_surface = build_refusal_surface(
            safety_verdict, ethics_verdict, self.ethics_pack,
        )
        refusal_emitted = refusal_surface is not None
        if refusal_emitted:
            response_surface = refusal_surface
            self._last_refusal_was_typed = True
        elif pack_grounded_surface is not None:
            response_surface = pack_grounded_surface
            if (
                self.config.thread_anaphora
                and grounded_source_tag in {"pack", "teaching"}
                and discovery_intent_subject
                and discovery_intent_tag is not None
            ):
                from chat.anaphora import thread_anaphora_prefix
                prefix = thread_anaphora_prefix(
                    self.thread_context,
                    discovery_intent_subject,
                    discovery_intent_tag.name.lower(),
                    grounded_source_tag,
                )
                if prefix is not None:
                    response_surface = prefix + response_surface
        else:
            response_surface = _UNKNOWN_DOMAIN_SURFACE
        if pack_grounded_surface is not None and not refusal_emitted:
            grounding_source = grounded_source_tag
        else:
            grounding_source = "none"
        verdicts_bundle = TurnVerdicts(
            identity_score=None,
            safety_verdict=safety_verdict,
            ethics_verdict=ethics_verdict,
            refusal_emitted=refusal_emitted,
            hedge_injected=False,
        )
        if tokens:
            stub_event = TurnEvent(
                turn=max(self._context.turn - 1, 0),
                input_tokens=tokens,
                surface=response_surface,
                walk_surface=_UNKNOWN_DOMAIN_SURFACE,
                articulation_surface=_UNKNOWN_DOMAIN_SURFACE,
                dialogue_role="assert",
                identity_score=None,
                cycle_cost_total=0.0,
                vault_hits=0,
                versor_condition=float(versor_condition(field_state.F)),
                flagged=False,
                elaboration=None,
                safety_verdict=safety_verdict,
                ethics_verdict=ethics_verdict,
                verdicts=verdicts_bundle,
                grounding_source=grounding_source,
            )
            self.turn_log.append(stub_event)
            self._emit_turn_event(stub_event)
            if discovery_intent_tag is not None:
                self._emit_discovery_candidates(
                    turn_event=stub_event,
                    intent_tag=discovery_intent_tag,
                    intent_subject=discovery_intent_subject,
                    grounding_source=grounding_source,
                )
                if grounding_source == "oov":
                    self._emit_oov_candidate(
                        turn_event=stub_event,
                        intent_tag=discovery_intent_tag,
                        token=discovery_intent_subject,
                    )
            self._push_thread_summary(
                turn_event=stub_event,
                intent_tag=discovery_intent_tag,
                intent_subject=discovery_intent_subject,
                grounding_source=grounding_source,
                surface=response_surface,
            )
        return ChatResponse(
            surface=response_surface,
            proposition=prop,
            articulation=art,
            articulation_surface=_UNKNOWN_DOMAIN_SURFACE,
            dialogue_role="assert",
            versor_condition=versor_condition(field_state.F),
            output_language=self.config.output_language,
            frame_pack=self.config.frame_pack,
            walk_surface=_UNKNOWN_DOMAIN_SURFACE,
            salience_top_k=None,
            candidates_used=None,
            vault_hits=0,
            identity_score=None,
            character_profile=self.character_profile,
            flagged=False,
            safety_verdict=safety_verdict,
            ethics_verdict=ethics_verdict,
            verdicts=verdicts_bundle,
            grounding_source=grounding_source,
        )

    def chat(self, text: str, max_tokens: int | None = None) -> ChatResponse:
        tokens = self._tokenize(text)
        filtered = self._apply_oov_policy(tokens)
        if not filtered:
            raise ValueError("ChatRuntime.chat() received no in-vocabulary tokens.")

        probe_state = self._context.probe_ingest(filtered)
        direct_hits = self._context.vault.recall(probe_state.F, top_k=3)
        direct_best = max((h["score"] for h in direct_hits), default=0.0)
        gate_decision = default_gate.check(
            direct_best,
            vault=self._context.vault,
            query=probe_state.F,
            decomposer=default_decomposer,
        )
        if gate_decision.fire:
            committed = self._context.commit_ingest(filtered)
            empty_result = GenerationResult(tokens=(), final_state=committed, vault_hits=0)
            pack_result = self._maybe_pack_grounded_surface(
                text, gate_decision.source
            )
            if pack_result is None:
                pack_surface = None
                pack_source_tag = "none"
            else:
                pack_surface, pack_source_tag = pack_result
            self._context.finalize_turn(
                empty_result,
                tokens_in=tuple(filtered),
                input_versor=committed.F,
                dialogue_role="assert",
                metadata={
                    "unknown": True,
                    "unknown_source": gate_decision.source,
                    "grounding_source": pack_source_tag if pack_surface else "none",
                },
            )
            discovery_intent_tag = None
            discovery_intent_subject: str | None = None
            if (
                gate_decision.source == "empty_vault"
                and self.config.output_language == "en"
            ):
                from generate.intent_bridge import classify_intent_from_input
                _intent = classify_intent_from_input(text)
                discovery_intent_tag = _intent.tag
                discovery_intent_subject = _intent.subject
            return self._stub_response(
                committed,
                tokens=tuple(filtered),
                pack_grounded_surface=pack_surface,
                grounded_source_tag=pack_source_tag,
                discovery_intent_tag=discovery_intent_tag,
                discovery_intent_subject=discovery_intent_subject,
            )

        field_state = self._context.commit_ingest(filtered)
        field_state = self._apply_drive_bias(field_state)
        reference_blade = self._dialogue_reference()
        base_proposition = propose(
            field_state,
            None,
            self._context.vocab,
            self._frame_registry,
            output_lang=self.config.output_language,
        )
        dialogue_role = _stable_dialogue_role(
            classify_dialogue_blade(base_proposition.relation, reference_blade),
            raw_text=text,
            tokens=tokens,
        )
        proposition = propose_dialogue(
            field_state,
            self._context.vault,
            self._context.vocab,
            self._frame_registry,
            reference_blade,
            output_lang=self.config.output_language,
        )
        articulation = realize(proposition, self._context.vocab, output_language=self.config.output_language)
        articulation = _prefer_prompt_anchor(articulation, filtered, output_language=self.config.output_language)
        self._context.record_dialogue(proposition)

        forward_region = None
        if self.config.forward_graph_constraint and self.config.output_language == "en":
            pre_gen_graph = build_graph_from_input(text, articulation)
            forward_region = build_graph_constraint(pre_gen_graph, self._context.vocab)

        result = generate(
            field_state,
            self._context.vocab,
            self._context.persona,
            max_tokens=self.config.max_tokens if max_tokens is None else max_tokens,
            record_trajectory=True,
            vault=self._context.vault,
            recall_top_k=3 if self.config.allow_cross_language_recall else 0,
            output_lang=self.config.output_language,
            allow_cross_language_generation=self.config.allow_cross_language_generation,
            use_salience=self.config.use_salience,
            salience_top_k=self.config.salience_top_k,
            inhibition_threshold=self.config.inhibition_threshold,
            region=forward_region,
            inner_loop_admissibility=self.config.inner_loop_admissibility,
            admissibility_threshold=self.config.admissibility_threshold,
            admissibility_mode=self.config.admissibility_mode,
            admissibility_margin=self.config.admissibility_margin,
        )

        # --- Articulation fidelity: replace bare S-P-O join with intent-aware surface ---
        # Phase 2: pass proposition so the bridge grounds <pending> obj slots
        # from pack-resolved proposition slots (primary) rather than walk
        # tokens (supplemental backfill only).  walk_tokens still participates
        # as a fallback when proposition.object_ is None/empty.
        if self.config.output_language == "en":
            walk_tokens = tuple(
                tok for tok in (result.tokens or ()) if tok and tok.isalpha()
            )
            intent_surface = articulate_with_intent(
                text,
                articulation,
                walk_tokens,
                proposition=proposition,
            )
            if intent_surface:
                articulation = replace(articulation, surface=intent_surface)
        # --- end articulation fidelity ---

        reasoning_trajectory = _make_trajectory_from_result(result, self._context.turn)
        identity_score = self._identity_check.check(reasoning_trajectory, self.identity_manifold)
        flagged = identity_score.flagged
        cycle_cost = CycleCost(
            cycle_index=self._context.turn,
            attention_cost=float(result.candidates_used or 0),
            inhibition_cost=float(self.config.inhibition_threshold),
            digest_cost=0.0,
            trajectory_cost=float(len(result.trajectory or ())),
        )
        self.exertion_meter.record(cycle_cost)
        fatigue = self.exertion_meter.fatigue(at_cycle=self._context.turn)
        self.character_profile = CharacterProfile.from_manifold(
            self.identity_manifold,
            drive_summaries={g.axis.name: g.magnitude * (1.0 - fatigue.value) for g in self.drive_gradients},
            fatigue_index=fatigue.value,
        )

        self._context.finalize_turn(
            result,
            tokens_in=tuple(filtered),
            dialogue_role=str(dialogue_role),
        )
        current_valence = _energy_scalar(getattr(result.final_state, "valence", None))
        surface_ctx = self._build_surface_context(identity_score, current_valence)
        self._last_valence = current_valence
        surface = _terminate_surface(articulation.surface, role=dialogue_role, output_language=self.config.output_language)
        articulation = replace(articulation, surface=surface)
        sentence_plan: SentencePlan = SentenceAssembler().assemble(
            articulation,
            result.tokens,
            role=dialogue_role,
            context=surface_ctx,
        )
        walk_surface = sentence_plan.surface
        vault_hits = int(result.vault_hits)
        is_grounded = walk_surface != _UNKNOWN_DOMAIN_SURFACE
        hedge_emitted = _surface_contains_hedge(walk_surface, self.identity_manifold)
        safety_ctx = SafetyContext(
            field_state=_FieldStateWithVersor(
                versor_condition=float(versor_condition(result.final_state.F)),
            ),
            last_refusal_was_typed=self._last_refusal_was_typed,
            identity_manifold_hash_before=self._identity_manifold_hash,
            identity_manifold_hash_after=_hash_identity_manifold(self.identity_manifold),
        )
        safety_verdict = self.safety_check.check(safety_ctx, self.safety_pack)
        ethics_ctx = EthicsContext(
            alignment_score=float(getattr(identity_score, "alignment", 0.0)),
            hedge_threshold_soft=float(
                self.identity_manifold.surface_preferences.hedge_threshold_soft
            ),
            hedge_emitted=hedge_emitted,
            grounded_in_evidence=is_grounded,
            disclosure_emitted=not is_grounded,
        )
        ethics_verdict = self.ethics_check.check(ethics_ctx, self.ethics_pack)
        refusal_surface = build_refusal_surface(
            safety_verdict, ethics_verdict, self.ethics_pack,
        )
        refusal_emitted = refusal_surface is not None
        hedge_injected = False
        warm_grounding_source: str | None = None
        warm_pack_subject: str | None = None
        warm_pack_intent_tag: Any = None
        if refusal_emitted:
            response_surface = refusal_surface
            self._last_refusal_was_typed = True
        else:
            response_surface = walk_surface
            warm_pack_result = self._maybe_pack_grounded_surface(
                text, "warm", allow_warm=True
            )
            if warm_pack_result is None:
                from generate.intent import IntentTag
                from generate.intent_bridge import classify_intent_from_input
                _wintent = classify_intent_from_input(text)
                # Discovery-signal preservation on warm path: when CAUSE /
                # VERIFICATION lacks both a teaching chain and a cross-pack
                # chain, the cold path emits the unknown-domain disclosure.
                # The warm path must match — fabricating a vault-grounded
                # walk fragment ("Work infer.") would mask the very gap
                # the discovery layer is meant to surface.
                if _wintent.tag in (IntentTag.CAUSE, IntentTag.VERIFICATION):
                    response_surface = _UNKNOWN_DOMAIN_SURFACE
                    articulation = replace(articulation, surface=_UNKNOWN_DOMAIN_SURFACE)
                    warm_grounding_source = "none"
            elif warm_pack_result is not None:
                warm_pack_surface, warm_grounding_source = warm_pack_result
                if self.config.thread_anaphora and warm_grounding_source in {"pack", "teaching"}:
                    from chat.anaphora import thread_anaphora_prefix
                    from generate.intent_bridge import classify_intent_from_input
                    _wintent = classify_intent_from_input(text)
                    warm_pack_intent_tag = _wintent.tag
                    warm_pack_subject = _wintent.subject
                    if warm_pack_subject and warm_pack_intent_tag is not None:
                        prefix = thread_anaphora_prefix(
                            self.thread_context,
                            warm_pack_subject,
                            warm_pack_intent_tag.name.lower(),
                            warm_grounding_source,
                        )
                        if prefix is not None:
                            warm_pack_surface = prefix + warm_pack_surface
                response_surface = warm_pack_surface
                articulation = replace(articulation, surface=warm_pack_surface)
                # Step 5 — discourse planner.  Opt-in; engages only on
                # pack/teaching-grounded turns where the response mode
                # asks for more than a single-sentence brief.  When the
                # planner returns a multi-move plan, replace the warm
                # surface with the deterministic multi-clause rendering.
                # BRIEF mode always collapses to a single ANCHOR move so
                # the flag-off path stays byte-identical to the existing
                # composer.
                if (
                    self.config.discourse_planner
                    and warm_grounding_source in {"pack", "teaching"}
                ):
                    from generate.discourse_planner import (
                        plan_discourse,
                        render_plan,
                    )
                    from generate.grounding_accessors import (
                        grounding_bundle_for,
                    )
                    from generate.intent import classify_response_mode
                    from generate.intent_bridge import (
                        classify_intent_from_input,
                    )

                    _dintent = classify_intent_from_input(text)
                    _dmode = classify_response_mode(text)
                    if _dintent.subject:
                        _dbundle = grounding_bundle_for(_dintent.subject)
                        _dplan = plan_discourse(_dintent, _dmode, _dbundle)
                        if len(_dplan.moves) > 1:
                            _drendered = render_plan(_dplan)
                            if _drendered:
                                response_surface = _drendered
                                articulation = replace(
                                    articulation, surface=_drendered
                                )
            if should_inject_hedge(ethics_verdict, self.ethics_pack):
                hedge_prefix = build_hedge_prefix(self.identity_manifold)
                before = response_surface
                response_surface = inject_hedge(response_surface, hedge_prefix)
                hedge_injected = response_surface != before
        verdicts_bundle = TurnVerdicts(
            identity_score=identity_score,
            safety_verdict=safety_verdict,
            ethics_verdict=ethics_verdict,
            refusal_emitted=refusal_emitted,
            hedge_injected=hedge_injected,
        )
        turn_event = TurnEvent(
            turn=self._context.turn - 1,
            input_tokens=tuple(filtered),
            surface=response_surface,
            walk_surface=walk_surface,
            articulation_surface=articulation.surface,
            dialogue_role=str(dialogue_role),
            identity_score=identity_score,
            cycle_cost_total=cycle_cost.total,
            vault_hits=vault_hits,
            versor_condition=versor_condition(result.final_state.F),
            flagged=flagged,
            elaboration=sentence_plan.elaboration,
            safety_verdict=safety_verdict,
            ethics_verdict=ethics_verdict,
            verdicts=verdicts_bundle,
            grounding_source=warm_grounding_source or "vault",
        )
        self.turn_log.append(turn_event)
        self._emit_turn_event(turn_event)
        self._push_thread_summary(
            turn_event=turn_event,
            intent_tag=warm_pack_intent_tag,
            intent_subject=warm_pack_subject or articulation.subject,
            grounding_source=warm_grounding_source or "vault",
            surface=response_surface,
        )
        return ChatResponse(
            surface=response_surface,
            proposition=proposition,
            articulation=articulation,
            articulation_surface=articulation.surface,
            dialogue_role=dialogue_role,
            versor_condition=versor_condition(result.final_state.F),
            output_language=self.config.output_language,
            frame_pack=self.config.frame_pack,
            walk_surface=walk_surface,
            salience_top_k=result.salience_top_k,
            candidates_used=result.candidates_used,
            vault_hits=vault_hits,
            identity_score=identity_score,
            character_profile=self.character_profile,
            flagged=flagged,
            admissibility_trace=result.admissibility_trace,
            region_was_unconstrained=result.region_was_unconstrained,
            safety_verdict=safety_verdict,
            ethics_verdict=ethics_verdict,
            verdicts=verdicts_bundle,
            grounding_source=warm_grounding_source or "vault",
        )

    def _unknown_domain_response(self, field_state: FieldState, filtered: list[str]) -> ChatResponse:
        return self._stub_response(field_state)

    def respond(self, text: str, max_tokens: int | None = None) -> str:
        """Return only the user-facing surface string for *text*.

        Convenience wrapper around :meth:`chat` for callers that need
        the raw surface without ChatResponse provenance — REPLs, simple
        scripts, and the existing test_language_pack_runtime suite.
        For audit / telemetry / verdict access, call :meth:`chat`.
        """
        return self.chat(text, max_tokens=max_tokens).surface

    async def achat(self, text: str, max_tokens: int | None = None) -> ChatResponse:
        """Async-compatible convenience wrapper around :meth:`chat`.

        This is a thin async surface; the underlying call is still
        synchronous CPU-bound work (versor walk, vault recall, surface
        composition).  Use this only for integration with asyncio-based
        callers that need an awaitable.  No real off-thread execution
        is performed — if true non-blocking concurrency is required,
        wrap calls in :func:`asyncio.to_thread` at the call site.
        """
        return self.chat(text, max_tokens=max_tokens)

    async def arespond(self, text: str, max_tokens: int | None = None) -> str:
        """Async-compatible convenience wrapper around :meth:`respond`.

        Same caveats as :meth:`achat` — wrapper, not true async.
        """
        return self.respond(text, max_tokens=max_tokens)

    def correct(self, text: str, target_turn: int = -1, max_tokens: int | None = None) -> ChatResponse:
        tokens = self._tokenize(text)
        filtered = self._apply_oov_policy(tokens)
        if not filtered:
            raise ValueError("correct() received no in-vocabulary tokens.")
        correction_state = inject(filtered, self._context.vocab)
        correction_result = self._correction_pass.apply(
            self._context.graph,
            correction_state.F,
            from_turn=target_turn,
        )
        self._context.apply_corrected_outputs(correction_result.records)
        self._emit_correction_event(correction_result, target_turn=target_turn)
        regen_tokens = self._context.last_input_tokens
        if not regen_tokens:
            return self._stub_response(correction_state)
        return self.chat(" ".join(regen_tokens), max_tokens=max_tokens)

    def _emit_correction_event(
        self, correction_result, *, target_turn: int,
    ) -> None:
        """ADR-0059 — emit one JSONL correction event to the telemetry sink."""
        sink = self._telemetry_sink
        if sink is None:
            return
        line = format_correction_event_jsonl(
            correction_result,
            target_turn=target_turn,
            identity_pack_id=self.identity_pack_id,
            safety_pack_id=self.safety_pack.pack_id,
            ethics_pack_id=self.ethics_pack_id,
        )
        sink.emit(line)
