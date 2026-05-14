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

import numpy as np

from field.state import FieldState
from field.propagate import propagate_step
from algebra.rotor import word_transition_rotor
from generate.attention import AttentionOperator
from generate.result import GenerationResult
from generate.salience import SalienceOperator

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
    candidate_indices: np.ndarray | None = None,
) -> tuple[str, int]:
    """
    Select the nearest vocabulary point while avoiding short loops.

    Allowing the current node to win makes V = transition(A, A), which is an
    identity-like transition and can stall generation forever on one token.
    Recent-node exclusion reduces two- and three-token attractor cycles.
    Stop-node exclusion keeps function-word wells from dominating when more
    informative neighbors are available.

    If attention/language filtering leaves only the current node available,
    the final fallback deliberately permits that singleton candidate instead
    of crashing. That keeps inhibition fail-closed to the attended region.
    """
    if len(vocab) <= 1:
        return vocab.nearest(F_voiced, candidate_indices=candidate_indices)

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
            return _nearest_with_optional_candidates(
                vocab,
                F_voiced,
                current_node,
                extra,
                candidate_indices,
            )
        except ValueError:
            continue
    return _nearest_with_optional_candidates(
        vocab,
        F_voiced,
        -1,
        set(),
        candidate_indices,
    )


def _nearest_with_optional_candidates(
    vocab,
    F_voiced,
    current_node: int,
    exclude_indices: set[int],
    candidate_indices: np.ndarray | None,
) -> tuple[str, int]:
    try:
        return vocab.nearest(
            F_voiced,
            exclude_idx=current_node,
            exclude_indices=exclude_indices,
            candidate_indices=candidate_indices,
        )
    except TypeError:
        if candidate_indices is not None:
            raise
        return vocab.nearest(
            F_voiced,
            exclude_idx=current_node,
            exclude_indices=exclude_indices,
        )


def _voiced_state(state: FieldState, persona) -> FieldState:
    """Compose the session persona motor into the live field path."""
    return FieldState(
        F=persona.apply(state.F),
        node=state.node,
        step=state.step,
        holonomy=state.holonomy,
        energy=state.energy,
        valence=state.valence,
    )


def _recall_state(state: FieldState, vault, top_k: int) -> FieldState:
    """
    Feed exact vault recall back into the field as sequential operators.

    Recall returns stored versors ranked by the vault's exact metric. Each hit
    is treated as an additional operator in the propagation path.
    """
    if vault is None or top_k <= 0:
        return state

    current = state
    for hit in vault.recall(current.F, top_k=top_k):
        recalled_F = hit["versor"]
        V = word_transition_rotor(current.F, recalled_F)
        current = propagate_step(current, V)
        current = FieldState(
            F=current.F,
            node=state.node,
            step=current.step,
            holonomy=state.holonomy,
            energy=state.energy,
            valence=state.valence,
        )
    return current


def _candidate_indices_for_language(vocab, output_lang: str | None) -> np.ndarray | None:
    if output_lang is None:
        return None
    indices_for_language = getattr(vocab, "indices_for_language", None)
    if indices_for_language is None:
        return None
    indices = indices_for_language(output_lang)
    if len(indices) == 0:
        raise ValueError(f"No generation candidates for output language {output_lang!r}.")
    return indices


def _intersect_candidates(a: np.ndarray | None, b: np.ndarray | None) -> np.ndarray | None:
    if a is None:
        return b
    if b is None:
        return a
    if len(a) == 0 or len(b) == 0:
        return np.asarray([], dtype=np.int64)
    b_set = {int(idx) for idx in b}
    return np.asarray([int(idx) for idx in a if int(idx) in b_set], dtype=np.int64)


def _attention_candidates(
    state: FieldState,
    vocab,
    use_salience: bool,
    salience_top_k: int,
    inhibition_threshold: float,
) -> tuple[np.ndarray | None, int | None, int | None]:
    if not use_salience:
        return None, None, None
    salience = SalienceOperator().compute(state, vocab, top_k=salience_top_k)
    attention = AttentionOperator(inhibition_threshold).plan(salience, vocab)
    return attention.allowed_indices, salience.budget, len(attention.allowed_indices)


