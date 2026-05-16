"""
SessionContext — binds field, vault, vocab, persona, referents, and graph.

The ingest path is split into a non-mutating probe and a committing ingest so
runtime gates can inspect the candidate field before durable vault writes.  All
response paths finalize through one graph/vault/session-state method.
"""

from __future__ import annotations

import numpy as np

from algebra.backend import cga_inner, versor_apply
from algebra.cga import outer_product
from field.state import FieldState
from generate.dialogue import DialogueTurn
from generate.proposition import Proposition
from generate.result import GenerationResult
from generate.stream import generate
from ingest.gate import inject
from persona.motor import PersonaMotor
from session.graph import SessionGraph
from session.referents import ReferentRegistry
from vault.store import VaultStore


class SessionContext:
    def __init__(self, vocab, persona=None, vault=None, vault_reproject_interval: int = 100):
        self.vocab = vocab
        self.persona = persona or PersonaMotor.identity()
        self.vault = vault or VaultStore(reproject_interval=vault_reproject_interval)
        self.state: FieldState | None = None
        self.turn: int = 0
        self.graph: SessionGraph = SessionGraph()
        self.referents: ReferentRegistry = ReferentRegistry()
        self.running_dialogue_blade: np.ndarray | None = None
        self._last_response_tokens: tuple[str, ...] | None = None
        self._anchor_field: np.ndarray | None = None
        self._dialogue_history_compat: list[DialogueTurn] = []
        self._last_input_tokens: tuple[str, ...] = ()
        self._last_resolved_input_tokens: tuple[str, ...] = ()
        self._last_input_versor: np.ndarray | None = None

    @property
    def dialogue_history(self) -> list[DialogueTurn]:
        return self._dialogue_history_compat

    @property
    def last_input_tokens(self) -> tuple[str, ...]:
        return self._last_input_tokens

    @property
    def last_resolved_input_tokens(self) -> tuple[str, ...]:
        return self._last_resolved_input_tokens

    def _field_from_tokens(self, tokens: list[str], *, resolve_referents: bool) -> tuple[FieldState, list[str]]:
        resolved_tokens = self.referents.resolve(tokens) if resolve_referents else list(tokens)
        injected = inject(resolved_tokens, self.vocab)
        anchor_token = resolved_tokens[0] if resolved_tokens else (tokens[0] if tokens else "")
        try:
            node_idx = self.vocab.index_of(anchor_token)
        except (KeyError, IndexError):
            node_idx = self.vocab.index_of(tokens[0]) if tokens else 0

        if self.state is None:
            candidate = FieldState(
                F=injected.F,
                node=node_idx,
                step=injected.step,
                holonomy=injected.holonomy,
                energy=injected.energy,
                valence=injected.valence,
            )
        else:
            candidate = FieldState(
                F=versor_apply(injected.F, self.state.F),
                node=node_idx,
                step=self.state.step + 1,
                holonomy=injected.holonomy,
                energy=injected.energy,
                valence=injected.valence,
            )
        return candidate, resolved_tokens

    def probe_ingest(self, tokens: list[str]) -> FieldState:
        """Build the candidate ingest field without mutating state or vault."""
        snapshot_sources = self.referents.consumed_turns()
        snapshot_slots = self.referents.consumed_slots()
        candidate, _ = self._field_from_tokens(tokens, resolve_referents=True)
        # Restore consumed metadata because probe must not define graph edges.
        self.referents._last_resolved_sources = snapshot_sources  # internal rollback by design
        self.referents._last_resolved_slots = snapshot_slots
        return candidate

    def commit_ingest(self, tokens: list[str]) -> FieldState:
        """Resolve, inject, mutate live state, and store the user field."""
        field_state, resolved_tokens = self._field_from_tokens(tokens, resolve_referents=True)
        self.state = field_state
        if self._anchor_field is None:
            self._anchor_field = field_state.F.copy()
        self._last_input_tokens = tuple(tokens)
        self._last_resolved_input_tokens = tuple(resolved_tokens)
        self._last_input_versor = field_state.F.copy()
        self.vault.store(field_state.F, {"turn": self.turn, "role": "user"})
        return field_state

    def ingest(self, tokens: list[str]) -> FieldState:
        """Backward-compatible committing ingest."""
        return self.commit_ingest(tokens)

    def record_dialogue(self, proposition: Proposition) -> DialogueTurn:
        from generate.dialogue import DialogueTurn as _DT

        blade = proposition.relation
        turn = _DT(proposition=proposition, outer_product_blade=blade)
        self._dialogue_history_compat.append(turn)
        if self.running_dialogue_blade is None:
            self.running_dialogue_blade = blade.copy()
        else:
            self.running_dialogue_blade = outer_product(self.running_dialogue_blade, blade)
        return turn

    @property
    def last_dialogue_blade(self) -> np.ndarray | None:
        if not self._dialogue_history_compat:
            return None
        return self._dialogue_history_compat[-1].outer_product_blade.copy()

    def _register_result_referent(self, result: GenerationResult) -> None:
        if not result.tokens:
            return
        versors: dict[str, np.ndarray] = {}
        for tok in result.tokens:
            try:
                versors[tok] = self.vocab.get_versor(tok)
            except KeyError:
                pass
        self.referents.register_from_tokens(result.tokens, versors, turn=self.turn)

    def finalize_turn(
        self,
        result: GenerationResult,
        *,
        tokens_in: tuple[str, ...] | None = None,
        dialogue_role: str = "assert",
        input_versor: np.ndarray | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Finalize assistant output into referents, graph, vault, and state."""
        if self.state is None and input_versor is None:
            raise AssertionError("Call ingest() before finalize_turn().")

        input_F = (
            np.asarray(input_versor, dtype=np.float32).copy()
            if input_versor is not None
            else (self._last_input_versor.copy() if self._last_input_versor is not None else self.state.F.copy())
        )
        turn_tokens = tuple(tokens_in if tokens_in is not None else self._last_input_tokens)
        backward_edges = self.referents.consumed_turns()
        active_slots = self.referents.active_slots()

        self._register_result_referent(result)
        # Include any newly registered output referent in the turn metadata.
        active_slots = self.referents.active_slots() | active_slots

        self.graph.add_turn(
            turn_idx=self.turn,
            input_versor=input_F,
            output_versor=result.final_state.F,
            tokens_in=turn_tokens,
            tokens_out=tuple(result.tokens or []),
            dialogue_role=dialogue_role,
            referent_slots=active_slots,
            backward_edges=backward_edges,
        )
        self.state = result.final_state
        payload = {"turn": self.turn, "role": "assistant"}
        if metadata:
            payload.update(metadata)
        self.vault.store(result.final_state.F, payload)
        self.turn += 1
        self._last_response_tokens = result.tokens

    def apply_corrected_outputs(self, records) -> None:
        """Synchronize corrected graph records into live session recall surfaces."""
        for record in records:
            self.vault.store(
                record.new_versor,
                {"turn": record.turn_idx, "role": "assistant", "corrected": True},
            )
            self.referents.update_turn_versor(record.turn_idx, record.new_versor)
        if records:
            last = max(records, key=lambda r: r.turn_idx)
            if self.state is not None:
                self.state = FieldState(
                    F=last.new_versor,
                    node=self.state.node,
                    step=self.state.step,
                    holonomy=self.state.holonomy,
                    energy=self.state.energy,
                    valence=self.state.valence,
                )

    def respond(self, max_tokens: int = 128) -> GenerationResult:
        assert self.state is not None, "Call ingest() before respond()."
        input_versor = self._last_input_versor.copy() if self._last_input_versor is not None else self.state.F.copy()
        result = generate(self.state, self.vocab, self.persona, max_tokens, vault=self.vault)
        if self._last_response_tokens is not None and result.tokens == self._last_response_tokens and result.tokens:
            try:
                pivot_node = self.vocab.index_of(result.tokens[0])
            except KeyError:
                pivot_node = self.state.node
            if pivot_node != self.state.node:
                pivot = FieldState(
                    F=self.state.F,
                    node=pivot_node,
                    step=self.state.step,
                    holonomy=self.state.holonomy,
                    energy=self.state.energy,
                    valence=self.state.valence,
                )
                result = generate(pivot, self.vocab, self.persona, max_tokens, vault=self.vault)
        result = self._orient_result_to_anchor(result)
        self.finalize_turn(result, input_versor=input_versor, dialogue_role="assert")
        return result

    def _orient_result_to_anchor(self, result: GenerationResult) -> GenerationResult:
        final_state = result.final_state
        coherence_anchor = self._anchor_field if self._anchor_field is not None else (self.state.F if self.state is not None else None)
        if coherence_anchor is None:
            return result
        cga_score = cga_inner(final_state.F, coherence_anchor)
        euclidean_score = float(np.dot(final_state.F, coherence_anchor))
        if cga_score < 0.0 or euclidean_score < 0.0:
            final_state = FieldState(
                F=-final_state.F,
                node=final_state.node,
                step=final_state.step,
                holonomy=final_state.holonomy,
                energy=final_state.energy,
                valence=final_state.valence,
            )
            return GenerationResult(
                tokens=result.tokens,
                final_state=final_state,
                trajectory=result.trajectory,
                salience_top_k=result.salience_top_k,
                candidates_used=result.candidates_used,
                vault_hits=result.vault_hits,
                identity_score=result.identity_score,
            )
        return result

    async def arespond(self, max_tokens: int = 128):
        assert self.state is not None, "Call ingest() before arespond()."
        input_versor = self._last_input_versor.copy() if self._last_input_versor is not None else self.state.F.copy()
        result = self._orient_result_to_anchor(
            generate(self.state, self.vocab, self.persona, max_tokens, vault=self.vault)
        )
        for token in result.tokens:
            yield token
        self.finalize_turn(result, input_versor=input_versor, dialogue_role="assert")

    def recall(self, query_tokens: list, top_k: int = 5) -> list:
        query_state = inject(query_tokens, self.vocab)
        return self.vault.recall(query_state.F, top_k=top_k)
