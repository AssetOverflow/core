"""
Generation loop — token streaming from the versor manifold.

Every token:  nearest word to current F via CGA inner product.
Every step:   F <- versor_apply(V, F) where V = word_transition_rotor(A, B).

Architectural boundaries enforced here:
  - VocabManifold owns manifold points only (get_versor_at, nearest).
  - algebra.rotor.word_transition_rotor constructs the transition operator.
  - Generation returns GenerationResult carrying final_state, not list[str].
  - No normalization inside this loop. FieldState invariant is maintained
    structurally by versor_apply() and the closed algebra.

No confidence gates. No IDK fallback. No attractor clamping.
F is always on the manifold. nearest() is always exact.
"""

from __future__ import annotations
from field.state import FieldState
from field.propagate import propagate_step
from algebra.rotor import word_transition_rotor
from generate.result import GenerationResult


def generate(
    state: FieldState,
    vocab,
    persona,
    max_tokens: int = 128,
    record_trajectory: bool = False,
) -> GenerationResult:
    """
    Generate a token sequence from an initial FieldState.

    Loop:
    1. Apply persona motor to current field
    2. Find nearest vocab node via CGA inner product
    3. Emit token
    4. Build transition rotor: V = word_transition_rotor(A, B)
       where A = versor at current node, B = versor at nearest node
    5. Propagate: F <- versor_apply(V, F)
    6. Advance node pointer

    Returns:
        GenerationResult with tokens, final_state, and optional trajectory.
    """
    tokens = []
    trajectory = [] if record_trajectory else None
    current = state

    for _ in range(max_tokens):
        F_voiced = persona.apply(current.F)
        word, word_idx = vocab.nearest(F_voiced)
        tokens.append(word)

        if record_trajectory:
            trajectory.append(current)

        A = vocab.get_versor_at(current.node)
        B = vocab.get_versor_at(word_idx)
        V = word_transition_rotor(A, B)

        current = propagate_step(current, V)
        current = FieldState(F=current.F, node=word_idx, step=current.step)

    return GenerationResult(
        tokens=tokens,
        final_state=current,
        trajectory=trajectory,
    )


async def agenerate(
    state: FieldState,
    vocab,
    persona,
    max_tokens: int = 128,
):
    """
    Async streaming version — yields one token at a time.

    The caller must await the generator and can retrieve final_state
    by calling .athrow() or by consuming the StopAsyncIteration value.
    For the final state, prefer the synchronous generate() path or
    wrap in an async collector that reads the return value.

    Yields: str (one token per iteration)
    """
    current = state
    for _ in range(max_tokens):
        F_voiced = persona.apply(current.F)
        word, word_idx = vocab.nearest(F_voiced)
        yield word

        A = vocab.get_versor_at(current.node)
        B = vocab.get_versor_at(word_idx)
        V = word_transition_rotor(A, B)

        current = propagate_step(current, V)
        current = FieldState(F=current.F, node=word_idx, step=current.step)
