from __future__ import annotations

from dataclasses import dataclass, replace
import re
from collections.abc import Sequence
from typing import List

import numpy as np

from algebra.versor import versor_condition
from core.config import DEFAULT_CONFIG, RuntimeConfig
from core.physics.drive import DriveGradientMap, GradientField, ValueAxis
from core.physics.energy import EnergyProfile
from core.physics.exertion import CycleCost, ExertionMeter
from core.physics.identity import (
    CharacterProfile,
    IdentityCheck,
    IdentityManifold,
    IdentityScore,
    TurnEvent,
)
from field.state import FieldState
from generate.articulation import ArticulationPlan, realize
from generate.dialogue import DialogueRole, classify_dialogue_blade, propose_dialogue
from generate.intent_bridge import articulate_with_intent
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
            resolved_config = RuntimeConfig(
                input_packs=pack_ids,
                output_language=config.output_language,
                frame_pack=frame_pack or config.frame_pack,
                max_tokens=config.max_tokens,
                allow_cross_language_recall=config.allow_cross_language_recall,
                allow_cross_language_generation=config.allow_cross_language_generation,
                vault_reproject_interval=config.vault_reproject_interval,
                use_salience=config.use_salience,
                salience_top_k=config.salience_top_k,
                inhibition_threshold=config.inhibition_threshold,
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
        self.identity_manifold = _default_identity_manifold()
        # Keep the generic runtime neutral. Identity/persona motivation belongs
        # behind an explicit IdentityProfile contract, not the baseline chat path.
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
        self.turn_log: List[TurnEvent] = []
        self._correction_pass = CorrectionPass()
        self._last_valence: float = 0.0

    @property
    def session(self) -> SessionContext:
        return self._context

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
        """Generic runtime keeps motivation/drive disabled.

        Motivation is an identity-profile concern, not a free runtime field
        mutation. Keeping this a no-op preserves the neutral baseline while
        generic chat closure and cognition evals are being stabilized.
        """
        return field_state

    def _build_surface_context(self, identity_score, current_valence: float) -> SurfaceContext:
        active = self._context.referents.active_referent()
        alignment = float(identity_score.alignment) if identity_score is not None else 1.0
        return SurfaceContext(
            active_referent_surface=active.surface if active is not None else "",
            active_referent_slot=active.slot if active is not None else "neut_sg",
            identity_alignment=alignment,
            valence_delta=current_valence - self._last_valence,
            elab_conjunction="",
        )

    def _stub_response(self, field_state: FieldState) -> ChatResponse:
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
        return ChatResponse(
            surface=_UNKNOWN_DOMAIN_SURFACE,
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
        )

    def chat(self, text: str, max_tokens: int | None = None) -> ChatResponse:
        tokens = self._tokenize(text)
        filtered = self._apply_oov_policy(tokens)
        if not filtered:
            raise ValueError("ChatRuntime.chat() received no in-vocabulary tokens.")

        probe_state = self._context.probe_ingest(filtered)
        # INV-24 recall role: RECOGNITION.  Feeds UnknownDomainGate — asks
        # "have we seen anything like this before?", not "what is admissible
        # evidence?".  Session-tier SPECULATIVE memory must count here, so
        # no min_status filter is applied.
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
            self._context.finalize_turn(
                empty_result,
                tokens_in=tuple(filtered),
                input_versor=committed.F,
                dialogue_role="assert",
                metadata={"unknown": True, "unknown_source": gate_decision.source},
            )
            return self._stub_response(committed)

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
        )

        # --- Articulation fidelity: replace bare S-P-O join with intent-aware surface ---
        # articulate_with_intent() classifies the input intent, builds a proposition
        # graph grounded on the generation result's recalled tokens, and calls the
        # realize_semantic() path (13-construction realizer) that was previously
        # implemented but never connected to the chat hot path.
        # Falls back to the existing articulation.surface when bridge returns "".
        if self.config.output_language == "en":
            recalled_words = tuple(
                tok for tok in (result.tokens or ()) if tok and tok.isalpha()
            )
            intent_surface = articulate_with_intent(text, articulation, recalled_words)
            if intent_surface:
                articulation = replace(articulation, surface=intent_surface)
        # --- end articulation fidelity fix ---

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
        turn_event = TurnEvent(
            turn=self._context.turn - 1,
            input_tokens=tuple(filtered),
            surface=surface,
            walk_surface=walk_surface,
            articulation_surface=articulation.surface,
            dialogue_role=str(dialogue_role),
            identity_score=identity_score,
            cycle_cost_total=cycle_cost.total,
            vault_hits=vault_hits,
            versor_condition=versor_condition(result.final_state.F),
            flagged=flagged,
            elaboration=sentence_plan.elaboration,
        )
        self.turn_log.append(turn_event)
        return ChatResponse(
            surface=walk_surface,
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
        )

    def _unknown_domain_response(self, field_state: FieldState, filtered: list[str]) -> ChatResponse:
        return self._stub_response(field_state)

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
        regen_tokens = self._context.last_input_tokens
        if not regen_tokens:
            return self._stub_response(correction_state)
        return self.chat(" ".join(regen_tokens), max_tokens=max_tokens)

    def respond(self, text: str, max_tokens: int | None = None) -> str:
        try:
            return self.chat(text, max_tokens=max_tokens).surface
        except ValueError:
            return ""

    async def achat(self, text: str, max_tokens: int | None = None) -> ChatResponse:
        return self.chat(text, max_tokens=max_tokens)

    async def arespond(self, text: str, max_tokens: int | None = None) -> str:
        try:
            return (await self.achat(text, max_tokens=max_tokens)).surface
        except ValueError:
            return ""


def _default_identity_manifold() -> IdentityManifold:
    axes = (
        ValueAxis(
            axis_id="truthfulness",
            name="truthfulness",
            direction=(1.0, 0.0, 0.0),
            theological_note="Truth is treated as a fixed value axis, not a prompt preference.",
        ),
        ValueAxis(
            axis_id="coherence",
            name="coherence",
            direction=(0.0, 1.0, 0.0),
            theological_note="Operations must preserve field coherence under propagation.",
        ),
        ValueAxis(
            axis_id="reverence",
            name="reverence",
            direction=(0.0, 0.0, 1.0),
            theological_note="Depth-language handling remains bounded by source structure.",
        ),
    )
    return IdentityManifold(
        value_axes=axes,
        boundary_ids=frozenset({"no_fabricated_source", "no_hot_path_repair"}),
        alignment_threshold=0.45,
    )
