"""Orthogonality tour — composes register × anchor-lens × prompts in
one 3 × 3 × 2 grid (ADR-0074).

The single-axis tours assert opposite invariants:

  register-tour    : per (lens, prompt), trace_hash CONSTANT across
                     registers (R5 / ADR-0072).
  anchor-lens-tour : per (register=neutral, prompt), trace_hash
                     DISTINCT across engaging lenses
                     (L1.4 / ADR-0073d).

This tour packages both claims simultaneously into a single demo
that walks the full register × lens × prompt matrix and asserts
the orthogonality holds turn-by-turn across all 18 cells.

Composed claims
---------------

* **A) inner_register_invariant_within_lens** — for each
  (lens, prompt), the three register runs share an identical
  trace_hash.
* **B) outer_lens_distinctness_within_register** — for each
  (register, prompt) where any non-unanchored lens engages, the
  engaged lens's trace_hash differs from the unanchored baseline.
* **C) surface_carries_register_marker_under_convivial** — every
  convivial cell with a non-empty surface has a non-empty
  ``register_variant_id``.
* **D) surface_carries_lens_annotation_when_engaged** — every
  engaged cell carries the ``[lens(<id>):<mode>]`` annotation and a
  non-empty ``anchor_lens_mode_label``.
* **E) no_substrate_glyph_leak_across_grid** — no cell's surface
  contains Greek/Hebrew/Syriac/Arabic glyphs.

Exit code 0 iff every claim holds.
"""

from __future__ import annotations

import json
from functools import partial
from typing import Any, Callable

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from evals._parallel import normalize_workers, run_cases_parallel


_REGISTERS = (
    "default_neutral_v1",
    "terse_v1",
    "convivial_v1",
)

_LENSES = (
    "default_unanchored_v1",
    "grc_logos_v1",
    "he_logos_v1",
)

