import numpy as np

from algebra.versor import unitize_versor, versor_condition
from algebra.holonomy import holonomy_encode, holonomy_similarity


def _unit_reflector(seed: int) -> np.ndarray:
    """Construct a true grade-1 versor/reflector in Cl(4,1)."""
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(5).astype(np.float32)
    if abs(float(np.dot(vec[:4], vec[:4]) - vec[4] * vec[4])) < 1e-4:
        vec[0] += 1.0
    mv = np.zeros(32, dtype=np.float32)
    mv[1:6] = vec
    return unitize_versor(mv)


def _random_versors(n: int, seed: int = 0) -> list:
    return [_unit_reflector(seed + i) for i in range(n)]


def test_holonomy_is_versor():
    words = _random_versors(5)
    H = holonomy_encode(words)
    assert versor_condition(H) < 1e-5


def test_holonomy_bounded_short():
    words = _random_versors(1)
    H = holonomy_encode(words)
    norm = float(np.linalg.norm(H))
    assert 0.1 < norm < 10.0, f"Holonomy norm out of range: {norm}"


def test_holonomy_bounded_long():
    words = _random_versors(100)
    H = holonomy_encode(words)
    norm = float(np.linalg.norm(H))
    assert np.isfinite(norm)
    assert 0.1 < norm < 10.0, f"Long holonomy norm out of range: {norm}"


def test_holonomy_distinguishes_prompts():
    words_a = _random_versors(5, seed=0)
    words_b = _random_versors(5, seed=99)
    Ha = holonomy_encode(words_a)
    Hb = holonomy_encode(words_b)
    sim = abs(holonomy_similarity(Ha, Hb))
    assert sim < 0.99, f"Two random prompts should be geometrically distinct, got sim={sim}"


def test_holonomy_single_word():
    words = _random_versors(1)
    H = holonomy_encode(words)
    assert versor_condition(H) < 1e-5
