"""
SessionContext — binds field, vault, vocab, and persona for one session.

One session = one field trajectory on the manifold.
The vault accumulates versors across turns.
The persona motor is fixed per session (or composable across sessions).

Generation returns GenerationResult so the evolved field state is preserved.
The assistant vault entry stores the generated final_state, not the prompt
field that entered the turn.
"""

from __future__ import annotations

from field.state import FieldState
from vault.store import VaultStore
from persona.motor import PersonaMotor
from ingest.gate import inject
from generate.stream import generate
from generate.result import GenerationResult


class SessionContext:
    def __init__(self, vocab, persona=None, vault=None):
        self.vocab = vocab
        self.persona = persona or PersonaMotor.identity()
        self.vault = vault or VaultStore()
        self.state: FieldState | None = None
        self.turn: int = 0

    def ingest(self, tokens: list) -> FieldState:
        """Inject a prompt. Sets self.state. Stores the user field in vault."""
        state = inject(tokens, self.vocab)
        node_idx = self.vocab.index_of(tokens[0])
        self.state = FieldState(
            F=state.F,
            node=node_idx,
            step=state.step,
            holonomy=state.holonomy,
        )
        self.vault.store(self.state.F, {"turn": self.turn, "role": "user"})
        return self.state

    def respond(self, max_tokens: int = 128) -> GenerationResult:
        """
        Generate a response from current state and preserve the evolved field.

        Returns:
            GenerationResult carrying emitted tokens and final_state.
        """
        assert self.state is not None, "Call ingest() before respond()."
        result = generate(self.state, self.vocab, self.persona, max_tokens)
        self.state = result.final_state
        self.vault.store(result.final_state.F, {"turn": self.turn, "role": "assistant"})
        self.turn += 1
        return result

    async def arespond(self, max_tokens: int = 128):
        """
        Async token-yielding response path.

        The generation pass still returns a GenerationResult internally so
        SessionContext can store the evolved assistant final_state after
        yielding the surface tokens.
        """
        assert self.state is not None, "Call ingest() before arespond()."
        result = generate(self.state, self.vocab, self.persona, max_tokens)
        for token in result.tokens:
            yield token
        self.state = result.final_state
        self.vault.store(result.final_state.F, {"turn": self.turn, "role": "assistant"})
        self.turn += 1

    def recall(self, query_tokens: list, top_k: int = 5) -> list:
        """Recall relevant past versors for a query."""
        query_state = inject(query_tokens, self.vocab)
        return self.vault.recall(query_state.F, top_k=top_k)
