"""Per-tick idle backpressure telemetry — observational leaf.

Models the ``idle_tick`` learning flywheel's backlog depth, inflow vs drain,
and proximity to the ADR-0161 cap so pressure is visible *before* the cap
starts refusing.  This module is **read-only** — it never gates, refuses, or
alters the served surface or ``trace_hash``.  The ADR-0161 cap and its
``queue_full`` control logic live in ``teaching.proposals``; this leaf only
observes.

The structure mirrors ``core.cognition.leeway``: a frozen dataclass +
a pure builder function that derives all secondary fields from the counts
``idle_tick`` already computes, with no new runtime state.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_DEFAULT_PENDING_CAP: int = 256  # mirrors teaching.proposals.DEFAULT_PENDING_CAP


@dataclass(frozen=True, slots=True)
class BackpressureRecord:
    """Observational telemetry for one ``idle_tick`` run.

    All fields are counts or derived booleans — no gating logic here.

    ``headroom`` is ``max(0, cap - pending_proposals)``; zero means the cap
    is full and the next proposal creation attempt will be refused by
    ADR-0161.  ``at_fixed_point`` is True when the candidate backlog is
    empty AND no proposals were created this tick (the learning flywheel
    has nothing to drain).
    """

    pending_proposals: int       # proposals awaiting HITL ratification after this tick
    candidate_backlog: int       # discovery candidates waiting to be contemplated
    cap: int                     # ADR-0161 cap (CORE_HITL_PENDING_CAP or 256)
    headroom: int                # cap - pending_proposals (≥0; 0 = cap is full)
    contemplated_this_tick: int  # candidates contemplated during this tick
    created_this_tick: int       # proposals created during this tick
    at_fixed_point: bool         # backlog empty AND nothing created → flywheel idle
    did_work: bool               # True when the tick advanced at least one pass


def _resolve_cap() -> int:
    """Resolve the ADR-0161 pending cap — env-overridable, default 256."""
    env_val = os.environ.get("CORE_HITL_PENDING_CAP")
    if env_val is not None:
        try:
            return int(env_val)
        except ValueError:
            pass
    return _DEFAULT_PENDING_CAP


def build_backpressure_record(
    *,
    pending_proposals: int,
    candidate_backlog: int,
    contemplated_this_tick: int,
    created_this_tick: int,
    did_work: bool,
) -> BackpressureRecord:
    """Build the idle-tick backpressure telemetry record.

    All inputs are counts already computed by ``idle_tick``; this function
    only resolves the cap and derives ``headroom`` and ``at_fixed_point``.
    """
    cap = _resolve_cap()
    headroom = max(0, cap - pending_proposals)
    at_fixed_point = candidate_backlog == 0 and created_this_tick == 0
    return BackpressureRecord(
        pending_proposals=pending_proposals,
        candidate_backlog=candidate_backlog,
        cap=cap,
        headroom=headroom,
        contemplated_this_tick=contemplated_this_tick,
        created_this_tick=created_this_tick,
        at_fixed_point=at_fixed_point,
        did_work=did_work,
    )
