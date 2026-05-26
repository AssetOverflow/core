"""Regression test for issue #300 — versor_condition margin at the
ingest-gate boundary.

The bug: ``ingest.gate.inject`` raised RuntimeError("Injection produced
non-versor field") on a class of ordinary English token combinations
(declarative-with-quantity + transfer phrase + "How many" question).
Both observed condition values (1.02e-06, 2.12e-06) cleared
``unitize_versor``'s ``bad_residue`` heuristic but landed just above
the gate's 1e-6 threshold, crashing the engine on textbook word
problems.

The fix: ``normalize_to_versor`` now applies the strict-closure
pattern from ``_runtime_closed`` — when unitization succeeds but the
result still fails ``versor_condition < 1e-6``, project through the
deterministic construction map instead of returning the drifted
candidate.  Threshold stays at 1e-6 per CLAUDE.md; the construction
boundary is where the margin is repaired.
"""

from __future__ import annotations

import subprocess

import numpy as np
import pytest

from algebra.versor import (
    _RUNTIME_CLOSURE_TOLERANCE,
    normalize_to_versor,
    versor_condition,
)


# ---------------------------------------------------------------------------
# Property: normalize_to_versor's output always satisfies the gate's
# downstream condition < 1e-6 contract.
# ---------------------------------------------------------------------------


class TestNormalizeToVersorClosure:
    def test_threshold_is_pinned_at_1e_minus_6(self) -> None:
        """CLAUDE.md non-negotiable.  Lowering this threshold to make
        tests pass violates the field-invariant doctrine."""
        assert _RUNTIME_CLOSURE_TOLERANCE == 1e-6

    @pytest.mark.parametrize("seed", [0, 1, 2, 7, 42, 99])
    def test_random_seeds_yield_closed_versors(self, seed: int) -> None:
        """A wide sample of seeded random inputs must produce outputs
        whose versor_condition strictly satisfies the gate's contract."""
        rng = np.random.default_rng(seed)
        raw = rng.standard_normal(32)
        out = normalize_to_versor(raw)
        cond = versor_condition(out)
        assert cond < _RUNTIME_CLOSURE_TOLERANCE, (
            f"normalize_to_versor produced cond={cond:.2e} >= "
            f"{_RUNTIME_CLOSURE_TOLERANCE:.2e} for seed={seed}"
        )

    def test_synthetic_marginal_input_routes_through_construction(self) -> None:
        """A handcrafted input that lands marginally above the threshold
        under unitize alone must be routed to the construction-fallback
        path and emerge closed."""
        # Construct a versor whose post-unitize condition is on the
        # 1e-6 boundary by perturbing a near-rotor seed.  The exact
        # values come from observation; the property under test is
        # that normalize_to_versor's output, regardless of input drift,
        # satisfies the gate contract.
        rng = np.random.default_rng(2026_05_26)
        for _ in range(20):
            raw = rng.standard_normal(32) * 1e-3
            raw[0] = 1.0 + rng.standard_normal() * 1e-7
            out = normalize_to_versor(raw)
            assert versor_condition(out) < _RUNTIME_CLOSURE_TOLERANCE


# ---------------------------------------------------------------------------
# End-to-end repros from issue #300.  Each is a real English sentence
# combination whose token-walk crashed the gate before the fix.
# ---------------------------------------------------------------------------


_CRASH_REPROS: tuple[str, ...] = (
    "Tom has 5 apples. He gives 2 to Sarah. How many does Tom have?",
    "Tom has 5 apples. He gives 2 to Mary. How many does Tom have?",
    "Tom has 5 apples. He gives 2 to her. How many does Tom have?",
)


@pytest.mark.parametrize("prompt", _CRASH_REPROS)
def test_issue_300_prompts_no_longer_crash_through_core_chat(prompt: str) -> None:
    """The three bisected crash repros from issue #300 must complete
    without raising the gate's RuntimeError.  Exit code 0 + no
    'non-versor field' substring in stderr suffices — the contents of
    the surface are doctrine-elsewhere.
    """
    result = subprocess.run(
        ["uv", "run", "core", "chat"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=120,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "Injection produced non-versor field" not in combined, (
        f"issue #300 regression: prompt {prompt!r} raised the "
        f"versor-margin RuntimeError"
    )
    assert result.returncode == 0, (
        f"core chat exited {result.returncode} on prompt {prompt!r}; "
        f"stderr tail: {(result.stderr or '')[-300:]}"
    )
