"""Register tour — narrative walkthrough demonstrating the
presentation-axis seam (ADR-0068 → ADR-0072).

Walks a fixed four-prompt sequence under three ratified registers
({default_neutral_v1, terse_v1, convivial_v1}) and prints a grid of
per-cell ``(surface, grounding_source, trace_hash, register_id,
register_variant_id)``.

Load-bearing claim asserted before exit (R5 invariant):

* ``all_grounding_sources_identical`` — for every prompt, the
  grounding_source is byte-identical across registers.
* ``all_trace_hashes_identical`` — for every prompt, the trace_hash is
  byte-identical across registers.
* ``surfaces_vary_at_least_once`` — at least one prompt produces a
  visibly different surface under convivial vs neutral (the variation
  is real, not stubbed).

Exit code 0 iff every claim holds.  Designed for ``core demo
register-tour`` and the corresponding ``tests/test_register_tour_demo.py``
gate.
"""

from __future__ import annotations

import json
from typing import Any

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig


# Three ratified registers cover the three structural points of the
# R1–R4 architecture: unregistered-equivalent neutral baseline, the
# realizer-override variant (terse_v1), and the seeded-variation
# variant (convivial_v1).
_REGISTERS = (
    "default_neutral_v1",
    "terse_v1",
    "convivial_v1",
)

# A fixed, deterministic prompt sequence.  Each prompt is chosen to
# exercise a different grounding source on the cold path so the
# register-invariance claim holds across the breadth of the cognition
# lane, not just one intent shape.
_PROMPTS = (
    "What is light?",
    "Define knowledge.",
    "What is truth?",
    "Light reveals truth, right?",
)


_VERBOSE = True


def _say(*args: Any, **kwargs: Any) -> None:
    if _VERBOSE:
        print(*args, **kwargs)


def _print_header() -> None:
    _say()
    _say("=" * 72)
    _say("  CORE Register Tour — presentation-axis seam in three registers")
    _say("=" * 72)
    _say(
        "  Same prompt sequence run under three ratified register packs.\n"
        "  Claim: switching register varies SURFACE only — grounding_source\n"
        "  and trace_hash stay byte-identical (ADR-0069 invariant C,\n"
        "  ADR-0070 register_invariant_grounding, ADR-0071 seeded variation\n"
        "  replay equivalence, ADR-0072 operator-visible audit)."
    )
    _say()


def _run_one_register(register_id: str) -> list[dict[str, Any]]:
    """Run the prompt sequence under ``register_id`` and return per-cell records."""
    runtime = ChatRuntime(config=RuntimeConfig(register_pack_id=register_id))
    pipeline = CognitiveTurnPipeline(runtime=runtime)
    cells: list[dict[str, Any]] = []
    for prompt in _PROMPTS:
        # ``pipeline.run(prompt)`` computes trace_hash on the pre-
        # decoration surface (ADR-0069 invariant C).  We want the
        # *post-decoration* surface (the user-facing string) for the
        # surface-varies claim, which lives on TurnEvent.surface after
        # ChatRuntime applied seeded variation.
        result = pipeline.run(prompt)
        turn_event = runtime.turn_log[-1]
        cells.append(
            {
                "prompt": prompt,
                "surface": turn_event.surface,
                "grounding_source": getattr(turn_event, "grounding_source", ""),
                "trace_hash": result.trace_hash,
                "register_id": getattr(turn_event, "register_id", ""),
                "register_variant_id": getattr(turn_event, "register_variant_id", ""),
            }
        )
    return cells


def _print_grid(grid: dict[str, list[dict[str, Any]]]) -> None:
    for prompt_idx, prompt in enumerate(_PROMPTS):
        _say(f"  P{prompt_idx + 1}: {prompt!r}")
        for register_id in _REGISTERS:
            cell = grid[register_id][prompt_idx]
            _say(
                f"    {register_id:24s}  surface = {cell['surface']!r}"
            )
            _say(
                f"    {'':24s}  grounding = {cell['grounding_source']:<10s}"
                f"  trace_hash = {cell['trace_hash'][:12]}…"
                f"  variant_id = {cell['register_variant_id'] or '(none)'}"
            )
        _say()


def _check_claims(
    grid: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Return the three load-bearing seam-claim booleans + supporting evidence."""

    all_grounding_identical = True
    all_trace_hashes_identical = True
    surfaces_vary_at_least_once = False

    per_prompt_evidence: list[dict[str, Any]] = []
    for prompt_idx, prompt in enumerate(_PROMPTS):
        cells = [grid[r][prompt_idx] for r in _REGISTERS]
        grounding_set = {c["grounding_source"] for c in cells}
        trace_set = {c["trace_hash"] for c in cells}
        surface_set = {c["surface"] for c in cells}
        if len(grounding_set) > 1:
            all_grounding_identical = False
        if len(trace_set) > 1:
            all_trace_hashes_identical = False
        if len(surface_set) > 1:
            surfaces_vary_at_least_once = True
        per_prompt_evidence.append(
            {
                "prompt": prompt,
                "distinct_grounding_sources": sorted(grounding_set),
                "distinct_trace_hashes": sorted(trace_set),
                "distinct_surfaces_count": len(surface_set),
            }
        )

    return {
        "all_grounding_sources_identical": all_grounding_identical,
        "all_trace_hashes_identical": all_trace_hashes_identical,
        "surfaces_vary_at_least_once": surfaces_vary_at_least_once,
        "per_prompt_evidence": per_prompt_evidence,
    }


def run_tour(*, emit_json: bool = False) -> dict[str, Any]:
    """Run the register tour end-to-end and return a structured report.

    When ``emit_json`` is True the human narration is suppressed and
    only the result dict is returned (caller prints it).  Otherwise
    narration is printed and the dict is returned for index callers.
    """
    global _VERBOSE
    _VERBOSE = not emit_json

    if not emit_json:
        _print_header()

    grid: dict[str, list[dict[str, Any]]] = {}
    for register_id in _REGISTERS:
        if not emit_json:
            _say(f"  Running register: {register_id}")
        grid[register_id] = _run_one_register(register_id)
    if not emit_json:
        _say()
        _say("-" * 72)
        _say("  Register × prompt grid")
        _say("-" * 72)
        _print_grid(grid)

    claims = _check_claims(grid)
    all_supported = (
        claims["all_grounding_sources_identical"]
        and claims["all_trace_hashes_identical"]
        and claims["surfaces_vary_at_least_once"]
    )

    if not emit_json:
        _say("=" * 72)
        _say("  Load-bearing seam claims (R5 invariant)")
        _say("=" * 72)
        _say(
            f"  all_grounding_sources_identical : "
            f"{claims['all_grounding_sources_identical']}"
        )
        _say(
            f"  all_trace_hashes_identical      : "
            f"{claims['all_trace_hashes_identical']}"
        )
        _say(
            f"  surfaces_vary_at_least_once     : "
            f"{claims['surfaces_vary_at_least_once']}"
        )
        _say()
        _say(f"  all_claims_supported            : {all_supported}")
        _say()

    return {
        "registers": list(_REGISTERS),
        "prompts": list(_PROMPTS),
        "grid": grid,
        "claims": claims,
        "all_claims_supported": all_supported,
    }


if __name__ == "__main__":  # pragma: no cover
    import sys

    emit_json = "--json" in sys.argv
    report = run_tour(emit_json=emit_json)
    if emit_json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    sys.exit(0 if report["all_claims_supported"] else 1)
