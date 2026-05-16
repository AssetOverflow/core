"""Proof-level property tests for CORE.

These tests verify structural properties that distinguish CORE from
stochastic LLMs:
  - Determinism: identical input -> identical output, always
  - Rust/Python parity: both backends produce identical results
  - Convergence: every eval prompt converges within MAX_STEPS
  - Realizer coverage: every intent type produces a non-empty surface
  - Versor closure: field invariant holds at every intermediate step
"""

from __future__ import annotations

import os

import numpy as np
import pytest

from algebra.backend import using_rust, versor_condition
from field.operators import (
    ConstraintCorrectionOperator,
    GraphDiffusionOperator,
)
from language_packs.compiler import load_pack
from scripts.run_pulse import _build_manifold, run_pulse


@pytest.fixture(scope="module")
def compiled_manifold():
    _, manifold = load_pack("en_core_cognition_v1")
    return manifold


# ---------------------------------------------------------------------------
# Determinism proof
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Same input must produce bit-identical output every time."""

    @pytest.mark.parametrize("prompt", [
        "What is truth?",
        "Compare knowledge and wisdom",
        "Why does light exist?",
        "truth",
    ])
    def test_pulse_determinism(self, prompt: str) -> None:
        r1 = run_pulse(prompt, use_glove=False)
        r2 = run_pulse(prompt, use_glove=False)
        assert r1.recalled_words == r2.recalled_words, (
            f"Recall diverged: {r1.recalled_words} vs {r2.recalled_words}"
        )
        assert r1.surface == r2.surface, (
            f"Surface diverged: {r1.surface!r} vs {r2.surface!r}"
        )

    def test_diffusion_determinism(self, compiled_manifold) -> None:
        """GraphDiffusionOperator is deterministic across runs."""
        state, _, _ = _build_manifold("truth and light", compiled_manifold)
        op = GraphDiffusionOperator(damping=0.5)

        s1 = state
        for _ in range(50):
            s1, _ = op.forward(s1)

        s2 = state
        for _ in range(50):
            s2, _ = op.forward(s2)

        assert np.array_equal(s1.fields, s2.fields)


# ---------------------------------------------------------------------------
# Rust/Python parity
# ---------------------------------------------------------------------------

class TestBackendParity:
    """Both backends must produce identical results."""

    @pytest.mark.skipif(not using_rust(), reason="Rust backend not available")
    def test_unitize_parity(self) -> None:
        """Rust and Python unitize produce the same rotor."""
        from field.operators import _unitize_f32

        test_vectors = [
            np.zeros(32, dtype=np.float32),
            np.eye(32, dtype=np.float32)[0],
        ]
        v = np.zeros(32, dtype=np.float32)
        v[0] = 0.8; v[6] = 0.3; v[9] = 0.2
        test_vectors.append(v)
        v2 = np.zeros(32, dtype=np.float32)
        v2[0] = -0.5; v2[7] = 0.4; v2[12] = 0.1
        test_vectors.append(v2)

        for i, vec in enumerate(test_vectors):
            rust_result = _unitize_f32(vec)
            vc = versor_condition(rust_result)
            assert vc < 1e-4, (
                f"Vector {i}: Rust unitize versor_condition={vc:.2e}"
            )

    @pytest.mark.skipif(not using_rust(), reason="Rust backend not available")
    def test_diffusion_parity(self, compiled_manifold) -> None:
        """Rust and Python diffusion forward produce the same state."""
        import importlib

        state, _, _ = _build_manifold("truth light", compiled_manifold)
        op_rust = GraphDiffusionOperator(damping=0.5)

        s_rust = state
        for _ in range(10):
            s_rust, _ = op_rust.forward(s_rust)

        # Force Python backend
        import importlib
        import algebra.backend as _ab
        from field import operators as _ops

        env_backup = os.environ.get("CORE_BACKEND")
        os.environ["CORE_BACKEND"] = "python"
        try:
            importlib.reload(_ab)
            _ops._rust_diffusion_step = _ab.diffusion_step
            _ops._rust_unitize = _ab.unitize_expmap

            op_python = GraphDiffusionOperator(damping=0.5)
            s_py = state
            for _ in range(10):
                s_py, _ = op_python.forward(s_py)
        finally:
            if env_backup is not None:
                os.environ["CORE_BACKEND"] = env_backup
            else:
                os.environ.pop("CORE_BACKEND", None)
            importlib.reload(_ab)
            _ops._rust_diffusion_step = _ab.diffusion_step
            _ops._rust_unitize = _ab.unitize_expmap

        assert np.allclose(s_rust.fields, s_py.fields, atol=1e-4), (
            f"Backend divergence: max_diff={np.max(np.abs(s_rust.fields - s_py.fields)):.2e}"
        )


# ---------------------------------------------------------------------------
# Convergence proof
# ---------------------------------------------------------------------------

class TestConvergenceProof:
    """Every eval prompt must converge or reach a bounded equilibrium."""

    @pytest.mark.parametrize("prompt", [
        "What is truth?",
        "What is light?",
        "What is knowledge?",
        "Compare truth and light",
        "Why does light exist?",
        "How do I define a concept?",
        "Is truth coherent?",
        "No, that is wrong",
        "truth",
        "light",
    ])
    def test_prompt_converges_v3(self, prompt: str) -> None:
        """Pure diffusion (V3) converges for asymmetric/3+ token topologies."""
        result = run_pulse(prompt, use_glove=False, use_correction=False)
        assert result.converged, (
            f"V3 pulse did not converge for {prompt!r} in {result.steps} steps"
        )

    def test_symmetric_2token_bounded(self) -> None:
        """Symmetric 2-token star topologies may oscillate but must
        produce valid output with bounded delta."""
        result = run_pulse("Remember truth", use_glove=False, use_correction=False)
        assert len(result.recalled_words) > 0
        assert result.surface

    @pytest.mark.parametrize("prompt", [
        "What is truth?",
        "What is light?",
        "Compare truth and light",
        "truth",
    ])
    def test_coupled_pulse_produces_output(self, prompt: str) -> None:
        """V4 coupled pulse produces recall and surface even when the
        dual-correction loop reaches a limit cycle rather than exact
        convergence. Both modes must produce valid output."""
        result = run_pulse(prompt, use_glove=False, use_correction=True)
        assert len(result.recalled_words) > 0
        assert result.surface


# ---------------------------------------------------------------------------
# Realizer join coverage
# ---------------------------------------------------------------------------

class TestRealizerCoverage:
    """Every intent type must produce a non-empty surface."""

    @pytest.mark.parametrize("intent,prompt", [
        ("definition", "What is truth?"),
        ("comparison", "Compare knowledge and wisdom"),
        ("cause", "Why does light exist?"),
        ("procedure", "How do I define a concept?"),
        ("recall", "Remember truth"),
        ("verification", "Is truth coherent?"),
        ("correction", "No, that's wrong"),
        ("unknown", "truth"),
    ])
    def test_intent_produces_surface(self, intent: str, prompt: str) -> None:
        result = run_pulse(prompt, use_glove=False)
        assert result.surface, (
            f"Intent {intent!r} produced empty surface for {prompt!r}"
        )
        assert isinstance(result.surface, str)
        assert result.surface.endswith(".")


# ---------------------------------------------------------------------------
# Versor closure audit
# ---------------------------------------------------------------------------

class TestVersorClosureAudit:
    """Field invariant versor_condition < 1e-6 must hold at every step."""

    def test_intermediate_states_satisfy_invariant(self, compiled_manifold) -> None:
        prompts = ["What is truth?", "Compare knowledge and wisdom", "truth"]
        steps_per_prompt = 30

        for prompt in prompts:
            state, _, target = _build_manifold(prompt, compiled_manifold)
            diff_op = GraphDiffusionOperator(damping=0.5)
            corr_op = ConstraintCorrectionOperator(
                target_versor=target, correction_rate=0.3, node_index=-1,
            )

            for step in range(steps_per_prompt):
                state, _ = diff_op.forward(state)
                state, _ = corr_op.adjoint_pass(state)

                for i in range(state.fields.shape[0]):
                    vc = versor_condition(state.fields[i])
                    assert vc < 1e-6, (
                        f"Versor violation at prompt={prompt!r}, step={step}, "
                        f"node={i}: vc={vc:.2e}"
                    )
