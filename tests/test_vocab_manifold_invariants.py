import numpy as np
import pytest

from vocab.manifold import VocabManifold


def _identity() -> np.ndarray:
    v = np.zeros(32, dtype=np.float32)
    v[0] = 1.0
    return v


def _negative_unit_vector() -> np.ndarray:
    v = np.zeros(32, dtype=np.float32)
    v[5] = 1.0
    return v


def _scalar_norm_one_with_non_scalar_residue() -> np.ndarray:
    v = np.zeros(32, dtype=np.float32)
    v[0] = np.sqrt(0.5)
    v[1] = np.sqrt(0.5)
    return v


def test_manifold_accepts_positive_unit_versor() -> None:
    manifold = VocabManifold()
    manifold.add("one", _identity())
    assert manifold.index_of("one") == 0


def test_manifold_accepts_negative_unit_versor() -> None:
    """Vocabulary manifold entries follow the mathematical ±1 versor contract."""
    manifold = VocabManifold()
    manifold.add("negative", _negative_unit_vector())
    assert manifold.index_of("negative") == 0


def test_manifold_rejects_scalar_norm_shortcut_with_non_scalar_residue() -> None:
    """Scalar grade-norm near one is insufficient when residue is non-scalar."""
    manifold = VocabManifold()

    with pytest.raises(ValueError, match="non_scalar_residue"):
        manifold.add("dirty", _scalar_norm_one_with_non_scalar_residue())


def test_manifold_update_rejects_non_scalar_residue() -> None:
    manifold = VocabManifold()
    manifold.add("clean", _identity())

    with pytest.raises(ValueError, match="replacement versor residual"):
        manifold.update("clean", _scalar_norm_one_with_non_scalar_residue())
