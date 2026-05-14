from __future__ import annotations

from dataclasses import dataclass
import re
from collections.abc import Sequence

import numpy as np

from algebra.versor import versor_condition
from core.config import DEFAULT_CONFIG, RuntimeConfig
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
        self._context = SessionContext(
            manifold,
            persona=PersonaMotor.identity(),
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

    def chat(self, text: str, max_tokens: int | None = None) -> ChatResponse:
        tokens = self._tokenize(text)
        filtered = self._apply_oov_policy(tokens)
        if not filtered:
            raise ValueError("ChatRuntime.chat() received no in-vocabulary tokens.")

        field_state = self._context.ingest(filtered)
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
            vault=self._context.vault,
            recall_top_k=3 if self.config.allow_cross_language_recall else 0,
            output_lang=self.config.output_language,
            allow_cross_language_generation=self.config.allow_cross_language_generation,
            use_salience=self.config.use_salience,
            salience_top_k=self.config.salience_top_k,
            inhibition_threshold=self.config.inhibition_threshold,
        )
        self._context.state = result.final_state
        self._context.vault.store(
            result.final_state.F,
            {"turn": self._context.turn, "role": "assistant"},
        )
        self._context.turn += 1
        guarded = self._syntactic_guard(result.tokens)
        walk_surface = " ".join(guarded)
        return ChatResponse(
            surface=articulation.surface,
            proposition=proposition,
            articulation=articulation,
            dialogue_role=dialogue_role,
            versor_condition=versor_condition(result.final_state.F),
            output_language=self.config.output_language,
            frame_pack=self.config.frame_pack,
            walk_surface=walk_surface,
            salience_top_k=result.salience_top_k,
            candidates_used=result.candidates_used,
        )

    def respond(self, text: str, max_tokens: int | None = None) -> str:
        try:
            return self.chat(text, max_tokens=max_tokens).surface
        except ValueError:
            return ""
