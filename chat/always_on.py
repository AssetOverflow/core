"""The L10 always-on heartbeat — the loop that makes the life CONTINUOUS.

CORE is meant to be ONE continuous life (listen -> comprehend -> recall -> think ->
articulate -> learn -> replay), not "many lives sharing a checkpoint." Three pieces of
that spine are already built:

  * the turn loop (``chat/runtime.py``) handles user turns;
  * Shape B+ persistence makes a reboot resume the SAME life (field/vault/anchor/graph
    restored bit-exactly, ``config.persist_session_state``);
  * ``ChatRuntime.idle_tick`` advances continuous learning *between* turns
    (proposal-only + sound session-memory consolidation).

What was missing is a runtime that holds the engine alive and learning over uptime with
no user turn — the T-experience direction. This module is the reusable **heartbeat
loop**: ``run_continuous`` ticks ``idle_tick`` on a cadence so the engine lives and
learns even when no one is talking to it, READS (never repairs) the closure invariant as
evidence each beat, and persists so the life survives interruption and resumes as the
SAME life. It is the core a daemon would call — the production daemon shell (a real
wall-clock cadence, signal handling, a ``core always-on`` CLI entry) is a thin follow-up
on top of this loop, not built here.

Safety by composition, no new authority:
  * ``idle_tick`` is proposal-only (HITL ratification untouched) + sound, proof-gated
    session-memory consolidation — the heartbeat introduces no unreviewed mutation.
  * closure (``versor_condition < 1e-6``) holds BY CONSTRUCTION (the sanctioned session
    anchoring; L10 Decision-0 ruling), so the heartbeat only *reads* ``versor_condition``
    as telemetry — never a hot-path repair or watchdog (CLAUDE.md no-hot-path-repair).
  * the engine's content identity is invariant within a life (config-derived, not
    lived-state); cross-reboot "same life" enforcement is owned by the ``ChatRuntime``
    load guard (``IdentityContinuityError`` when the stamped checkpoint identity differs
    from the recomputed one) — this loop does not re-implement it.

See the L10 continuity soak (``evals/l10_continuity``) for the turn-loop half; this is
the idle/heartbeat half.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from algebra.versor import versor_condition
from core.engine_identity import engine_identity_for_config
from engine_state import get_git_revision

# The name of the persisted lived-life artifact (one per always-on run) in the
# engine-state dir, read-only, for the workbench Lived Life surface.
LIVED_LIFE_FILENAME = "lived_life.json"
LIVED_LIFE_SCHEMA_VERSION = "lived_life_v1"

# The non-negotiable field invariant (CLAUDE.md). The heartbeat READS this as evidence;
# it never repairs to keep it true — closure is owned by ``algebra/versor.py``.
CLOSURE_CEILING = 1e-6


@dataclass(frozen=True, slots=True)
class HeartbeatRecord:
    """Per-beat evidence of one continuous-life heartbeat (read-only telemetry)."""

    tick: int
    versor_condition: float | None  # closure of the live field; None before any turn built one
    field_valid: bool  # versor_condition < CLOSURE_CEILING (vacuously True when no field yet)
    facts_consolidated: int  # Step-D facts learned this beat (continuous learning)
    proposals_created: int  # reviewable proposals emitted this beat (proposal-only)
    pending_proposals: int
    did_work: bool


@dataclass(frozen=True, slots=True)
class AlwaysOnReport:
    """The ordered evidence of one always-on run — the soak subject.

    ``identity`` is the engine's content identity for the run (honest telemetry — it is
    invariant within a life BY CONSTRUCTION, config-derived, so it is recorded once and
    is NOT a continuity proof; cross-reboot "same life" is enforced by the ``ChatRuntime``
    load guard). ``closure_observed`` says whether any beat actually observed a field, so
    a consumer can distinguish "closure held over N observations" from "no field ever
    existed" (``closure_held`` is vacuously True with zero observations).
    ``final_checkpoint_ok`` surfaces whether the exit checkpoint persisted (never silently
    swallowed)."""

    records: tuple[HeartbeatRecord, ...]
    identity: str
    closure_observed: bool
    closure_held: bool  # every OBSERVED versor_condition < CLOSURE_CEILING
    final_checkpoint_ok: bool
    total_facts_consolidated: int
    total_proposals_created: int

    @property
    def heartbeats(self) -> int:
        return len(self.records)


def serialize_report(report: AlwaysOnReport) -> dict[str, Any]:
    """Deterministic, JSON-able projection of an always-on run — the persisted lived-life
    evidence the workbench reads."""
    return {
        "schema_version": LIVED_LIFE_SCHEMA_VERSION,
        "identity": report.identity,
        "heartbeats": report.heartbeats,
        "closure_ceiling": CLOSURE_CEILING,
        "closure_observed": report.closure_observed,
        "closure_held": report.closure_held,
        "final_checkpoint_ok": report.final_checkpoint_ok,
        "total_facts_consolidated": report.total_facts_consolidated,
        "total_proposals_created": report.total_proposals_created,
        "records": [
            {
                "tick": r.tick,
                "versor_condition": r.versor_condition,
                "field_valid": r.field_valid,
                "facts_consolidated": r.facts_consolidated,
                "proposals_created": r.proposals_created,
                "pending_proposals": r.pending_proposals,
                "did_work": r.did_work,
            }
            for r in report.records
        ],
    }


def write_lived_life(report: AlwaysOnReport, path: Path) -> None:
    """Persist the lived-life evidence deterministically (sorted keys) so the workbench can
    read it as a read-only artifact. Overwrites — the artifact is the latest always-on run
    (a cumulative whole-life log is a future enhancement)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(serialize_report(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _live_versor_condition(runtime) -> float | None:
    """Read the closure of the runtime's live field, or None if no turn built one yet.

    Pure telemetry — never mutates or repairs the field."""
    context = getattr(runtime, "_context", None)
    state = getattr(context, "state", None) if context is not None else None
    if state is None:
        return None
    return float(versor_condition(state.F))


def run_continuous(
    runtime,
    *,
    heartbeats: int,
    sleep_seconds: float = 0.0,
    on_heartbeat: Callable[[HeartbeatRecord], None] | None = None,
    stop: Callable[[], bool] | None = None,
    report_path: Path | None = None,
) -> AlwaysOnReport:
    """Run the always-on heartbeat for up to ``heartbeats`` beats.

    Each beat: advance continuous learning (``idle_tick``), then record the closure +
    learning evidence. ``idle_tick`` self-checkpoints on real work; this loop also
    checkpoints once at exit, so the life survives interruption — the next ``ChatRuntime``
    over the same engine-state dir resumes the SAME life (with Shape B+ persistence on,
    and the load-time identity guard enforcing it).

    Bounded for falsifiable soaks; a daemon passes a large ``heartbeats`` + a ``stop``
    predicate (and a real ``sleep_seconds`` cadence). ``stop`` is checked BEFORE each
    beat so a clean shutdown still persists the final state.

    When ``report_path`` is given, the run's lived-life evidence is persisted there after
    the loop exits — point it at ``<engine_state>/lived_life.json`` so the workbench Lived
    Life surface reads the continuous life. A clean ``stop`` still writes the full report
    (the report captures everything accumulated up to the stop). On a crash the engine
    state is still checkpointed in ``finally`` for recovery, but the workbench report is
    best-effort and simply not refreshed — the surface keeps the last good run.
    """
    if heartbeats < 0:
        raise ValueError("heartbeats must be >= 0")

    git_revision = get_git_revision()
    identity = engine_identity_for_config(runtime.config, git_revision)
    records: list[HeartbeatRecord] = []
    final_checkpoint_ok = True
    try:
        for tick in range(heartbeats):
            if stop is not None and stop():
                break
            result = runtime.idle_tick()
            vc = _live_versor_condition(runtime)
            did_work = (
                result.facts_consolidated > 0
                or result.proposals_created > 0
                or result.candidates_contemplated > 0
            )
            record = HeartbeatRecord(
                tick=tick,
                versor_condition=vc,
                field_valid=(vc is None or vc < CLOSURE_CEILING),
                facts_consolidated=result.facts_consolidated,
                proposals_created=result.proposals_created,
                pending_proposals=result.pending_proposals,
                did_work=did_work,
            )
            records.append(record)
            if on_heartbeat is not None:
                on_heartbeat(record)
            if sleep_seconds:
                time.sleep(sleep_seconds)
    finally:
        # Final checkpoint even on a mid-beat interruption — the life persists and resumes
        # as the SAME life. Best-effort so a checkpoint failure cannot mask the original
        # error, but the outcome is SURFACED (final_checkpoint_ok), never silently swallowed.
        try:
            runtime.checkpoint_engine_state()
        except Exception:  # noqa: BLE001 — persistence is best-effort at the boundary
            final_checkpoint_ok = False

    observed = [r.versor_condition for r in records if r.versor_condition is not None]
    report = AlwaysOnReport(
        records=tuple(records),
        identity=identity,
        closure_observed=bool(observed),
        closure_held=all(vc < CLOSURE_CEILING for vc in observed),
        final_checkpoint_ok=final_checkpoint_ok,
        total_facts_consolidated=sum(r.facts_consolidated for r in records),
        total_proposals_created=sum(r.proposals_created for r in records),
    )
    if report_path is not None:
        write_lived_life(report, report_path)
    return report
