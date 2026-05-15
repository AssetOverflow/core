"""GraphDiffusionOperator tests — convergence, closure, self-adjointness."""

import numpy as np
import pytest

from algebra.backend import versor_condition
from algebra.rotor import make_rotor_from_angle
from field.operators import GraphDiffusionOperator
from field.state import ManifoldState


def _make_versors(n: int) -> np.ndarray:
    return np.stack(
        [make_rotor_from_angle(0.1 * (i + 1)).astype(np.float32) for i in range(n)],
        axis=0,
    )


class TestGraphDiffusion:
    def test_self_adjoint(self) -> None:
        op = GraphDiffusionOperator(damping=0.5)
        assert op.adjoint() is op

    def test_invalid_damping(self) -> None:
        with pytest.raises(ValueError):
            GraphDiffusionOperator(damping=0.0)
        with pytest.raises(ValueError):
            GraphDiffusionOperator(damping=1.5)

    def test_forward_returns_manifold_and_delta(self) -> None:
        fields = _make_versors(2)
        edges = np.array([[0, 1]], dtype=np.int32)
        state = ManifoldState(fields=fields, edges=edges)
        op = GraphDiffusionOperator(damping=0.5)
        new_state, delta = op.forward(state)
        assert isinstance(new_state, ManifoldState)
        assert isinstance(delta, float)
        assert new_state.step == 1

    def test_versor_condition_preserved(self) -> None:
        fields = _make_versors(3)
        edges = np.array([[0, 1], [1, 2], [0, 2]], dtype=np.int32)
        state = ManifoldState(fields=fields, edges=edges)
        op = GraphDiffusionOperator(damping=0.5)
        new_state, _ = op.forward(state)
        for i in range(new_state.fields.shape[0]):
            assert versor_condition(new_state.fields[i]) < 1e-6

    def test_convergence_delta_nonnegative(self) -> None:
        fields = _make_versors(3)
        edges = np.array([[0, 1], [1, 2], [0, 2]], dtype=np.int32)
        state = ManifoldState(fields=fields, edges=edges)
        op = GraphDiffusionOperator(damping=0.5)
        for _ in range(10):
            state, delta = op.forward(state)
            assert delta >= 0.0

    def test_identical_nodes_small_delta(self) -> None:
        v = make_rotor_from_angle(0.3).astype(np.float32)
        fields = np.stack([v, v], axis=0)
        edges = np.array([[0, 1]], dtype=np.int32)
        state = ManifoldState(fields=fields, edges=edges)
        op = GraphDiffusionOperator(damping=0.5)
        _, delta = op.forward(state)
        assert delta < 0.5
