"""C1/C2 holdout cluster.

Hybrid gate after C2:

* Synthetic illegal candidates are checked directly against
  ``generate.realizer_guard.check_surface`` so the guard-firing
  invariant remains pinned after upstream C2 normalization fixes the
  runtime prompts.
* The former runtime bug prompts are run through ``CognitiveTurnPipeline``
  and must now produce accepted propositional surfaces.

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
from generate.realizer_guard import check_surface


_PRIMING_PROMPTS: tuple[str, ...] = (
    "What is light?",
    "Define knowledge.",
    "What is truth?",
)


_SYNTHETIC_ILLEGAL_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("Right does not thought.", "R2_aux_neg_requires_verb"),
    ("Light is not reveal.", "R3_be_neg_requires_predicate"),
)


_HOLDOUT_PROMPTS: tuple[str, ...] = (
    "Light reveals truth, right?",
    "Light reveals truth, no?",
    "Light reveals truth, yes?",
    "Knowledge supports truth, right?",
    "Light grounds truth, right?",
    "Light supports truth, right?",
)


def _build_runtime() -> ChatRuntime:
    """Fresh runtime with neutral register and unanchored lens —
    the bug reproduces on the truth path regardless of register
    or lens, so we pick the simplest combination."""
    return ChatRuntime(config=RuntimeConfig(
        register_pack_id="default_neutral_v1",
    ))


def _run_runtime_one(prompt: str) -> dict[str, Any]:
    runtime = _build_runtime()
    pipeline = CognitiveTurnPipeline(runtime=runtime)
    for primer in _PRIMING_PROMPTS:
        pipeline.run(primer)
    pipeline.run(prompt)
    turn_event = runtime.turn_log[-1]
    status = getattr(turn_event, "realizer_guard_status", "")
    rule = getattr(turn_event, "realizer_guard_rule", "")
    surface = turn_event.surface
    grounding_source = getattr(turn_event, "grounding_source", "")
    accepted = status == "ok"
    proposition_surface = bool(surface) and "pack-grounded" in surface and grounding_source == "pack"
    return {
        "prompt": prompt,
        "realizer_guard_status": status,
        "realizer_guard_rule": rule,
        "surface": surface,
        "grounding_source": grounding_source,
        "accepted": accepted,
        "proposition_surface": proposition_surface,
        "cell_supported": accepted and rule == "" and proposition_surface,
    }


def _run_synthetic_one(candidate: str, expected_rule: str) -> dict[str, Any]:
    runtime = _build_runtime()
    verdict = check_surface(candidate, pos_lookup=runtime._pos_by_surface.get)
    return {
        "candidate": candidate,
        "expected_rule": expected_rule,
        "realizer_guard_status": verdict.status,
        "realizer_guard_rule": verdict.rule_id,
        "cell_supported": (
            verdict.status == "rejected"
            and verdict.rule_id == expected_rule
        ),
    }


def run_holdout(*, emit_json: bool = False) -> dict[str, Any]:
    synthetic_cells = [
        _run_synthetic_one(candidate, rule)
        for candidate, rule in _SYNTHETIC_ILLEGAL_CANDIDATES
    ]
    runtime_cells = [_run_runtime_one(p) for p in _HOLDOUT_PROMPTS]
    failures = [
        c for c in (*synthetic_cells, *runtime_cells)
        if not c["cell_supported"]
    ]
    all_supported = not failures

    if not emit_json:
        print()
        print("=" * 76)
        print("  ADR-0075/0076 (C1/C2) — hybrid guard + confirmation cluster")
        print("=" * 76)
        print(f"  Priming sequence: {list(_PRIMING_PROMPTS)}")
        print(f"  Synthetic illegal candidates : {len(_SYNTHETIC_ILLEGAL_CANDIDATES)}")
        print(f"  Runtime confirmation prompts : {len(_HOLDOUT_PROMPTS)}")
        print()
        for c in synthetic_cells:
            mark = "+" if c["cell_supported"] else "X"
            print(f"  {mark} synthetic {c['candidate']!r}")
            print(f"     guard_status         : {c['realizer_guard_status']}")
            print(f"     guard_rule           : {c['realizer_guard_rule']}")
            print()
        for c in runtime_cells:
            mark = "+" if c["cell_supported"] else "X"
            print(f"  {mark} runtime {c['prompt']!r}")
            print(f"     guard_status         : {c['realizer_guard_status']}")
            print(f"     guard_rule           : {c['realizer_guard_rule']}")
            print(f"     surface              : {c['surface']!r}")
            print(f"     grounding_source     : {c['grounding_source']}")
            print()
        print(f"  all_claims_supported : {all_supported}")
        print()

    return {
        "priming": list(_PRIMING_PROMPTS),
        "synthetic_illegal_candidates": [c for c, _ in _SYNTHETIC_ILLEGAL_CANDIDATES],
        "holdout_prompts": list(_HOLDOUT_PROMPTS),
        "synthetic_cells": synthetic_cells,
        "runtime_cells": runtime_cells,
        "cells": [*synthetic_cells, *runtime_cells],
        "failures": failures,
        "all_claims_supported": all_supported,
    }


if __name__ == "__main__":  # pragma: no cover
    emit_json = "--json" in sys.argv
    report = run_holdout(emit_json=emit_json)
    if emit_json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    sys.exit(0 if report["all_claims_supported"] else 1)
