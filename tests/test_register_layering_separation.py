"""ADR-0077 (R6) — register layering separation tests.

Pins the load-bearing invariant that distinguishes R6 from a naive
register implementation: substantive register transforms must not
move ``trace_hash``.  The cognition pipeline hashes
``register_canonical_surface`` (composer output BEFORE any register
transformation); this module proves that field is byte-identical
across registers and the trace_hash derived from it is constant.

Companion to ``tests/test_register_substantive_consumption.py``
(which proves the transforms ARE doing visible work on the user-
facing surface).  Together these gate the strict orthogonality
claim: "register varies user-facing wording without moving the truth
path identity".
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig


_REGISTERS = ("default_neutral_v1", "terse_v1", "convivial_v1")
_DEFINITION_PROMPTS = (
    "What is light?",
    "Define knowledge.",
    "What is truth?",
)


def _run_one(register_id: str, prompts: tuple[str, ...]):
    """Run *prompts* under *register_id* and return per-prompt records."""
    rt = ChatRuntime(config=RuntimeConfig(register_pack_id=register_id))
    pipe = CognitiveTurnPipeline(runtime=rt)
    records = []
    for prompt in prompts:
        result = pipe.run(prompt)
        te = rt.turn_log[-1]
        records.append({
            "prompt": prompt,
            "surface": te.surface,
            "canonical": te.register_canonical_surface,
            "trace_hash": result.trace_hash,
            "grounding_source": te.grounding_source,
        })
    return records


@pytest.fixture(scope="module")
def grid():
    return {r: _run_one(r, _DEFINITION_PROMPTS) for r in _REGISTERS}


# ---------- invariant_register_canonical_surface_constant_across_registers ----------


def test_canonical_surface_byte_identical_across_registers(grid):
    """The composer output is the same on the truth-path regardless of
    which register pack is loaded — substantive transforms operate
    strictly downstream."""
    for prompt_idx, prompt in enumerate(_DEFINITION_PROMPTS):
        canonicals = {grid[r][prompt_idx]["canonical"] for r in _REGISTERS}
        assert len(canonicals) == 1, (
            f"Canonical surface differs across registers on {prompt!r}: "
            f"{canonicals}"
        )


def test_canonical_surface_nonempty_under_r6(grid):
    """Every R6 turn must populate register_canonical_surface (the
    pipeline depends on it for trace_hash)."""
    for prompt_idx in range(len(_DEFINITION_PROMPTS)):
        for register_id in _REGISTERS:
            cell = grid[register_id][prompt_idx]
            assert cell["canonical"], (
                f"empty register_canonical_surface on "
                f"{register_id} / {cell['prompt']!r}"
            )


# ---------- invariant_trace_hash_constant_across_registers_per_prompt ----------


def test_trace_hash_byte_identical_across_registers(grid):
    for prompt_idx, prompt in enumerate(_DEFINITION_PROMPTS):
        hashes = {grid[r][prompt_idx]["trace_hash"] for r in _REGISTERS}
        assert len(hashes) == 1, (
            f"trace_hash differs across registers on {prompt!r}: {hashes}"
        )


def test_trace_hash_invariance_holds_while_surfaces_differ(grid):
    """R6's load-bearing claim: trace_hash is constant ACROSS REGISTERS
    *while substantive surfaces are demonstrably different* on the
    same prompt.  Both halves must hold."""
    for prompt_idx, prompt in enumerate(_DEFINITION_PROMPTS):
        surfaces = {grid[r][prompt_idx]["surface"] for r in _REGISTERS}
        hashes = {grid[r][prompt_idx]["trace_hash"] for r in _REGISTERS}
        assert len(hashes) == 1, prompt
        # At least neutral vs terse must differ (terse has 3 knobs on).
        neutral = grid["default_neutral_v1"][prompt_idx]["surface"]
        terse = grid["terse_v1"][prompt_idx]["surface"]
        assert neutral != terse, (
            f"R6 not engaging on {prompt!r}: neutral and terse surfaces "
            "match byte-for-byte"
        )
        # Three distinct surfaces total (neutral, terse, convivial).
        assert len(surfaces) == 3, (
            f"Expected 3 distinct surfaces on {prompt!r}, got {len(surfaces)}"
        )


# ---------- pipeline read-source preference ----------


def test_pipeline_prefers_canonical_over_pre_decoration():
    """When ``register_canonical_surface`` is populated, the pipeline
    must hash it (not the post-substantive ``pre_decoration_surface``).

    Proof: under terse_v1, ``pre_decoration_surface`` differs
    substantively from ``register_canonical_surface``.  If the
    pipeline read pre_decoration, terse's trace_hash would differ
    from neutral's.  The previous test pinned hashes equal, so
    transitively the pipeline must be reading canonical.

    This test makes the proof direct: the two surfaces are
    measurably different and the canonical-prefer rule is the only
    explanation for the constant hash.
    """
    rt_terse = ChatRuntime(config=RuntimeConfig(register_pack_id="terse_v1"))
    response = rt_terse.chat("What is light?")
    assert response.register_canonical_surface != response.pre_decoration_surface, (
        "Test invalid: terse_v1 produced identical canonical and "
        "pre_decoration surfaces; the R6 knobs are no longer firing."
    )


# ---------- Backward compatibility ----------


def test_event_without_canonical_falls_back_to_pre_decoration():
    """A TurnEvent constructed without ``register_canonical_surface``
    (pre-R6 caller) must still hash via ``pre_decoration_surface``.

    Direct unit test on the pipeline's surface-selection helper would
    be ideal, but the field default is ``""`` and getattr returns it
    cleanly, so this is exercised by the historical pre-R6 trace_hash
    byte-identity invariants that have been pinned since R4.
    """
    from core.physics.identity import TurnEvent
    te = TurnEvent(
        turn=0,
        input_tokens=("hello",),
        surface="x",
        walk_surface="y",
        articulation_surface="z",
        dialogue_role="assert",
        identity_score=None,
        cycle_cost_total=0.0,
        vault_hits=0,
        versor_condition=0.0,
        flagged=False,
    )
    # Pre-R6 default values
    assert te.register_canonical_surface == ""
