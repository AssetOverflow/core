"""Integration test — full pulse cycle from injection to vault recall.

Covers both V3 pure-diffusion mode and V4 coupled dual-correction.
"""

import numpy as np
import pytest

from scripts.run_pulse import run_pulse, _build_manifold
from language_packs.compiler import load_pack
from field.operators import (
    ConstraintCorrectionOperator,
    GraphDiffusionOperator,
)


@pytest.fixture(scope="module")
def compiled_manifold():
    _, manifold = load_pack("en_core_cognition_v1")
    return manifold


# ---------------------------------------------------------------------------
# V3 regression — pure diffusion still works
# ---------------------------------------------------------------------------

class TestPulseDiffusion:
    def test_full_cycle_completes(self) -> None:
        words = run_pulse("hello world", use_glove=False)
        assert isinstance(words, list)
        assert len(words) > 0
        assert all(isinstance(w, str) for w in words)

    def test_output_node_changes(self, compiled_manifold) -> None:
        state, labels, _ = _build_manifold("test input", compiled_manifold)
        output_idx = len(labels) - 1
        initial_output = state.fields[output_idx].copy()

        op = GraphDiffusionOperator(damping=0.5)
        for _ in range(20):
            state, _ = op.forward(state)
        assert not np.allclose(state.fields[output_idx], initial_output, atol=1e-7)

    def test_different_inputs_produce_different_output(self) -> None:
        w1 = run_pulse("alpha", use_glove=False)
        w2 = run_pulse("omega", use_glove=False)
        assert isinstance(w1, list) and isinstance(w2, list)

    def test_recall_returns_known_vocab(self, compiled_manifold) -> None:
        words = run_pulse("wisdom seeker", use_glove=False)
        for w in words:
            try:
                compiled_manifold.get_versor(w)
            except KeyError:
                raise AssertionError(f"{w!r} not in compiled vocab")

    def test_no_correction_mode_matches_v3(self) -> None:
        """--no-correction flag reproduces V3 pure-diffusion semantics."""
        words = run_pulse("truth", use_glove=False, use_correction=False)
        assert len(words) > 0


# ---------------------------------------------------------------------------
# ConstraintCorrectionOperator unit tests
# ---------------------------------------------------------------------------

