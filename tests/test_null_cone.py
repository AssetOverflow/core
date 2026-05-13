import numpy as np
import pytest

from algebra.cga import embed_point, is_null, null_project, cga_inner


def test_embedded_point_is_null():
    x = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    X = embed_point(x)
    assert is_null(X), f"Embedded point not null: cga_inner(X,X)={cga_inner(X,X):.2e}"


def test_origin_is_null():
    X = embed_point(np.zeros(3, dtype=np.float32))
    assert is_null(X)


def test_null_project_restores_null():
    x = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    X = embed_point(x)
    rng = np.random.default_rng(0)
    X_drifted = X + rng.standard_normal(32).astype(np.float32) * 0.01
    X_fixed = null_project(X_drifted)
    assert is_null(X_fixed), f"null_project failed: {cga_inner(X_fixed, X_fixed):.2e}"


def test_cga_inner_symmetry():
    X = embed_point(np.array([1.0, 0.0, 0.0]))
    Y = embed_point(np.array([0.0, 1.0, 0.0]))
    assert abs(cga_inner(X, Y) - cga_inner(Y, X)) < 1e-6


def test_cga_inner_distance_identity():
    """cga_inner(X, Y) = -d^2 / 2 for unit-distance points."""
    X = embed_point(np.array([0.0, 0.0, 0.0]))
    Y = embed_point(np.array([1.0, 0.0, 0.0]))
    inner = cga_inner(X, Y)
    # d=1, so expected = -0.5
    assert abs(inner - (-0.5)) < 1e-5, f"Expected -0.5, got {inner}"
