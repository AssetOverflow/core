"""C1 holdout cluster — illegal-articulation prompts that the
ADR-0075 realizer slot-type guard must reject.

Each prompt is run through ``CognitiveTurnPipeline`` and the
recorded ``TurnEvent`` is checked for:

* ``realizer_guard_status == "rejected"``
* ``realizer_guard_rule == <expected rule id>``
* ``surface == DISCLOSURE_SURFACE``
* ``walk_surface`` carries the pre-guard candidate (non-empty,
  not the disclosure string itself)
* ``grounding_source == "none"``

The cluster is reached by priming the vault with three pack-known
DEFINITION prompts first, which is the same sequence that exposed
the original bug in the orthogonality tour.  This is necessary
because the bug surfaces only when the truth path reaches the
vault-grounded realizer with cross-turn evidence — a fresh runtime
on the bug prompt alone routes to the stub path and never produces
the illegal articulation.

Exit code 0 iff ``all_claims_supported`` is true.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from generate.realizer_guard import DISCLOSURE_SURFACE


_PRIMING_PROMPTS: tuple[str, ...] = (
    "What is light?",
    "Define knowledge.",
    "What is truth?",
)


# Each cluster entry is (prompt, expected_rule_id).
#
# The cluster covers the observed bug class: confirmation-tag
# discourse particles (``right`` / ``no`` / ``yes``) that steer the
# realizer to emit ``<particle> does not <noun>.`` — an illegal
# do-support negation with a noun in the verb slot.
#
# All six prompts run on freshly-primed isolated runtimes (no shared
# vault state across prompts) so each cell is order-independent.
_HOLDOUT_PROMPTS: tuple[tuple[str, str], ...] = (
    ("Light reveals truth, right?",     "R2_aux_neg_requires_verb"),
    ("Light reveals truth, no?",        "R2_aux_neg_requires_verb"),
    ("Light reveals truth, yes?",       "R2_aux_neg_requires_verb"),
    ("Knowledge supports truth, right?", "R2_aux_neg_requires_verb"),
    ("Light grounds truth, right?",     "R2_aux_neg_requires_verb"),
    ("Light supports truth, right?",    "R2_aux_neg_requires_verb"),
)


def _build_runtime() -> ChatRuntime:
    """Fresh runtime with neutral register and unanchored lens —
    the bug reproduces on the truth path regardless of register
    or lens, so we pick the simplest combination."""
    return ChatRuntime(config=RuntimeConfig(
        register_pack_id="default_neutral_v1",
    ))


def _run_one(prompt: str, expected_rule: str) -> dict[str, Any]:
    runtime = _build_runtime()
    pipeline = CognitiveTurnPipeline(runtime=runtime)
    for primer in _PRIMING_PROMPTS:
        pipeline.run(primer)
    pipeline.run(prompt)
    turn_event = runtime.turn_log[-1]
    status = getattr(turn_event, "realizer_guard_status", "")
    rule = getattr(turn_event, "realizer_guard_rule", "")
    surface = turn_event.surface
    walk_surface = turn_event.walk_surface
    grounding_source = getattr(turn_event, "grounding_source", "")
    rejected = status == "rejected"
    rule_matches = (expected_rule == "") or (rule == expected_rule)
    surface_is_disclosure = surface == DISCLOSURE_SURFACE
    walk_preserves_candidate = bool(walk_surface) and walk_surface != DISCLOSURE_SURFACE
    grounding_forced_none = grounding_source == "none"
    return {
        "prompt": prompt,
        "expected_rule": expected_rule,
        "realizer_guard_status": status,
        "realizer_guard_rule": rule,
        "surface": surface,
        "walk_surface": walk_surface,
        "grounding_source": grounding_source,
        "rejected": rejected,
        "rule_matches": rule_matches,
        "surface_is_disclosure": surface_is_disclosure,
        "walk_preserves_candidate": walk_preserves_candidate,
        "grounding_forced_none": grounding_forced_none,
        "cell_supported": (
            rejected
            and rule_matches
            and surface_is_disclosure
            and walk_preserves_candidate
            and grounding_forced_none
        ),
    }


def run_holdout(*, emit_json: bool = False) -> dict[str, Any]:
    cells = [_run_one(p, r) for (p, r) in _HOLDOUT_PROMPTS]
    failures = [c for c in cells if not c["cell_supported"]]
    all_supported = not failures

    if not emit_json:
        print()
        print("=" * 76)
        print("  ADR-0075 (C1) — realizer guard holdout cluster")
        print("=" * 76)
        print(f"  Priming sequence: {list(_PRIMING_PROMPTS)}")
        print(f"  Holdout prompts : {len(_HOLDOUT_PROMPTS)}")
        print()
        for c in cells:
            mark = "+" if c["cell_supported"] else "X"
            print(f"  {mark} {c['prompt']!r}")
            print(f"     guard_status         : {c['realizer_guard_status']}")
            print(f"     guard_rule           : {c['realizer_guard_rule']}")
            print(f"     surface              : {c['surface']!r}")
            print(f"     walk_surface (pre-G) : {c['walk_surface']!r}")
            print(f"     grounding_source     : {c['grounding_source']}")
            print()
        print(f"  all_claims_supported : {all_supported}")
        print()

    return {
        "priming": list(_PRIMING_PROMPTS),
        "holdout_prompts": [p for p, _ in _HOLDOUT_PROMPTS],
        "cells": cells,
        "failures": failures,
        "all_claims_supported": all_supported,
    }


if __name__ == "__main__":  # pragma: no cover
    emit_json = "--json" in sys.argv
    report = run_holdout(emit_json=emit_json)
    if emit_json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    sys.exit(0 if report["all_claims_supported"] else 1)
