"""Anchor-lens tour — narrative walkthrough demonstrating the
substantive-axis seam (ADR-0073 → ADR-0073d).

Walks a fixed two-prompt sequence under three ratified lenses
({default_unanchored_v1, grc_logos_v1, he_logos_v1}) and prints a
grid of per-cell ``(surface, grounding_source, trace_hash,
anchor_lens_id, anchor_lens_mode_label)``.

Load-bearing claims asserted before exit (L1.4 invariants — the
*opposite* of register-tour's invariants):

* ``lens_ids_recorded_per_turn`` — every TurnEvent records the
  loaded lens id (empty for unanchored, lens_id otherwise).
* ``trace_hashes_distinct_across_lenses`` — for each prompt where
  any lens engages, at least two distinct trace_hashes appear
  across the three runs.  This is the substantive-axis claim:
  switching the lens moves the proposition, not just the surface
  text.
* ``surface_propositions_distinct_across_lenses`` — at least one
  prompt yields at least two distinct surfaces across the lens
  triple.
* ``no_substrate_glyph_leak`` — no Greek / Hebrew / Syriac / Arabic
  letter blocks appear in any cell's surface under any lens
  (ADR-0073c hard gate, re-asserted in tour scope).

Exit code 0 iff every claim holds.  Designed for ``core demo
anchor-lens-tour`` and the corresponding
``tests/test_anchor_lens_tour_demo.py`` gate.

Composition with register-tour
------------------------------
``register-tour`` asserts trace_hash CONSTANT across registers.
``anchor-lens-tour`` asserts trace_hash DISTINCT across lenses.
Both must hold continuously; failure of either breaks the
orthogonality seam claimed by ADR-0073.
"""

from __future__ import annotations

import json
from typing import Any

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig


_LENSES = (
    "default_unanchored_v1",
    "grc_logos_v1",
    "he_logos_v1",
)

# Prompts are chosen so each non-trivial lens engages on at least one
# of them (grc_logos_v1 on knowledge, he_logos_v1 on truth).  The
# unanchored baseline never engages, demonstrating the null-lift floor
# explicitly inside the tour.
_PROMPTS = (
    "What is knowledge?",
    "What is truth?",
)

#: Forbidden Unicode blocks: substrate letter scripts that anchor lens
#: must not leak (ADR-0073c hard gate).
_FORBIDDEN_BLOCKS: tuple[tuple[int, int, str], ...] = (
    (0x0370, 0x03FF, "Greek and Coptic"),
    (0x1F00, 0x1FFF, "Greek Extended"),
    (0x0590, 0x05FF, "Hebrew"),
    (0x0700, 0x074F, "Syriac"),
    (0x0600, 0x06FF, "Arabic"),
)


_VERBOSE = True


def _say(*args: Any, **kwargs: Any) -> None:
    if _VERBOSE:
        print(*args, **kwargs)


def _print_header() -> None:
    _say()
    _say("=" * 72)
    _say("  CORE Anchor-lens Tour — substantive-axis seam in three lenses")
    _say("=" * 72)
    _say(
        "  Same prompt sequence run under three ratified anchor-lens packs.\n"
        "  Claim: switching lens MOVES the proposition — trace_hash and\n"
        "  surface differ across lenses where engagement fires (ADR-0073\n"
        "  L1.3 lift + L1.4 telemetry).  This is the *opposite* invariant\n"
        "  from `core demo register-tour`, which asserts trace_hash CONSTANT\n"
        "  across registers.  Both invariants must hold continuously."
    )
    _say()


def _substrate_glyph_violations(surface: str) -> list[tuple[int, str, str]]:
    out: list[tuple[int, str, str]] = []
    for i, ch in enumerate(surface):
        cp = ord(ch)
        for start, end, label in _FORBIDDEN_BLOCKS:
            if start <= cp <= end:
                out.append((i, ch, label))
                break
    return out


def _run_one_lens(lens_id: str) -> list[dict[str, Any]]:
    """Run the prompt sequence under ``lens_id`` and return per-cell records."""
    runtime = ChatRuntime(config=RuntimeConfig(anchor_lens_id=lens_id))
    pipeline = CognitiveTurnPipeline(runtime=runtime)
    cells: list[dict[str, Any]] = []
    for prompt in _PROMPTS:
        result = pipeline.run(prompt)
        turn_event = runtime.turn_log[-1]
        cells.append(
            {
                "prompt": prompt,
                "surface": turn_event.surface,
                "grounding_source": getattr(turn_event, "grounding_source", ""),
                "trace_hash": result.trace_hash,
                "anchor_lens_id": getattr(turn_event, "anchor_lens_id", ""),
                "anchor_lens_mode_label": getattr(
                    turn_event, "anchor_lens_mode_label", ""
                ),
            }
        )
    return cells


