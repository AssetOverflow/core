"""ManifoldState construction, validation, and immutability tests."""

import numpy as np
import pytest

from algebra.rotor import make_rotor_from_angle
from field.state import ManifoldState


def _make_versors(n: int) -> np.ndarray:
    return np.stack(
        [make_rotor_from_angle(0.1 * (i + 1)).astype(np.float32) for i in range(n)],
        axis=0,
    )


def _triangle_edges() -> np.ndarray:
    return np.array([[0, 1], [1, 2], [0, 2]], dtype=np.int32)


class TestConstruction:
    def test_valid_construction(self) -> None:
        fields = _make_versors(3)
        edges = _triangle_edges()
        ms = ManifoldState(fields=fields, edges=edges)
        assert ms.fields.shape == (3, 32)
        assert ms.edges.shape == (3, 2)
        assert ms.step == 0

    def test_fields_are_copied(self) -> None:
        fields = _make_versors(2)
        edges = np.array([[0, 1]], dtype=np.int32)
        ms = ManifoldState(fields=fields, edges=edges)
        assert ms.fields is not fields

    def test_bad_field_shape_raises(self) -> None:
        with pytest.raises(ValueError, match="shape"):
            ManifoldState(
                fields=np.ones((3, 16), dtype=np.float32),
                edges=_triangle_edges(),
            )

    def test_bad_edge_shape_raises(self) -> None:
        with pytest.raises(ValueError, match="shape"):
            ManifoldState(
                fields=_make_versors(3),
                edges=np.array([[0, 1, 2]], dtype=np.int32),
            )

    def test_edge_out_of_bounds_raises(self) -> None:
        with pytest.raises(ValueError, match="indices"):
            ManifoldState(
                fields=_make_versors(2),
                edges=np.array([[0, 5]], dtype=np.int32),
            )

    def test_versor_condition_enforced(self) -> None:
        bad_fields = np.random.randn(2, 32).astype(np.float32)
        with pytest.raises(ValueError, match="versor_condition"):
            ManifoldState(
                fields=bad_fields,
                edges=np.array([[0, 1]], dtype=np.int32),
            )


class TestMutation:
    def test_frozen(self) -> None:
        ms = ManifoldState(fields=_make_versors(2), edges=np.array([[0, 1]], dtype=np.int32))
        with pytest.raises(AttributeError):
            ms.step = 5  # type: ignore[misc]

    def test_with_fields_returns_new(self) -> None:
        ms = ManifoldState(fields=_make_versors(2), edges=np.array([[0, 1]], dtype=np.int32))
        new_fields = _make_versors(2)
        ms2 = ms.with_fields(new_fields)
        assert ms2 is not ms
        assert ms.step == ms2.step

    def test_advance_increments_step(self) -> None:
        ms = ManifoldState(fields=_make_versors(2), edges=np.array([[0, 1]], dtype=np.int32))
        ms2 = ms.advance()
        assert ms2.step == ms.step + 1
        assert np.array_equal(ms2.fields, ms.fields)
