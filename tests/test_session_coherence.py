from __future__ import annotations

import numpy as np

from algebra.backend import cga_inner
from algebra.versor import unitize_versor
from session.context import SessionContext
from vocab.manifold import VocabManifold


def _positive_unit_reflector(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vec4 = rng.standard_normal(4).astype(np.float32)
    norm4 = float(np.linalg.norm(vec4))
    if norm4 < 1e-6:
        vec4[0] = 1.0
        norm4 = 1.0

    vec = np.zeros(5, dtype=np.float32)
    vec[:4] = vec4
    vec[4] = 0.25 * norm4 * np.tanh(float(rng.standard_normal()))

    mv = np.zeros(32, dtype=np.float32)
    mv[1:6] = vec
    return unitize_versor(mv)


def _random_rotor(seed: int) -> np.ndarray:
    """Build a random even-grade versor (rotor) for CGA inner-product comparison.

    Field states are even-grade (grade 0+2+4). Reflectors are grade-1 and
    orthogonal under cga_inner, so we need rotors to get nonzero scores.
    """
    a = _positive_unit_reflector(seed)
    b = _positive_unit_reflector(seed + 10000)
    from algebra.cl41 import geometric_product as gp
    rotor = gp(a, b)
    return unitize_versor(rotor)


def _vocab() -> VocabManifold:
    vocab = VocabManifold()
    vocab.add("logos", _positive_unit_reflector(1))
    vocab.add("arche", _positive_unit_reflector(2))
    vocab.add("pneuma", _positive_unit_reflector(3))
    vocab.add("truth", _positive_unit_reflector(4))
    vocab.add("nous", _positive_unit_reflector(5))
    return vocab


def _farther_unrelated(result_F: np.ndarray, prompt_F: np.ndarray, start_seed: int) -> np.ndarray:
    prompt_score = cga_inner(result_F, prompt_F)
    for seed in range(start_seed, start_seed + 2048):
        candidate = _random_rotor(seed)
        if prompt_score > cga_inner(result_F, candidate):
            return candidate
    raise AssertionError("Could not construct a deterministic farther unrelated versor.")


def test_repeated_prompt_accumulates_field_and_stays_prompt_coherent() -> None:
    session = SessionContext(vocab=_vocab())
    prompt = ["logos", "arche"]

    initial = session.ingest(prompt)
    first = session.respond(max_tokens=4)

    second_prompt_state = session.ingest(prompt)
    assert not np.array_equal(second_prompt_state.F, initial.F)

    second = session.respond(max_tokens=4)

    assert second.tokens != first.tokens
    assert not np.array_equal(second.final_state.F, first.final_state.F)

    for i, result in enumerate((first, second)):
        random_unrelated = _farther_unrelated(result.final_state.F, initial.F, 11 + (i * 64))
        prompt_score = cga_inner(result.final_state.F, initial.F)
        random_score = cga_inner(result.final_state.F, random_unrelated)
        assert prompt_score > random_score