def _print_grid(grid: dict[str, list[dict[str, Any]]]) -> None:
    for prompt_idx, prompt in enumerate(_PROMPTS):
        _say(f"  P{prompt_idx + 1}: {prompt!r}")
        for lens_id in _LENSES:
            cell = grid[lens_id][prompt_idx]
            _say(f"    {lens_id:24s}  surface = {cell['surface']!r}")
            mode = cell["anchor_lens_mode_label"] or "(no engagement)"
            _say(
                f"    {'':24s}  trace_hash = {cell['trace_hash'][:12]}…  "
                f"mode_label = {mode}"
            )
        _say()


def _check_claims(
    grid: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Return the four load-bearing seam-claim booleans + evidence."""
    lens_ids_recorded = True
    surfaces_vary_at_least_once = False
    trace_hashes_distinct_when_engaged = True
    glyph_violations: list[str] = []

    per_prompt_evidence: list[dict[str, Any]] = []
    for prompt_idx, prompt in enumerate(_PROMPTS):
        cells = [grid[lens_id][prompt_idx] for lens_id in _LENSES]

        # Telemetry visibility: each cell's anchor_lens_id matches the
        # lens we configured (empty when the lens_id was the
        # unanchored sentinel — pack id "default_unanchored_v1" still
        # records as that string).
        for lens_id, cell in zip(_LENSES, cells):
            if cell["anchor_lens_id"] != lens_id:
                lens_ids_recorded = False

        # Glyph-leak gate.
        for lens_id, cell in zip(_LENSES, cells):
            violations = _substrate_glyph_violations(cell["surface"])
            for pos, ch, block in violations:
                glyph_violations.append(
                    f"{prompt!r} × {lens_id}: substrate glyph "
                    f"{ch!r} (block={block}) at pos {pos}"
                )

        # Distinctness claims.  Any prompt where ≥2 distinct
        # surfaces / trace_hashes appear across the lens triple
        # counts toward the "vary at least once" gate.  For the
        # "distinct when engaged" gate, we require that if any lens
        # cell has a non-empty mode_label (engaged), its trace_hash
        # must differ from the unanchored baseline.
        unanchored_cell = cells[0]
        surface_set = {c["surface"] for c in cells}
        if len(surface_set) > 1:
            surfaces_vary_at_least_once = True
        for c in cells[1:]:
            if c["anchor_lens_mode_label"]:
                # Lens engaged; require trace_hash divergence from baseline.
                if c["trace_hash"] == unanchored_cell["trace_hash"]:
                    trace_hashes_distinct_when_engaged = False

        per_prompt_evidence.append(
            {
                "prompt": prompt,
                "distinct_surfaces_count": len(surface_set),
                "distinct_trace_hashes_count": len(
                    {c["trace_hash"] for c in cells}
                ),
                "lenses_engaged": [
                    c["anchor_lens_id"]
                    for c in cells
                    if c["anchor_lens_mode_label"]
                ],
            }
        )

    return {
        "lens_ids_recorded_per_turn": lens_ids_recorded,
        "trace_hashes_distinct_across_lenses": trace_hashes_distinct_when_engaged,
        "surface_propositions_distinct_across_lenses": surfaces_vary_at_least_once,
        "no_substrate_glyph_leak": not glyph_violations,
        "per_prompt_evidence": per_prompt_evidence,
        "glyph_violations": glyph_violations,
    }


def run_tour(*, emit_json: bool = False) -> dict[str, Any]:
    """Run the anchor-lens tour end-to-end and return a structured report."""
    global _VERBOSE
    _VERBOSE = not emit_json

    if not emit_json:
        _print_header()

    grid: dict[str, list[dict[str, Any]]] = {}
    for lens_id in _LENSES:
        if not emit_json:
            _say(f"  Running lens: {lens_id}")
        grid[lens_id] = _run_one_lens(lens_id)
    if not emit_json:
        _say()
        _say("-" * 72)
        _say("  Lens × prompt grid")
        _say("-" * 72)
        _print_grid(grid)

    claims = _check_claims(grid)
    all_supported = (
        claims["lens_ids_recorded_per_turn"]
        and claims["trace_hashes_distinct_across_lenses"]
        and claims["surface_propositions_distinct_across_lenses"]
        and claims["no_substrate_glyph_leak"]
    )

    if not emit_json:
        _say("=" * 72)
        _say("  Load-bearing seam claims (L1.4 invariant)")
        _say("=" * 72)
        _say(
            f"  lens_ids_recorded_per_turn                  : "
            f"{claims['lens_ids_recorded_per_turn']}"
        )
        _say(
            f"  trace_hashes_distinct_across_lenses         : "
            f"{claims['trace_hashes_distinct_across_lenses']}"
        )
        _say(
            f"  surface_propositions_distinct_across_lenses : "
            f"{claims['surface_propositions_distinct_across_lenses']}"
        )
        _say(
            f"  no_substrate_glyph_leak                     : "
            f"{claims['no_substrate_glyph_leak']}"
        )
        _say()
        _say(f"  all_claims_supported                        : {all_supported}")
        _say()

    return {
        "lenses": list(_LENSES),
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
