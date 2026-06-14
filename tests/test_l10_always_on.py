"""L10 — the always-on heartbeat: one continuous life that lives + learns when idle
and survives interruption as the SAME life.

These exercise the T-experience heartbeat (``chat/always_on.run_continuous``) directly:
the engine ticks ``idle_tick`` over uptime with no user turn, the closure invariant holds
by construction (read as evidence, never repaired), and a reboot resumes the SAME life
with its accumulated heartbeat learning intact (enforced by the strict identity guard).
Wrong=0 / no-hot-path-repair are preserved by composition — the heartbeat only proposes
(HITL untouched) + consolidates sound session memory.
"""

from __future__ import annotations

from chat.always_on import CLOSURE_CEILING, run_continuous
from chat.runtime import ChatRuntime, RuntimeConfig
from core.cognition.pipeline import CognitiveTurnPipeline
from generate.meaning_graph.reader import comprehend
from generate.realize import realize_comprehension, recall_realized
from session.context import SessionContext

_RESUME_CONFIG = RuntimeConfig(
    persist_session_state=True,  # Shape B+ — the lived field/vault survive reboot
    consolidate_determinations=True,  # Step D — the loop learns from determined facts
    strict_identity_continuity=True,  # a reboot must be the SAME life or refuse (load guard)
)


def _stored_members(ctx: SessionContext, subject: str) -> set[str]:
    """The set of ``b`` for which ``member(subject, b)`` is a STORED realized record
    (recall, not on-the-fly re-derivation)."""
    return {
        f.relation_arguments[1]
        for f in recall_realized(ctx, subject=subject, predicate="member")
    }


def _seed_continuous_life(runtime: ChatRuntime) -> None:
    """Seed a consolidatable held self — member(socrates, man) + subset(man, mortal),
    from which the idle heartbeat DERIVES member(socrates, mortal) — and excite the field
    so closure is observed, not vacuous."""
    ctx = runtime._context
    realize_comprehension(comprehend("Socrates is a man."), ctx)
    realize_comprehension(comprehend("All men are mortals."), ctx)
    # A real cognitive turn excites the field so ``versor_condition`` is observable.
    CognitiveTurnPipeline(runtime=runtime).run("Socrates is a man.")


def test_heartbeat_lives_learns_and_converges(tmp_path) -> None:
    runtime = ChatRuntime(config=_RESUME_CONFIG, engine_state_path=tmp_path / "engine_state")
    _seed_continuous_life(runtime)
    # The derived membership is NOT stored before the heartbeat runs.
    assert "mortal" not in _stored_members(runtime._context, "socrates")

    report = run_continuous(runtime, heartbeats=5)

    assert report.heartbeats == 5
    assert report.final_checkpoint_ok
    assert report.identity  # the life carries a content identity (telemetry)
    # LIVES: closure holds by construction across the uptime, and it is OBSERVED (a real
    # field exists), not vacuously true.
    assert report.closure_observed
    assert report.closure_held
    observed = [r.versor_condition for r in report.records if r.versor_condition is not None]
    assert observed and all(vc < CLOSURE_CEILING for vc in observed)
    # LEARNS while idle: Step-D consolidation derived AND STORED member(socrates, mortal)
    # during the heartbeat (non-vacuous — it was absent before run_continuous).
    assert report.total_facts_consolidated >= 1
    assert "mortal" in _stored_members(runtime._context, "socrates")
    # CONVERGES: a saturated life stops churning — the final beat does no work.
    assert report.records[-1].did_work is False


def test_life_survives_interruption_as_the_same_life(tmp_path) -> None:
    state_dir = tmp_path / "engine_state"
    runtime = ChatRuntime(config=_RESUME_CONFIG, engine_state_path=state_dir)
    _seed_continuous_life(runtime)

    report = run_continuous(runtime, heartbeats=3)
    # The heartbeat's ACCUMULATED learning before the interruption.
    assert report.total_facts_consolidated >= 1
    assert "mortal" in _stored_members(runtime._context, "socrates")

    # Interruption: the live runtime is dropped. The next runtime over the SAME engine-state
    # dir is the reboot. Under strict_identity_continuity, constructing it ENFORCES the
    # same-life identity guard — a clean construction means the stamped checkpoint identity
    # matched the recomputed one (the SAME life, not a new one).
    del runtime
    resumed = ChatRuntime(config=_RESUME_CONFIG, engine_state_path=state_dir)

    # The heartbeat's accumulated learning survived the reboot as a STORED record — not
    # merely re-derivable from the seeds: the consolidated member(socrates, mortal) is
    # recalled directly. (With consolidation off, this would NOT be stored — non-vacuous.)
    assert "mortal" in _stored_members(resumed._context, "socrates")


def test_heartbeat_never_repairs_closure(tmp_path) -> None:
    """The heartbeat READS versor_condition as evidence; it must never repair the field.
    A no-op idle life (nothing to learn) keeps closure stable without any mutation."""
    runtime = ChatRuntime(config=_RESUME_CONFIG, engine_state_path=tmp_path / "engine_state")
    _seed_continuous_life(runtime)
    assert runtime._context.state is not None
    field_before = runtime._context.state.F.copy()

    report = run_continuous(runtime, heartbeats=4)

    # The field is byte-unchanged by the idle heartbeat (no propagation, no repair).
    assert runtime._context.state is not None
    assert (runtime._context.state.F == field_before).all()
    assert report.closure_observed and report.closure_held
