from __future__ import annotations

from language_packs import OOVPolicy, load_pack, load_pack_entries
from persona.motor import PersonaMotor
from field.state import FieldState
from session.context import SessionContext


class ChatRuntime:
    def __init__(self, pack_id: str = "en_minimal_v1") -> None:
        manifest, manifold = load_pack(pack_id)
        self._manifest = manifest
        self._context = SessionContext(manifold, persona=PersonaMotor.identity())
        self._index_by_surface = {w: i for i, w in enumerate(self._context.vocab._words)}
        self._pos_by_surface = {
            e.surface: (e.pos or e.part_of_speech or "X") for e in load_pack_entries(pack_id)
        }

    def _apply_oov_policy(self, tokens: list[str]) -> list[str]:
        kept: list[str] = []
        for token in tokens:
            try:
                self._context.vocab.get_versor(token)
                kept.append(token)
            except KeyError:
                if self._manifest.oov_policy is OOVPolicy.FAIL_CLOSED:
                    raise
                if self._manifest.oov_policy is OOVPolicy.PROPOSE_VOCAB_EXPANSION:
                    raise KeyError(f"OOV token requires vocab proposal: {token}")
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

    def respond(self, text: str, max_tokens: int = 32) -> str:
        tokens = [t.strip() for t in text.split() if t.strip()]
        filtered = self._apply_oov_policy(tokens)
        if not filtered:
            return ""
        self._context.ingest(filtered)
        node_idx = self._index_by_surface.get(filtered[0], 0)
        self._context.state = FieldState(
            F=self._context.state.F,
            node=node_idx,
            step=self._context.state.step,
            holonomy=self._context.state.holonomy,
        )
        result = self._context.respond(max_tokens=max_tokens)
        guarded = self._syntactic_guard(result.tokens)
        return " ".join(guarded)
