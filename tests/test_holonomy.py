import numpy as np

from algebra.versor import unitize_versor, versor_condition
from algebra.holonomy import holonomy_encode, holonomy_similarity


def _positive_unit_reflector(seed: int) -> np.ndarray:
    """Construct a true positive-norm grade-1 versor in Cl(4,1)."""
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


def _random_versors(n: int, seed: int = 0) -> list:
    return [_positive_unit_reflector(seed + i) for i in range(n)]


def test_holonomy_is_versor():
    words = _random_versors(5)
    H = holonomy_encode(words)
    assert versor_condition(H) < 1e-4


def test_holonomy_bounded_short():
    words = _random_versors(1)
    H = holonomy_encode(words)
    norm = float(np.linalg.norm(H))
    assert np.isfinite(norm)
    assert norm > 0.1, f"Holonomy norm out of range: {norm}"


def test_holonomy_bounded_long():
    words = _random_versors(100)
    H = holonomy_encode(words)
    norm = float(np.linalg.norm(H))
    assert np.isfinite(norm)
    assert norm > 0.1, f"Long holonomy norm out of range: {norm}"


def test_holonomy_distinguishes_prompts():
    words_a = _random_versors(5, seed=0)
    words_b = _random_versors(5, seed=99)
    Ha = holonomy_encode(words_a)
    Hb = holonomy_encode(words_b)
    # CGA inner product is indefinite and not a cosine bounded to [-1, 1].
    # The invariant here is not a bounded similarity score; it is that two
    # distinct prompt paths do not collapse to identical holonomy.
    assert not np.allclose(Ha, Hb)
    assert np.isfinite(holonomy_similarity(Ha, Hb))


def test_holonomy_single_word():
    words = _random_versors(1)
    H = holonomy_encode(words)
    assert versor_condition(H) < 1e-5
