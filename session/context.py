"""
SessionContext — binds field, vault, vocab, and persona for one session.

One session = one field trajectory on the manifold.
The vault accumulates versors across turns.
The persona motor is fixed per session (or composable across sessions).
"""

from field.state import FieldState
from vault.store import VaultStore
from persona.motor import PersonaMotor
from ingest.gate import inject
from generate.stream import generate, agenerate


class SessionContext:
    def __init__(self, vocab, persona=None, vault=None):
        self.vocab = vocab
        self.persona = persona or PersonaMotor.identity()
        self.vault = vault or VaultStore()
        self.state: FieldState = None
        self.turn: int = 0

    def ingest(self, tokens: list) -> FieldState:
        """Inject a prompt. Sets self.state. Stores field in vault."""
        self.state = inject(tokens, self.vocab)
        self.vault.store(self.state.F, {"turn": self.turn, "role": "user"})
        return self.state

    def respond(self, max_tokens: int = 128) -> list:
        """Generate a response from current state. Stores result in vault."""
        assert self.state is not None, "Call ingest() before respond()."
        tokens = generate(self.state, self.vocab, self.persona, max_tokens)
        self.vault.store(self.state.F, {"turn": self.turn, "role": "assistant"})
        self.turn += 1
        return tokens

    async def arespond(self, max_tokens: int = 128):
        """Async streaming response."""
        assert self.state is not None, "Call ingest() before arespond()."
        async for token in agenerate(self.state, self.vocab, self.persona, max_tokens):
            yield token
        self.vault.store(self.state.F, {"turn": self.turn, "role": "assistant"})
        self.turn += 1

    def recall(self, query_tokens: list, top_k: int = 5) -> list:
        """Recall relevant past versors for a query."""
        query_state = inject(query_tokens, self.vocab)
        return self.vault.recall(query_state.F, top_k=top_k)
