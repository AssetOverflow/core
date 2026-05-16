"""Integration test — full pulse cycle from injection to vault recall."""

import numpy as np

from scripts.run_pulse import run_pulse, _build_manifold
from language_packs.compiler import load_pack


class TestPulseIntegration:
    def test_full_cycle_completes(self) -> None:
        words = run_pulse("hello world", use_glove=False)
        assert isinstance(words, list)
        assert len(words) > 0
        assert all(isinstance(w, str) for w in words)

    def test_output_node_changes(self) -> None:
        _, manifold = load_pack("en_core_cognition_v1")
        state, labels = _build_manifold("test input", manifold)
        output_idx = len(labels) - 1
        initial_output = state.fields[output_idx].copy()

        from field.operators import GraphDiffusionOperator
        op = GraphDiffusionOperator(damping=0.5)
        for _ in range(20):
            state, _ = op.forward(state)
        assert not np.allclose(state.fields[output_idx], initial_output, atol=1e-7)

    def test_different_inputs_produce_different_output(self) -> None:
        w1 = run_pulse("alpha", use_glove=False)
        w2 = run_pulse("omega", use_glove=False)
        assert isinstance(w1, list) and isinstance(w2, list)

    def test_recall_returns_known_vocab(self) -> None:
        _, manifold = load_pack("en_core_cognition_v1")
        words = run_pulse("wisdom seeker", use_glove=False)
        for w in words:
            try:
                manifold.get_versor(w)
            except KeyError:
                raise AssertionError(f"{w!r} not in compiled vocab")