_PROMPTS = (
    "What is knowledge?",
    "What is truth?",
)

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
    _say("=" * 76)
    _say("  CORE Orthogonality Tour — register × anchor-lens × prompts")
    _say("=" * 76)
    _say(
        "  Walks the full 3 × 3 × 2 matrix (18 cells) and asserts:\n"
        "    A) varying register inside a fixed lens keeps trace_hash CONSTANT\n"
        "    B) varying lens   inside a fixed register moves trace_hash where\n"
        "       the lens engages (DISTINCT from unanchored baseline)\n"
        "    C) convivial register attaches discourse markers\n"
        "    D) engaged lens emits [lens(<id>):<mode>] annotations\n"
        "    E) no substrate glyphs (Greek/Hebrew/…) leak into surfaces\n"
        "\n"
        "  Together these pin orthogonality under composition — register and\n"
        "  anchor-lens never interfere even when both flags are set."
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


def _run_one_cell(register_id: str, lens_id: str, prompt: str) -> dict[str, Any]:
    runtime = ChatRuntime(config=RuntimeConfig(
        register_pack_id=register_id,
        anchor_lens_id=lens_id,
    ))
    pipeline = CognitiveTurnPipeline(runtime=runtime)
    result = pipeline.run(prompt)
    turn_event = runtime.turn_log[-1]
    return {
        "prompt": prompt,
        "register_id": register_id,
        "lens_id": lens_id,
        "surface": turn_event.surface,
        "trace_hash": result.trace_hash,
        "grounding_source": getattr(turn_event, "grounding_source", ""),
        "register_variant_id": getattr(turn_event, "register_variant_id", ""),
        "anchor_lens_id": getattr(turn_event, "anchor_lens_id", ""),
        "anchor_lens_mode_label": getattr(turn_event, "anchor_lens_mode_label", ""),
    }


def _build_case_runner() -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Warm all register/lens pack combinations once, then score cases."""
    for register_id in _REGISTERS:
        for lens_id in _LENSES:
            ChatRuntime(config=RuntimeConfig(
                register_pack_id=register_id,
                anchor_lens_id=lens_id,
            ))

    def _run(case: dict[str, Any]) -> dict[str, Any]:
        register_id = case["register_id"]
        lens_id = case["lens_id"]
        prompt = case["prompt"]
        runtime = ChatRuntime(config=RuntimeConfig(
            register_pack_id=register_id,
            anchor_lens_id=lens_id,
        ))
        pipeline = CognitiveTurnPipeline(runtime=runtime)
        result = pipeline.run(prompt)
        turn_event = runtime.turn_log[-1]
        return {
            "prompt": prompt,
            "register_id": register_id,
            "lens_id": lens_id,
            "surface": turn_event.surface,
            "trace_hash": result.trace_hash,
            "grounding_source": getattr(turn_event, "grounding_source", ""),
            "register_variant_id": getattr(turn_event, "register_variant_id", ""),
            "anchor_lens_id": getattr(turn_event, "anchor_lens_id", ""),
            "anchor_lens_mode_label": getattr(turn_event, "anchor_lens_mode_label", ""),
        }

    return _run


def _cells_by(
    cells: list[dict[str, Any]],
    *,
    register_id: str | None = None,
    lens_id: str | None = None,
    prompt: str | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in cells:
        if register_id is not None and c["register_id"] != register_id:
            continue
        if lens_id is not None and c["lens_id"] != lens_id:
            continue
        if prompt is not None and c["prompt"] != prompt:
            continue
        out.append(c)
    return out


def _check_claims(cells: list[dict[str, Any]]) -> dict[str, Any]:
    glyph_violations: list[str] = []
    register_invariant_failures: list[str] = []
    lens_distinctness_failures: list[str] = []
    convivial_marker_failures: list[str] = []
    lens_annotation_failures: list[str] = []

    # Claim E — glyph leak across whole grid.
    for c in cells:
        for pos, ch, block in _substrate_glyph_violations(c["surface"]):
            glyph_violations.append(
                f"register={c['register_id']!r} lens={c['lens_id']!r} "
                f"prompt={c['prompt']!r}: substrate glyph {ch!r} "
                f"(block={block}) at pos {pos}"
            )

    # Claim A — register-tour seam inside every (lens, prompt) cell.
    for lens_id in _LENSES:
        for prompt in _PROMPTS:
            triple = _cells_by(cells, lens_id=lens_id, prompt=prompt)
            hashes = {c["trace_hash"] for c in triple}
            if len(hashes) != 1:
                register_invariant_failures.append(
                    f"lens={lens_id!r} prompt={prompt!r}: "
                    f"trace_hashes varied across registers: "
                    f"{sorted(hashes)}"
                )

    # Claim B — lens distinctness inside every (register, prompt) cell.
    # Engaged lenses' trace_hashes must differ from the unanchored
    # baseline at the same (register, prompt).
    for register_id in _REGISTERS:
        for prompt in _PROMPTS:
            unanchored_cell = _cells_by(
                cells,
                register_id=register_id,
                lens_id="default_unanchored_v1",
                prompt=prompt,
            )[0]
            for lens_id in _LENSES:
                if lens_id == "default_unanchored_v1":
                    continue
                cell = _cells_by(
                    cells,
                    register_id=register_id,
                    lens_id=lens_id,
                    prompt=prompt,
                )[0]
                if cell["anchor_lens_mode_label"]:
                    # Engaged → require trace_hash divergence.
                    if cell["trace_hash"] == unanchored_cell["trace_hash"]:
                        lens_distinctness_failures.append(
                            f"register={register_id!r} lens={lens_id!r} "
                            f"prompt={prompt!r}: engaged lens did not "
                            f"move trace_hash (still "
                            f"{cell['trace_hash'][:12]}...)"
                        )

    # Claim C — convivial register attaches discourse markers.
    for c in _cells_by(cells, register_id="convivial_v1"):
        if c["surface"] and not c["register_variant_id"]:
            convivial_marker_failures.append(
                f"convivial cell lens={c['lens_id']!r} "
                f"prompt={c['prompt']!r} has empty register_variant_id "
                f"despite non-empty surface"
            )

    # Claim D — engaged lens emits annotation + non-empty mode_label.
    for c in cells:
        if c["anchor_lens_mode_label"]:
            expected = f"[lens({c['lens_id']}):{c['anchor_lens_mode_label']}]"
            if expected not in c["surface"]:
                lens_annotation_failures.append(
                    f"register={c['register_id']!r} lens={c['lens_id']!r} "
                    f"prompt={c['prompt']!r}: mode_label="
                    f"{c['anchor_lens_mode_label']!r} but surface lacks "
                    f"annotation {expected!r}.  Surface: {c['surface']!r}"
                )

    return {
        "inner_register_invariant_within_lens": not register_invariant_failures,
        "outer_lens_distinctness_within_register": not lens_distinctness_failures,
        "surface_carries_register_marker_under_convivial": (
            not convivial_marker_failures
        ),
        "surface_carries_lens_annotation_when_engaged": not lens_annotation_failures,
        "no_substrate_glyph_leak_across_grid": not glyph_violations,
        "register_invariant_failures": register_invariant_failures,
        "lens_distinctness_failures": lens_distinctness_failures,
        "convivial_marker_failures": convivial_marker_failures,
        "lens_annotation_failures": lens_annotation_failures,
        "glyph_violations": glyph_violations,
    }


def _print_grid(cells: list[dict[str, Any]]) -> None:
    for prompt in _PROMPTS:
        _say(f"  Prompt: {prompt!r}")
        for register_id in _REGISTERS:
            _say(f"    register = {register_id}")
            for lens_id in _LENSES:
                cell = _cells_by(
                    cells, register_id=register_id, lens_id=lens_id,
                    prompt=prompt,
                )[0]
                mode = cell["anchor_lens_mode_label"] or "-"
                variant = cell["register_variant_id"] or "-"
                _say(
                    f"      lens={lens_id:24s} "
                    f"trace={cell['trace_hash'][:12]}…  "
                    f"mode={mode:18s} variant={variant}"
                )
        _say()


def run_tour(*, emit_json: bool = False, workers: int | None = None) -> dict[str, Any]:
    """Run the orthogonality tour and return a structured report."""
    global _VERBOSE
    _VERBOSE = not emit_json

    if not emit_json:
        _print_header()
        _say(f"  Building grid: {len(_REGISTERS)} registers × "
             f"{len(_LENSES)} lenses × {len(_PROMPTS)} prompts = "
             f"{len(_REGISTERS) * len(_LENSES) * len(_PROMPTS)} cells")
        _say()

    cases = [
        {"register_id": register_id, "lens_id": lens_id, "prompt": prompt}
        for register_id in _REGISTERS
        for lens_id in _LENSES
        for prompt in _PROMPTS
    ]
    effective_workers = normalize_workers(workers if workers is not None else 4, len(cases))
    if not emit_json:
        _say(f"  workers: {effective_workers}")
    cells = run_cases_parallel(
        cases,
        partial(_build_case_runner),
        n_workers=effective_workers,
    )

    if not emit_json:
        _say("-" * 76)
        _say("  Composition grid")
        _say("-" * 76)
        _print_grid(cells)

    claims = _check_claims(cells)
    all_supported = all(
        claims[k] for k in (
            "inner_register_invariant_within_lens",
            "outer_lens_distinctness_within_register",
            "surface_carries_register_marker_under_convivial",
            "surface_carries_lens_annotation_when_engaged",
            "no_substrate_glyph_leak_across_grid",
        )
    )

    if not emit_json:
        _say("=" * 76)
        _say("  Orthogonality claims (composition gate)")
        _say("=" * 76)
        for label, key in (
            ("A) inner_register_invariant_within_lens     ",
             "inner_register_invariant_within_lens"),
            ("B) outer_lens_distinctness_within_register  ",
             "outer_lens_distinctness_within_register"),
            ("C) surface_carries_register_marker_convivial",
             "surface_carries_register_marker_under_convivial"),
            ("D) surface_carries_lens_annotation_engaged  ",
             "surface_carries_lens_annotation_when_engaged"),
            ("E) no_substrate_glyph_leak_across_grid       ",
             "no_substrate_glyph_leak_across_grid"),
        ):
            _say(f"  {label}: {claims[key]}")
        _say()
        _say(f"  all_claims_supported : {all_supported}")
        _say()

    return {
        "registers": list(_REGISTERS),
        "lenses": list(_LENSES),
        "prompts": list(_PROMPTS),
        "cells": cells,
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
