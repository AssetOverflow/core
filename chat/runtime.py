from __future__ import annotations

from dataclasses import dataclass
import re
from collections.abc import Sequence

import numpy as np

from algebra.versor import versor_condition
from generate.dialogue import DialogueRole, classify_dialogue_blade, propose_dialogue
from generate.proposition import FrameRegistry, Proposition, propose
from generate.stream import generate
from language_packs import OOVPolicy, load_mounted_packs, load_pack, load_pack_entries
from persona.motor import PersonaMotor
from session.context import SessionContext

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_DEFAULT_PACKS = ("en_minimal_v1", "he_logos_micro_v1", "grc_logos_micro_v1")
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
    dialogue_role: DialogueRole
    versor_condition: float


class ChatRuntime:
    def __init__(
        self,
        pack_id: str | Sequence[str] = _DEFAULT_PACKS,
        *,
        frame_pack: str | None = None,
    ) -> None:
        pack_ids = (pack_id,) if isinstance(pack_id, str) else tuple(pack_id)
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
        self._context = SessionContext(manifold, persona=PersonaMotor.identity())
        self._frame_registry = FrameRegistry.from_pack(
            frame_pack or self._default_frame_pack(pack_ids),
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

    @staticmethod
    def _default_frame_pack(pack_ids: tuple[str, ...]) -> str:
        if any(pack_id.startswith("grc_") for pack_id in pack_ids):
            return "grc"
        if any(pack_id.startswith("he_") for pack_id in pack_ids):
            return "he"
        return "en"

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

    def chat(self, text: str, max_tokens: int = 32) -> ChatResponse:
        tokens = self._tokenize(text)
        filtered = self._apply_oov_policy(tokens)
        if not filtered:
            raise ValueError("ChatRuntime.chat() received no in-vocabulary tokens.")

        field_state = self._context.ingest(filtered)
        reference_blade = self._dialogue_reference()
        base_proposition = propose(field_state, None, self._context.vocab, self._frame_registry)
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
        )
        self._context.record_dialogue(proposition)

        result = generate(
            field_state,
            self._context.vocab,
            self._context.persona,
            max_tokens=max_tokens,
            vault=self._context.vault,
        )
        self._context.state = result.final_state
        self._context.vault.store(
            result.final_state.F,
            {"turn": self._context.turn, "role": "assistant"},
        )
        self._context.turn += 1
        guarded = self._syntactic_guard(result.tokens)
        surface = " ".join(guarded)
        return ChatResponse(
            surface=surface,
            proposition=proposition,
            dialogue_role=dialogue_role,
            versor_condition=versor_condition(result.final_state.F),
        )

    def respond(self, text: str, max_tokens: int = 32) -> str:
        try:
            return self.chat(text, max_tokens=max_tokens).surface
        except ValueError:
            return ""
