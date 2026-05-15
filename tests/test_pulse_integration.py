"""Integration test — full pulse cycle from injection to vault recall."""

import numpy as np

from scripts.run_pulse import build_initial_manifold, build_mock_vault, run_pulse
from sensorium.adapters.text import deterministic_hash_versor


class TestPulseIntegration:
    def test_full_cycle_completes(self) -> None:
        word = run_pulse("hello world")
        assert isinstance(word, str)
        assert len(word) > 0

    def test_output_node_changes(self) -> None:
        prompt = deterministic_hash_versor("test input")
        state = build_initial_manifold(prompt)
        initial_output = state.fields[2].copy()

        from field.operators import GraphDiffusionOperator
        op = GraphDiffusionOperator(damping=0.5)
        for _ in range(20):
            state, _ = op.forward(state)
        assert not np.allclose(state.fields[2], initial_output, atol=1e-7)

    def test_vault_recall_returns_known_word(self) -> None:
        word = run_pulse("wisdom seeker")
        vault_versors, vault_words = build_mock_vault()
        assert word in vault_words

    def test_different_inputs_may_differ(self) -> None:
        w1 = run_pulse("alpha")
        w2 = run_pulse("omega")
        assert isinstance(w1, str) and isinstance(w2, str)
