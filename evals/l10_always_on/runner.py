"""The L10 always-on heartbeat soak runner — drives the REAL idle loop over N beats.

It seeds a continuous life (a held self + a cognitive turn to excite the field), then runs
``chat/always_on.run_continuous`` over a fresh ``ChatRuntime`` whose checkpoint lives in a
caller-supplied dir. Optionally it injects a *reboot leg*: at a chosen beat it drops the
live runtime and reconstructs one from the on-disk checkpoint — the always-on lifecycle
("resume as the same life") — under the strict identity guard.

Pure instrumentation: it records per-beat evidence (``versor_condition``, ``field_valid``,
the learning counts, ``did_work``, vault size, boot segment) and returns it. It makes NO
pass/fail judgement (that is ``predicates.py``) and NEVER repairs or normalizes the field
(it reads only what the heartbeat produced — CLAUDE.md no-hot-path-repair).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from chat.always_on import HeartbeatRecord, run_continuous
from chat.always_on_daemon import continuous_life_config
from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from core.engine_identity import IdentityContinuityError, engine_identity_for_config


@dataclass(frozen=True, slots=True)
class BeatRecord:
    """Per-beat evidence captured from the real idle heartbeat (no judgement)."""

    beat_index: int  # global, across reboot segments
    segment_tick: int  # the run_continuous tick within this boot segment
    versor_condition: float | None  # None before any field exists
    field_valid: bool
    facts_consolidated: int
    proposals_created: int
    pending_proposals: int
    did_work: bool
    vault_size: int
    booted_segment: int


@dataclass(frozen=True, slots=True)
class HeartbeatSoakResult:
    """The full ordered evidence of one idle soak run."""

    n_beats: int
    reboot_at: tuple[int, ...]
    records: tuple[BeatRecord, ...]
    identity: str
    # Reboot-leg evidence (only meaningful when reboot_at is non-empty):
    resumed_cleanly: bool  # the reconstruct under the strict identity guard did not raise
    learned_fact_survived: bool | None  # a pre-reboot DERIVED fact is recalled post-reboot

    def observed(self) -> tuple[BeatRecord, ...]:
        return tuple(r for r in self.records if r.versor_condition is not None)

    def post_reboot_records(self) -> tuple[BeatRecord, ...]:
        return tuple(r for r in self.records if r.booted_segment > 0)


def _seed_life(runtime: ChatRuntime) -> None:
    """Seed a consolidatable held self + excite the field so closure is OBSERVED.

    member(socrates, man) + subset(man, mortal) — from which the idle heartbeat DERIVES
    member(socrates, mortal) — plus a real cognitive turn so ``versor_condition`` is
    observable (an idle life never excites its own field)."""
    from core.cognition.pipeline import CognitiveTurnPipeline
    from generate.meaning_graph.reader import comprehend
    from generate.realize import realize_comprehension

    ctx = runtime._context
    realize_comprehension(comprehend("Socrates is a man."), ctx)
    realize_comprehension(comprehend("All men are mortals."), ctx)
    CognitiveTurnPipeline(runtime=runtime).run("Socrates is a man.")


def _mortal_is_stored(runtime: ChatRuntime) -> bool:
    """True iff member(socrates, mortal) is a STORED realized record (recall, not redo)."""
    from generate.realize import recall_realized

    return any(
        f.relation_arguments[1] == "mortal"
        for f in recall_realized(runtime._context, subject="socrates", predicate="member")
    )


def run_heartbeat_soak(
    n_beats: int,
    *,
    engine_state_dir: Path,
    reboot_at: tuple[int, ...] = (),
    config: RuntimeConfig | None = None,
    seed: bool = True,
) -> HeartbeatSoakResult:
    """Run ``n_beats`` idle heartbeats, optionally rebooting at given beat boundaries.

    The config is forced to the continuous-life config (persist + consolidate + strict
    identity) — the daemon's contract. ``reboot_at`` beats split the soak into boot
    segments: before each, the live runtime is dropped and reconstructed from the
    checkpoint (the reboot). A reboot at beat 0 is meaningless and ignored.
    """
    if n_beats < 0:
        raise ValueError(f"n_beats must be non-negative, got {n_beats}")
    config = continuous_life_config(config)
    reboot_set = sorted({i for i in reboot_at if 0 < i < n_beats})
    boundaries = [0, *reboot_set, n_beats]

    runtime = ChatRuntime(config=config, engine_state_path=engine_state_dir)
    if seed:
        _seed_life(runtime)
    identity = engine_identity_for_config(config)
    records: list[BeatRecord] = []
    resumed_cleanly = True
    learned_fact_survived: bool | None = None

    for seg, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
        if seg > 0:
            # The reboot: reconstruct from the prior segment's checkpoint. Under the strict
            # identity guard this RAISES if the checkpoint is a different life.
            try:
                runtime = ChatRuntime(config=config, engine_state_path=engine_state_dir)
            except IdentityContinuityError:
                resumed_cleanly = False
                break
            if learned_fact_survived is None:
                learned_fact_survived = _mortal_is_stored(runtime)

        rt = runtime

        def _capture(record: HeartbeatRecord, *, _seg: int = seg, _rt: ChatRuntime = rt) -> None:
            records.append(
                BeatRecord(
                    beat_index=len(records),
                    segment_tick=record.tick,
                    versor_condition=record.versor_condition,
                    field_valid=record.field_valid,
                    facts_consolidated=record.facts_consolidated,
                    proposals_created=record.proposals_created,
                    pending_proposals=record.pending_proposals,
                    did_work=record.did_work,
                    vault_size=len(_rt._context.vault),
                    booted_segment=_seg,
                )
            )

        run_continuous(rt, heartbeats=end - start, on_heartbeat=_capture)

    return HeartbeatSoakResult(
        n_beats=n_beats,
        reboot_at=tuple(reboot_set),
        records=tuple(records),
        identity=identity,
        resumed_cleanly=resumed_cleanly,
        learned_fact_survived=learned_fact_survived,
    )
