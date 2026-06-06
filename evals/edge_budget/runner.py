"""Edge-deployment budget lane — deterministic per-turn persistence cost.

Runs the REAL turn loop with ``persist_session_state=True`` and measures the BYTES the
Shape B+ checkpoint writes each turn (``session_state.json``). The metric is
DETERMINISTIC (snapshot bytes, not wall-clock latency, which is machine-dependent and
would make an edge gate flaky in CI) — so it is a falsifiable handle, not a vibe.

Today persistence is O(n) per turn: ``save_session_state`` re-serializes the FULL
snapshot every turn, so per-turn bytes grow linearly with the accumulated life (the
vault). This lane makes that cliff visible and gated; it is the falsification lane for
the incremental/append-only persistence fix (O(Δ)/turn → bounded per-turn bytes).

Reuses the L10 continuity corpus (``prompt_at``) — the same deterministic, always-in-
vocabulary turn ring the lived-spine soak uses — so the cost series is reproducible.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from evals.l10_continuity.corpus import prompt_at

#: Default soak length — enough turns that an O(n)-per-turn implementation visibly
#: breaches the bounded edge budget, kept small enough to stay fast in CI.
DEFAULT_TURNS = 20

#: The edge budget: the most a constrained device (clinic/disaster-center box) can
#: afford to write to durable storage PER TURN, for a life that runs indefinitely.
#: A bounded (O(Δ)) implementation writes only the turn's delta (~a few KB); 16 KiB is
#: generous for that. Today's O(n) snapshot blows through it within a handful of turns.
EDGE_PER_TURN_CEILING_BYTES = 16 * 1024

#: Regression guard (passes today): current max per-turn (~86 KiB at 20 turns) + head-
#: room. Catches a change that makes the cliff materially WORSE before the fix lands.
REGRESSION_PER_TURN_CEILING_BYTES = 160 * 1024
REGRESSION_TOTAL_CEILING_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class TurnCost:
    turn_index: int
    vault_size: int
    checkpoint_bytes: int


def measure(n_turns: int = DEFAULT_TURNS, engine_state_dir: Path | None = None) -> list[TurnCost]:
    """Run the real turn loop and capture the per-turn checkpoint byte cost.

    If ``engine_state_dir`` is None a TemporaryDirectory is used (and cleaned up).
    """
    if engine_state_dir is not None:
        return _measure_into(n_turns, engine_state_dir)
    with tempfile.TemporaryDirectory() as tmp:
        return _measure_into(n_turns, Path(tmp))


def _measure_into(n_turns: int, engine_state_dir: Path) -> list[TurnCost]:
    config = replace(RuntimeConfig(), persist_session_state=True)
    runtime = ChatRuntime(config=config, engine_state_path=engine_state_dir)
    pipe = CognitiveTurnPipeline(runtime=runtime)
    session_file = engine_state_dir / "session_state.json"

    costs: list[TurnCost] = []
    for i in range(n_turns):
        pipe.run(prompt_at(i))
        size = session_file.stat().st_size if session_file.exists() else 0
        costs.append(TurnCost(i, len(runtime._context.vault), size))
    return costs


def run(n_turns: int = DEFAULT_TURNS) -> dict[str, Any]:
    """Measure and summarize the per-turn persistence cost (JSON-safe report)."""
    costs = measure(n_turns)
    per_turn = [c.checkpoint_bytes for c in costs]
    first = per_turn[0] if per_turn else 0
    return {
        "n_turns": n_turns,
        "per_turn_bytes": per_turn,
        "vault_sizes": [c.vault_size for c in costs],
        "first_per_turn_bytes": first,
        "final_per_turn_bytes": per_turn[-1] if per_turn else 0,
        "max_per_turn_bytes": max(per_turn) if per_turn else 0,
        "total_bytes_written": sum(per_turn),
        "growth_ratio": round(per_turn[-1] / first, 3) if first else 0.0,
        "edge_per_turn_ceiling_bytes": EDGE_PER_TURN_CEILING_BYTES,
        "edge_budget_met": (max(per_turn) if per_turn else 0) <= EDGE_PER_TURN_CEILING_BYTES,
    }
