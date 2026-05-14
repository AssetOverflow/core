from __future__ import annotations

from dataclasses import dataclass
import re
from collections.abc import Sequence
from typing import List

import numpy as np

from algebra.versor import versor_condition
from core.config import DEFAULT_CONFIG, RuntimeConfig
from core.physics.drive import DriveGradientMap, GradientField, ValueAxis
from core.physics.exertion import CycleCost, ExertionMeter
from core.physics.identity import (
    CharacterProfile,
    IdentityCheck,
    IdentityManifold,
    IdentityScore,
    TurnEvent,
)
from core.physics.reasoning import ReasoningTrajectory, TrajectoryOperator
from field.state import FieldState
from generate.articulation import ArticulationPlan, realize
from generate.dialogue import DialogueRole, classify_dialogue_blade, propose_dialogue
from generate.proposition import FrameRegistry, Proposition, propose
from generate.stream import generate
from language_packs import OOVPolicy, load_mounted_packs, load_pack, load_pack_entries
from persona.motor import PersonaMotor
from session.context import SessionContext

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_SEED_ALIASES = {
    "logos": "λόγος",
    "dabar": "דבר",
    "or": "אור",
    "phos": "φῶς",
    "zoe": "ζωή",
    "arche": "ἀρχή",
    "aletheia": "ἀλήθεια",
}

# ---------------------------------------------------------------------------
# Stub BindingFrame for IdentityCheck — allows check() to run without a full
# reasoning pipeline being wired. Carries the minimum contract that
# ReasoningTrajectory.frames requires: frame_id, coherence_magnitude,
# region_ids, cycle_index.
# ---------------------------------------------------------------------------


@dataclass
class _StubBindingFrame:
    frame_id: str
    coherence_magnitude: float
    region_ids: frozenset
    cycle_index: int


def _make_trajectory_from_result(
    result,
    turn: int,
) -> ReasoningTrajectory:
    """Build a ReasoningTrajectory from a GenerationResult for IdentityCheck.

    If the result carries a recorded trajectory (FieldState sequence), each
    state is mapped to a stub BindingFrame using its energy as coherence_magnitude.
    Otherwise a single-frame fallback is used so IdentityCheck always has
    something to evaluate.
    """
    operator = TrajectoryOperator()
    if result.trajectory:
        frames = [
            _StubBindingFrame(
                frame_id=f"t{turn}_s{i}",
                coherence_magnitude=float(getattr(fs, "energy", 1.0)),
                region_ids=frozenset({str(getattr(fs, "node", 0))}),
                cycle_index=turn,
            )
            for i, fs in enumerate(result.trajectory)
        ]
    else:
        frames = [
            _StubBindingFrame(
                frame_id=f"t{turn}_s0",
                coherence_magnitude=float(getattr(result.final_state, "energy", 1.0)),
                region_ids=frozenset({str(getattr(result.final_state, "node", 0))}),
                cycle_index=turn,
            )
        ]
    return operator.build(frames, trajectory_id=f"turn_{turn}")


