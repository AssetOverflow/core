"""
Generation loop — token streaming from the versor manifold.

Every token:  nearest word to current F via CGA inner product.
Every step:   F <- versor_apply(V, F) where V is the edge rotor.

No confidence gates. No IDK fallback. No attractor clamping.
F is always on the manifold. nearest() is always exact.
"""

import numpy as np
from field.state import FieldState
from field.propagate import propagate_step


def generate(state: FieldState, vocab, persona, max_tokens: int = 128) -> list:
    """
    Generate a token sequence from an initial FieldState.

    Loop:
    1. Apply persona motor to current field
    2. Find nearest vocab node via CGA inner product
    3. Emit token
    4. Get edge rotor from current node to nearest node
    5. Propagate: F <- versor_apply(V, F)
    6. Advance node pointer
    """
    tokens = []
    current = state

    for _ in range(max_tokens):
        F_voiced = persona.apply(current.F)
        word, word_idx = vocab.nearest(F_voiced)
        tokens.append(word)
        V = vocab.edge_rotor(current.node, word_idx)
        current = propagate_step(current, V)
        current = FieldState(F=current.F, node=word_idx, step=current.step)

    return tokens


async def agenerate(state: FieldState, vocab, persona, max_tokens: int = 128):
    """Async streaming version — yields one token at a time."""
    current = state
    for _ in range(max_tokens):
        F_voiced = persona.apply(current.F)
        word, word_idx = vocab.nearest(F_voiced)
        yield word
        V = vocab.edge_rotor(current.node, word_idx)
        current = propagate_step(current, V)
        current = FieldState(F=current.F, node=word_idx, step=current.step)
