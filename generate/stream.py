"""
Generation loop — token streaming from the versor manifold.

Every token:  nearest non-current word to current F via CGA inner product.
Every step:   F <- versor_apply(V, F) where V = word_transition_rotor(A, B).

Architectural boundaries enforced here:
  - VocabManifold owns manifold points only (get_versor_at, nearest).
  - algebra.rotor.word_transition_rotor constructs the transition operator.
  - Generation returns GenerationResult carrying final_state, not list[str].
  - No normalization inside this loop. FieldState invariant is maintained
    structurally by versor_apply() and the closed algebra.

No confidence gates. No IDK fallback. No attractor clamping.
F is always on the manifold. nearest() is exact.
"""

from __future__ import annotations
from collections import deque

from field.state import FieldState
from field.propagate import propagate_step
from algebra.rotor import word_transition_rotor
from generate.result import GenerationResult

_RECENT_WINDOW = 3
_STOP_TOKENS = frozenset({"it", "to", "word"})


def _articulate(vocab, word: str) -> str:
    """
    Recover the emitted surface through MorphologyEntry when available.

    The manifold walk selects a vocabulary point. Articulation then returns
    the structured surface carried by that point, preserving script and
    inflection without introducing a corrective pass.
    """
    morphology_for_word = getattr(vocab, "morphology_for_word", None)
    if morphology_for_word is None:
        return word
    morphology = morphology_for_word(word)
    return morphology.surface if morphology is not None else word


def _nearest_next(
    vocab,
    F_voiced,
    current_node: int,
    recent_nodes: tuple[int, ...] = (),
    stop_nodes: frozenset[int] = frozenset(),
) -> tuple[str, int]:
    """
    Select the nearest vocabulary point while avoiding short loops.

    Allowing the current node to win makes V = transition(A, A), which is an
    identity-like transition and can stall generation forever on one token.
    Recent-node exclusion reduces two- and three-token attractor cycles.
    Stop-node exclusion keeps function-word wells from dominating when more
    informative neighbors are available.
    """
    if len(vocab) <= 1:
        return vocab.nearest(F_voiced)

    recent = set(recent_nodes)
    stop = set(stop_nodes)
    fallback_orders = (
        recent | stop,
        stop,
        recent,
        set(),
    )
    for extra in fallback_orders:
        try:
            return vocab.nearest(F_voiced, exclude_idx=current_node, exclude_indices=extra)
        except ValueError:
            continue
    return vocab.nearest(F_voiced, exclude_idx=current_node)


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
    2. Find nearest non-current vocab node via CGA inner product
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
    recent_nodes = deque([state.node], maxlen=_RECENT_WINDOW)
    stop_nodes = frozenset(
        vocab.index_of(token)
        for token in _STOP_TOKENS
        if token in {vocab.get_word_at(i) for i in range(len(vocab))}
    )

    for _ in range(max_tokens):
        F_voiced = persona.apply(current.F)
        word, word_idx = _nearest_next(
            vocab,
            F_voiced,
            current.node,
            recent_nodes=tuple(recent_nodes),
            stop_nodes=stop_nodes,
        )
        tokens.append(_articulate(vocab, word))

        if record_trajectory:
            trajectory.append(current)

        A = vocab.get_versor_at(current.node)
        B = vocab.get_versor_at(word_idx)
        V = word_transition_rotor(A, B)

        current = propagate_step(current, V)
        current = FieldState(F=current.F, node=word_idx, step=current.step, holonomy=current.holonomy)
        recent_nodes.append(word_idx)

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
    recent_nodes = deque([state.node], maxlen=_RECENT_WINDOW)
    stop_nodes = frozenset(
        vocab.index_of(token)
        for token in _STOP_TOKENS
        if token in {vocab.get_word_at(i) for i in range(len(vocab))}
    )
    for _ in range(max_tokens):
        F_voiced = persona.apply(current.F)
        word, word_idx = _nearest_next(
            vocab,
            F_voiced,
            current.node,
            recent_nodes=tuple(recent_nodes),
            stop_nodes=stop_nodes,
        )
        yield _articulate(vocab, word)

        A = vocab.get_versor_at(current.node)
        B = vocab.get_versor_at(word_idx)
        V = word_transition_rotor(A, B)

        current = propagate_step(current, V)
        current = FieldState(F=current.F, node=word_idx, step=current.step, holonomy=current.holonomy)
        recent_nodes.append(word_idx)