def generate(
    state: FieldState,
    vocab,
    persona,
    max_tokens: int = 128,
    record_trajectory: bool = False,
    vault=None,
    recall_top_k: int = 3,
    output_lang: str | None = None,
    allow_cross_language_generation: bool = True,
    use_salience: bool = False,
    salience_top_k: int = 16,
    inhibition_threshold: float = 0.3,
) -> GenerationResult:
    """
    Generate a token sequence from an initial FieldState.

    Loop:
    1. Compose the persistent persona motor into the current field
    2. Propagate exact vault recall hits into the current field
    3. Find nearest non-current vocab node via CGA inner product
    4. Emit token
    5. Build transition rotor: V = word_transition_rotor(A, B)
       where A = versor at current node, B = versor at nearest node
    6. Propagate: F <- versor_apply(V, F)
    7. Advance node pointer

    Returns:
        GenerationResult with tokens, final_state, optional trajectory,
        and salience telemetry when attention is enabled.
    """
    tokens = []
    trajectory = [] if record_trajectory else None
    current = state
    recent_nodes = deque([state.node], maxlen=_RECENT_WINDOW)
    language_candidates = None if allow_cross_language_generation else _candidate_indices_for_language(vocab, output_lang)
    salience_candidates, salience_budget, candidates_used = _attention_candidates(
        state,
        vocab,
        use_salience=use_salience,
        salience_top_k=salience_top_k,
        inhibition_threshold=inhibition_threshold,
    )
    candidate_indices = _intersect_candidates(language_candidates, salience_candidates)
    if candidate_indices is not None and len(candidate_indices) == 0:
        candidate_indices = salience_candidates if salience_candidates is not None else language_candidates
        candidates_used = None if candidate_indices is None else len(candidate_indices)

    stop_nodes = frozenset(
        vocab.index_of(token)
        for token in _STOP_TOKENS
        if token in {vocab.get_word_at(i) for i in range(len(vocab))}
    )

    token_budget = min(max_tokens, int(candidates_used)) if candidates_used is not None else max_tokens
    for _ in range(token_budget):
        current = _recall_state(_voiced_state(current, persona), vault, recall_top_k)
        word, word_idx = _nearest_next(
            vocab,
            current.F,
            current.node,
            recent_nodes=tuple(recent_nodes),
            stop_nodes=stop_nodes,
            candidate_indices=candidate_indices,
        )
        tokens.append(_articulate(vocab, word))

        if record_trajectory:
            trajectory.append(current)

        A = vocab.get_versor_at(current.node)
        B = vocab.get_versor_at(word_idx)
        V = word_transition_rotor(A, B)

        current = propagate_step(current, V)
        current = FieldState(
            F=current.F,
            node=word_idx,
            step=current.step,
            holonomy=current.holonomy,
            energy=current.energy,
            valence=current.valence,
        )
        recent_nodes.append(word_idx)

    return GenerationResult(
        tokens=tokens,
        final_state=current,
        trajectory=trajectory,
        salience_top_k=salience_budget,
        candidates_used=candidates_used,
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
        current = _voiced_state(current, persona)
        word, word_idx = _nearest_next(
            vocab,
            current.F,
            current.node,
            recent_nodes=tuple(recent_nodes),
            stop_nodes=stop_nodes,
        )
        yield _articulate(vocab, word)

        A = vocab.get_versor_at(current.node)
        B = vocab.get_versor_at(word_idx)
        V = word_transition_rotor(A, B)

        current = propagate_step(current, V)
        current = FieldState(
            F=current.F,
            node=word_idx,
            step=current.step,
            holonomy=current.holonomy,
            energy=current.energy,
            valence=current.valence,
        )
        recent_nodes.append(word_idx)