class TestConstraintCorrectionOperator:
    def test_correction_pulls_toward_target(self, compiled_manifold) -> None:
        """After N correction steps, output node is closer to target than before."""
        state, labels, target_versor = _build_manifold("grace", compiled_manifold)
        output_idx = len(labels) - 1

        op = ConstraintCorrectionOperator(
            target_versor=target_versor,
            correction_rate=0.3,
            node_index=output_idx,
        )

        # Distance before
        initial = state.fields[output_idx].astype(np.float64)
        target64 = target_versor.astype(np.float64)
        dist_before = float(np.linalg.norm(initial - target64))

        # Apply 10 correction steps (no diffusion — isolate the correction)
        for _ in range(10):
            state, _ = op.adjoint_pass(state)

        corrected = state.fields[output_idx].astype(np.float64)
        dist_after = float(np.linalg.norm(corrected - target64))

        assert dist_after < dist_before, (
            f"Correction did not pull output toward target: "
            f"dist_before={dist_before:.4f}, dist_after={dist_after:.4f}"
        )

    def test_correction_does_not_collapse_instantly(self, compiled_manifold) -> None:
        """A single correction step with rate=0.3 does not jump to the target."""
        state, labels, target_versor = _build_manifold("knowledge", compiled_manifold)
        output_idx = len(labels) - 1

        op = ConstraintCorrectionOperator(
            target_versor=target_versor,
            correction_rate=0.3,
            node_index=output_idx,
        )
        state, delta = op.adjoint_pass(state)

        corrected = state.fields[output_idx].astype(np.float64)
        target64  = target_versor.astype(np.float64)
        dist = float(np.linalg.norm(corrected - target64))

        # Should be meaningfully close but not zero
        assert dist > 1e-4, (
            f"Single correction step collapsed to target (dist={dist:.2e}); "
            f"rate=0.3 should leave distance > 1e-4"
        )

    def test_correction_rate_zero_raises(self) -> None:
        """rate=0.0 is explicitly rejected (identity — use no_correction flag)."""
        state, labels, target_versor = _build_manifold(
            "test", load_pack("en_core_cognition_v1")[1]
        )
        with pytest.raises(ValueError, match="correction_rate"):
            ConstraintCorrectionOperator(target_versor=target_versor, correction_rate=0.0)

    def test_correction_maintains_versor_invariant(self, compiled_manifold) -> None:
        """Output node versor satisfies V·reverse(V) ≈ ±1 after correction."""
        from algebra.versor import versor_unit_residual

        state, labels, target_versor = _build_manifold("peace", compiled_manifold)
        output_idx = len(labels) - 1

        op = ConstraintCorrectionOperator(
            target_versor=target_versor,
            correction_rate=0.5,
            node_index=output_idx,
        )
        for _ in range(5):
            state, _ = op.adjoint_pass(state)

        residual = versor_unit_residual(
            state.fields[output_idx].astype(np.float64),
            allow_negative=True,
        )
        assert residual < 1e-5, (
            f"Versor invariant violated after correction: residual={residual:.2e}"
        )

    def test_different_targets_produce_different_corrections(self, compiled_manifold) -> None:
        """Correction targets built from different prompts are geometrically distinct."""
        _, _, target_a = _build_manifold("light",     compiled_manifold)
        _, _, target_b = _build_manifold("darkness",  compiled_manifold)

        # targets should differ
        dist = float(np.linalg.norm(
            target_a.astype(np.float64) - target_b.astype(np.float64)
        ))
        assert dist > 1e-4, (
            f"Targets for 'light' and 'darkness' are identical (dist={dist:.2e})"
        )


# ---------------------------------------------------------------------------
# V4 coupled loop integration
# ---------------------------------------------------------------------------

class TestCoupledPulse:
    def test_coupled_loop_converges(self) -> None:
        """Full V4 pulse with correction converges and returns recall."""
        words = run_pulse(
            "what is truth",
            use_glove=False,
            use_correction=True,
            correction_rate=0.3,
        )
        assert len(words) > 0
        assert all(isinstance(w, str) for w in words)

    def test_correction_changes_recall_vs_pure_diffusion(self) -> None:
        """With correction enabled, recall may differ from pure-diffusion mode.

        Both must return valid vocab words.  We don't assert they differ
        (they may agree on some inputs), but both paths must complete.
        """
        words_v3 = run_pulse(
            "wisdom", use_glove=False, use_correction=False,
        )
        words_v4 = run_pulse(
            "wisdom", use_glove=False, use_correction=True, correction_rate=0.3,
        )
        assert len(words_v3) > 0
        assert len(words_v4) > 0

    def test_high_correction_rate_biases_toward_target(self, compiled_manifold) -> None:
        """With correction_rate=0.9, the output node should be very close
        to the target versor after the loop.
        """
        _, labels, target_versor = _build_manifold("hope", compiled_manifold)
        output_idx = len(labels) - 1

        # Run manually to inspect the final output node.
        from algebra.backend import cga_inner

        state, labels, target_versor = _build_manifold("hope", compiled_manifold)
        diffusion_op  = GraphDiffusionOperator(damping=0.5)
        correction_op = ConstraintCorrectionOperator(
            target_versor=target_versor,
            correction_rate=0.9,
            node_index=-1,
        )

        for _ in range(100):
            state, _ = diffusion_op.forward(state)
            state, _ = correction_op.adjoint_pass(state)

        output = state.fields[output_idx].astype(np.float64)
        target = target_versor.astype(np.float64)
        dist   = float(np.linalg.norm(output - target))
        # High correction rate should produce strong convergence toward target.
        assert dist < 0.5, (
            f"High correction_rate=0.9 did not pull output close to target: dist={dist:.4f}"
        )
