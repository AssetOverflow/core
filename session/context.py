"""
SessionContext — binds field, vault, vocab, persona, referents, and session
graph for one session.

One session = one field trajectory on the manifold.
The vault accumulates versors across turns.
The persona motor is fixed per session (or composable across sessions).
The referent registry resolves pronouns before field injection.
The session graph records every turn as a TurnNode with backward edges.

Generation returns GenerationResult so the evolved field state is preserved.
The assistant vault entry stores the generated final_state, not the prompt
field that entered the turn.
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
        # Replaced flat list with SessionGraph; kept attribute name for
        # back-compat with any code that reads .dialogue_history as a list.
        self.graph: SessionGraph = SessionGraph()
        self.referents: ReferentRegistry = ReferentRegistry()
        self.running_dialogue_blade: np.ndarray | None = None
        self._last_response_tokens: tuple[str, ...] | None = None
        self._anchor_field: np.ndarray | None = None
        # Preserve the old list interface via a property so existing callers
        # that iterate dialogue_history don't break.
        self._dialogue_history_compat: list[DialogueTurn] = []

    # ------------------------------------------------------------------
    # Back-compat property so old callers still work
    # ------------------------------------------------------------------

    @property
    def dialogue_history(self) -> list[DialogueTurn]:
        return self._dialogue_history_compat

    def ingest(self, tokens: list) -> FieldState:
        """Inject a prompt into the running field.

        Pronouns in *tokens* are resolved to their registered referent
        surface forms before field injection so the field operates on the
        correct versor rather than a bare pronoun node.
        Stores the user field in vault.
        """
        # Resolve anaphoric pronouns via the referent registry
        resolved_tokens = self.referents.resolve(tokens)

        injected = inject(resolved_tokens, self.vocab)
        # node index from the original first token (pre-resolution surface)
        anchor_token = resolved_tokens[0] if resolved_tokens else (tokens[0] if tokens else "")
        try:
            node_idx = self.vocab.index_of(anchor_token)
        except (KeyError, IndexError):
            node_idx = self.vocab.index_of(tokens[0]) if tokens else 0

        if self.state is None:
            self.state = FieldState(
                F=injected.F,
                node=node_idx,
                step=injected.step,
                holonomy=injected.holonomy,
                energy=injected.energy,
                valence=injected.valence,
            )
            self._anchor_field = self.state.F.copy()
        else:
            self.state = FieldState(
                F=versor_apply(injected.F, self.state.F),
                node=node_idx,
                step=self.state.step + 1,
                holonomy=injected.holonomy,
                energy=injected.energy,
                valence=injected.valence,
            )
        self.vault.store(self.state.F, {"turn": self.turn, "role": "user"})
        return self.state

    def record_dialogue(self, proposition: Proposition) -> DialogueTurn:
        """
        Store a proposition as geometric dialogue state.

        The transcript surface is deliberately not used as session memory here;
        the retained object is the proposition paired with its relation blade.
        """
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

    def respond(self, max_tokens: int = 128) -> GenerationResult:
        """
        Generate a response from current state and preserve the evolved field.
        After generation, registers the last content token as the active
        neut_sg referent so future pronouns resolve correctly.

        Returns:
            GenerationResult carrying emitted tokens and final_state.
        """
        assert self.state is not None, "Call ingest() before respond()."
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

        # ------------------------------------------------------------------
        # Register the last content token in the output as the active referent
        # so incoming pronouns on the next turn resolve correctly.
        # ------------------------------------------------------------------
        if result.tokens:
            versors: dict[str, np.ndarray] = {}
            for tok in result.tokens:
                try:
                    versors[tok] = self.vocab.get_versor(tok)
                except KeyError:
                    pass
            self.referents.register_from_tokens(
                result.tokens, versors, turn=self.turn
            )

        # ------------------------------------------------------------------
        # Record turn in the session graph
        # ------------------------------------------------------------------
        input_versor = self.state.F  # already set by ingest
        self.state = result.final_state
        self.vault.store(result.final_state.F, {"turn": self.turn, "role": "assistant"})

        # Collect backward edges: turns whose output versor was consumed as a
        # referent during this turn's ingest (registered in referents.history).
        backward_edges = [
            entry.turn
            for entry in self.referents.history()
            if entry.turn < self.turn
        ]
        active_slots = {
            entry.slot: entry.turn
            for entry in self.referents.history()
            if entry.turn <= self.turn
        }
        self.graph.add_turn(
            turn_idx=self.turn,
            input_versor=input_versor,
            output_versor=result.final_state.F,
            tokens_in=tuple(self.state_input_tokens if hasattr(self, "state_input_tokens") else []),
            tokens_out=tuple(result.tokens or []),
            dialogue_role="assert",
            referent_slots=active_slots,
            backward_edges=list(dict.fromkeys(backward_edges)),  # deduplicated
        )

        self.turn += 1
        self._last_response_tokens = result.tokens
        return result

    def _orient_result_to_anchor(self, result: GenerationResult) -> GenerationResult:
        final_state = result.final_state
        coherence_anchor = self._anchor_field if self._anchor_field is not None else self.state.F
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
        """
        Async token-yielding response path.

        The generation pass still returns a GenerationResult internally so
        SessionContext can store the evolved assistant final_state after
        yielding the surface tokens.
        """
        assert self.state is not None, "Call ingest() before arespond()."
        result = self._orient_result_to_anchor(
            generate(self.state, self.vocab, self.persona, max_tokens, vault=self.vault)
        )
        for token in result.tokens:
            yield token

        if result.tokens:
            versors: dict[str, np.ndarray] = {}
            for tok in result.tokens:
                try:
                    versors[tok] = self.vocab.get_versor(tok)
                except KeyError:
                    pass
            self.referents.register_from_tokens(
                result.tokens, versors, turn=self.turn
            )

        self.state = result.final_state
        self.vault.store(result.final_state.F, {"turn": self.turn, "role": "assistant"})
        self.graph.add_turn(
            turn_idx=self.turn,
            input_versor=self.state.F,
            output_versor=result.final_state.F,
            tokens_in=(),
            tokens_out=tuple(result.tokens or []),
            dialogue_role="assert",
        )
        self.turn += 1

    def recall(self, query_tokens: list, top_k: int = 5) -> list:
        """Recall relevant past versors for a query."""
        query_state = inject(query_tokens, self.vocab)
        return self.vault.recall(query_state.F, top_k=top_k)