@dataclass(frozen=True, slots=True)
class ChatResponse:
    surface: str
    proposition: Proposition
    articulation: ArticulationPlan
    dialogue_role: DialogueRole
    versor_condition: float
    output_language: str
    frame_pack: str
    walk_surface: str
    salience_top_k: int | None
    candidates_used: int | None
    identity_score: IdentityScore | None
    character_profile: CharacterProfile
    flagged: bool


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

        # --- Identity manifold (built first; persona motor derived from it) ---
        self.identity_manifold = _default_identity_manifold()

        # --- Persona motor: non-identity, derived from value_axes directions ---
        persona_motor = PersonaMotor.from_identity_manifold(self.identity_manifold)

        self._context = SessionContext(
            manifold,
            persona=persona_motor,
            vault_reproject_interval=resolved_config.vault_reproject_interval,
        )
        self._frame_registry = FrameRegistry.from_pack(
            resolved_config.frame_pack,
            self._context.vocab,
        )
        self._surface_by_fold = {e.surface.casefold(): e.surface for e in entries}
        self._surface_by_fold.update(_SEED_ALIASES)
        self._pos_by_surface = {
            e.surface: (e.pos or e.part_of_speech or "X") for e in entries
        }

        # --- Physics ---
        self.exertion_meter = ExertionMeter(capacity_ceiling=128.0)
        self.drive_gradients = tuple(
            GradientField(axis=axis, magnitude=0.75)
            for axis in self.identity_manifold.value_axes
        )
        self._drive_map = DriveGradientMap(gradients=self.drive_gradients)

        # --- CharacterProfile: populated from live manifold at init ---
        self.character_profile = CharacterProfile.from_manifold(
            self.identity_manifold,
            drive_summaries={
                g.axis.name: g.magnitude for g in self.drive_gradients
            },
            fatigue_index=0.0,
        )

        # --- Identity checker ---
        self._identity_check = IdentityCheck()

        # --- Provenance log: append-only list of TurnEvents ---
        self.turn_log: List[TurnEvent] = []

    @property
    def session(self) -> SessionContext:
        return self._context

    def _tokenize(self, text: str) -> list[str]:
        tokens: list[str] = []
        for match in _TOKEN_RE.finditer(text):
            raw = match.group(0)
            tokens.append(self._surface_by_fold.get(raw.casefold(), raw))
        return tokens

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
                if any(
                    manifest.oov_policy is OOVPolicy.PROPOSE_VOCAB_EXPANSION
                    for manifest in self._manifests
                ):
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
        """Nudge field F by the combined drive gradient before generation.

        The bias is computed from DriveGradientMap.combined_bias() using the
        first three components of F as the current coordinates. The resulting
        perturbation is added to F[:3] and the state is returned unchanged
        apart from F. Magnitude is bounded by the current fatigue level so
        exhausted sessions receive progressively less drive pressure.
        """
        fatigue = self.exertion_meter.fatigue(at_cycle=self._context.turn)
        # Drive pressure is attenuated by fatigue: more tired = weaker nudge.
        available = 1.0 - fatigue.value
        if available < 1e-4:
            return field_state

        coords = tuple(float(x) for x in field_state.F[:3])
        bias = self._drive_map.combined_bias(coords)
        if not bias or all(abs(b) < 1e-8 for b in bias):
            return field_state

        nudged_F = field_state.F.copy()
        for i, b in enumerate(bias[:3]):
            nudged_F[i] += b * available * 0.1  # scale keeps perturbation small
        return FieldState(
            F=nudged_F,
            node=field_state.node,
            step=field_state.step,
            holonomy=field_state.holonomy,
            energy=field_state.energy,
            valence=field_state.valence,
        )

    def chat(self, text: str, max_tokens: int | None = None) -> ChatResponse:
        tokens = self._tokenize(text)
        filtered = self._apply_oov_policy(tokens)
        if not filtered:
            raise ValueError("ChatRuntime.chat() received no in-vocabulary tokens.")

        field_state = self._context.ingest(filtered)

        # Apply drive gradient bias before generation.
        field_state = self._apply_drive_bias(field_state)

        reference_blade = self._dialogue_reference()
        base_proposition = propose(
            field_state,
            None,
            self._context.vocab,
            self._frame_registry,
            output_lang=self.config.output_language,
        )
        dialogue_role = classify_dialogue_blade(
            base_proposition.relation,
            reference_blade,
        )
        proposition = propose_dialogue(
            field_state,
            self._context.vault,
            self._context.vocab,
            self._frame_registry,
            reference_blade,
            output_lang=self.config.output_language,
        )
        articulation = realize(
            proposition,
            self._context.vocab,
            output_language=self.config.output_language,
        )
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

        # --- IdentityCheck gate ---
        reasoning_trajectory = _make_trajectory_from_result(result, self._context.turn)
        identity_score = self._identity_check.check(
            reasoning_trajectory,
            self.identity_manifold,
        )
        flagged = identity_score.flagged

        cycle_cost = CycleCost(
            cycle_index=self._context.turn,
            attention_cost=float(result.candidates_used or 0),
            inhibition_cost=float(self.config.inhibition_threshold),
            digest_cost=0.0,
            trajectory_cost=float(len(result.trajectory or ())),
        )
        self.exertion_meter.record(cycle_cost)

        # Update CharacterProfile with current fatigue.
        fatigue = self.exertion_meter.fatigue(at_cycle=self._context.turn)
        self.character_profile = CharacterProfile.from_manifold(
            self.identity_manifold,
            drive_summaries={
                g.axis.name: g.magnitude * (1.0 - fatigue.value)
                for g in self.drive_gradients
            },
            fatigue_index=fatigue.value,
        )

        self._context.state = result.final_state
        self._context.vault.store(
            result.final_state.F,
            {"turn": self._context.turn, "role": "assistant"},
        )
        self._context.turn += 1

        guarded = self._syntactic_guard(result.tokens)
        walk_surface = " ".join(guarded)

        # If flagged, suppress walk and fall back to articulation surface.
        surface = articulation.surface if flagged else (articulation.surface or walk_surface)

        # Count vault hits that fired this turn (recall_top_k is the ceiling).
        vault_hits = 3 if self.config.allow_cross_language_recall else 0

        # --- Provenance: append TurnEvent ---
        turn_event = TurnEvent(
            turn=self._context.turn - 1,
            input_tokens=tuple(filtered),
            walk_surface=walk_surface,
            articulation_surface=articulation.surface,
            dialogue_role=str(dialogue_role),
            identity_score=identity_score,
            cycle_cost_total=cycle_cost.total,
            vault_hits=vault_hits,
            versor_condition=versor_condition(result.final_state.F),
            flagged=flagged,
        )
        self.turn_log.append(turn_event)

        return ChatResponse(
            surface=surface,
            proposition=proposition,
            articulation=articulation,
            dialogue_role=dialogue_role,
            versor_condition=versor_condition(result.final_state.F),
            output_language=self.config.output_language,
            frame_pack=self.config.frame_pack,
            walk_surface=walk_surface,
            salience_top_k=result.salience_top_k,
            candidates_used=result.candidates_used,
            identity_score=identity_score,
            character_profile=self.character_profile,
            flagged=flagged,
        )

    def respond(self, text: str, max_tokens: int | None = None) -> str:
        try:
            return self.chat(text, max_tokens=max_tokens).surface
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
        alignment_threshold=0.75,
    )
