"""Register tour — narrative walkthrough demonstrating the
presentation-axis seam (ADR-0068 → ADR-0072).

Walks a fixed four-prompt sequence under three ratified registers
({default_neutral_v1, terse_v1, convivial_v1}) and prints a grid of
per-cell ``(surface, grounding_source, trace_hash, register_id,
register_variant_id)``.

Load-bearing claims asserted before exit:

* ``all_grounding_sources_identical`` — R5 invariant.  For every
  prompt, the grounding_source is byte-identical across registers.
* ``all_trace_hashes_identical`` — R5 invariant.  For every prompt,
  the trace_hash is byte-identical across registers.  ADR-0077 (R6)
  strengthens this: it must hold even while substantive register
  transforms produce visibly different post-substantive surfaces.
* ``register_canonical_surfaces_identical`` — ADR-0077 (R6).  For
  every prompt, ``register_canonical_surface`` (the composer output
  BEFORE any register transformation) is byte-identical across
  registers.  Direct proof of the layering separation.
* ``terse_substantively_differs_from_neutral_on_pack_grounded_definition``
  — ADR-0077 (R6).  Replaces the old falsifiable-by-decoration
  ``surfaces_vary_at_least_once`` claim.  At least one DEFINITION
  prompt with ``grounding_source == "pack"`` produces a surface under
  terse_v1 that is byte-different from the neutral surface AND whose
  difference is not solely whitespace/punctuation.
* ``convivial_substantively_differs_from_neutral_on_pack_grounded_definition``
  — ADR-0077 (R6).  Same shape for convivial_v1.  Convivial's
  substantive contribution includes the appended
  ``Related: <atom>.`` clause OR the seeded marker; both are
  non-whitespace differences.

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
                # ADR-0077 (R6) — composer output BEFORE substantive
                # transformations; the truth-path identity field.
                "register_canonical_surface": getattr(
                    turn_event, "register_canonical_surface", "",
                ),
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


_DEFINITION_PROMPTS: frozenset[str] = frozenset({
    "What is light?",
    "Define knowledge.",
    "What is truth?",
})
"""Prompts in :data:`_PROMPTS` that the cognition pack classifies as
DEFINITION / RECALL.  The strengthened R6 gate measures substantive
distinctness against these specifically — they are the prompts where
the gloss DEFINITION composer fires and substantive transforms have
an observable effect.  Confirmation-tag and other intents are out
of the strengthened-gate scope per ADR-0077."""


def _strip_whitespace_and_punct(s: str) -> str:
    """Reduce a surface to its content fingerprint.

    Removes every ASCII whitespace and punctuation character, then
    lowercases.  Two surfaces differ "substantively" iff their
    fingerprints differ — pure whitespace/punctuation changes
    (paragraph wrapping, additional period after register markers,
    etc.) collapse to the same fingerprint and fail the gate.
    """
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch.lower())
    return "".join(out)


def _substantively_differs(a: str, b: str) -> bool:
    """True iff *a* and *b* differ on more than whitespace/punctuation."""
    if a == b:
        return False
    return _strip_whitespace_and_punct(a) != _strip_whitespace_and_punct(b)


def _check_claims(
    grid: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Return the strengthened R6 gate claims + per-prompt evidence."""

    all_grounding_identical = True
    all_trace_hashes_identical = True
    canonical_identical = True
    terse_substantive_hit = False
    convivial_substantive_hit = False

    per_prompt_evidence: list[dict[str, Any]] = []
    for prompt_idx, prompt in enumerate(_PROMPTS):
        cells = [grid[r][prompt_idx] for r in _REGISTERS]
        by_register = dict(zip(_REGISTERS, cells))
        grounding_set = {c["grounding_source"] for c in cells}
        trace_set = {c["trace_hash"] for c in cells}
        canonical_set = {c["register_canonical_surface"] for c in cells}
        if len(grounding_set) > 1:
            all_grounding_identical = False
        if len(trace_set) > 1:
            all_trace_hashes_identical = False
        if len(canonical_set) > 1:
            canonical_identical = False

        # R6 strengthened gate fires only on DEFINITION prompts where
        # grounding_source == "pack" — the cells where pack-grounded
        # gloss + substantive transforms compose.  Other prompts are
        # observational (still recorded; not gating).
        neutral_cell = by_register["default_neutral_v1"]
        terse_cell = by_register["terse_v1"]
        convivial_cell = by_register["convivial_v1"]
        prompt_is_def = (
            prompt in _DEFINITION_PROMPTS
            and neutral_cell["grounding_source"] == "pack"
        )
        terse_diff = False
        convivial_diff = False
        if prompt_is_def:
            terse_diff = _substantively_differs(
                neutral_cell["surface"], terse_cell["surface"],
            )
            convivial_diff = _substantively_differs(
                neutral_cell["surface"], convivial_cell["surface"],
            )
            if terse_diff:
                terse_substantive_hit = True
            if convivial_diff:
                convivial_substantive_hit = True

        per_prompt_evidence.append(
            {
                "prompt": prompt,
                "distinct_grounding_sources": sorted(grounding_set),
                "distinct_trace_hashes": sorted(trace_set),
                "distinct_canonical_surfaces_count": len(canonical_set),
                "is_definition_pack_prompt": prompt_is_def,
                "terse_substantively_differs": terse_diff,
                "convivial_substantively_differs": convivial_diff,
            }
        )

    return {
        "all_grounding_sources_identical": all_grounding_identical,
        "all_trace_hashes_identical": all_trace_hashes_identical,
        "register_canonical_surfaces_identical": canonical_identical,
        "terse_substantively_differs_from_neutral_on_pack_grounded_definition":
            terse_substantive_hit,
        "convivial_substantively_differs_from_neutral_on_pack_grounded_definition":
            convivial_substantive_hit,
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
        and claims["register_canonical_surfaces_identical"]
        and claims["terse_substantively_differs_from_neutral_on_pack_grounded_definition"]
        and claims["convivial_substantively_differs_from_neutral_on_pack_grounded_definition"]
    )

    if not emit_json:
        _say("=" * 72)
        _say("  Load-bearing seam claims (R5 + R6 invariants)")
        _say("=" * 72)
        _say(
            f"  all_grounding_sources_identical          : "
            f"{claims['all_grounding_sources_identical']}"
        )
        _say(
            f"  all_trace_hashes_identical               : "
            f"{claims['all_trace_hashes_identical']}"
        )
        _say(
            f"  register_canonical_surfaces_identical    : "
            f"{claims['register_canonical_surfaces_identical']}"
        )
        _say(
            f"  terse_substantively_differs              : "
            f"{claims['terse_substantively_differs_from_neutral_on_pack_grounded_definition']}"
        )
        _say(
            f"  convivial_substantively_differs          : "
            f"{claims['convivial_substantively_differs_from_neutral_on_pack_grounded_definition']}"
        )
        _say()
        _say(f"  all_claims_supported                     : {all_supported}")
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
