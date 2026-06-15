"""L10 always-on heartbeat soak — the falsifiable long-horizon gate for the IDLE path.

Per predicate, two tests (CLAUDE.md schema-as-proof):
- a ``*_holds`` test that drives the REAL idle heartbeat over a short soak and asserts the
  predicate passes on genuine evidence, and
- a ``*_bites`` test that feeds the predicate mutated evidence and asserts it FAILS.

These soak a seeded continuous life over the idle heartbeat (no user turn). Short N + a tmp
checkpoint dir; NOT in the default smoke suite (a soak — run on demand / nightly). The long
horizon is the ``python -m evals.l10_always_on`` CLI's job.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.l10_always_on.predicates import (
    VERSOR_CEILING,
    evaluate_h1_closure,
    evaluate_h2_bounded_idle,
    evaluate_h3_convergence,
    evaluate_h4_reboot_resume,
)
from evals.l10_always_on.runner import (
    BeatRecord,
    HeartbeatSoakResult,
    run_heartbeat_soak,
)

_SOAK_N = 12  # beat 0 learns the derived fact; beats 1+ converge to rest


# --------------------------------------------------------------------------- #
# Synthetic-evidence helpers (fast; no heartbeat) — used by the *_bites tests.  #
# --------------------------------------------------------------------------- #
def _beat(
    i: int,
    *,
    versor_condition: float | None = 8.2e-13,
    field_valid: bool = True,
    did_work: bool = False,
    vault_size: int = 2,
    segment: int = 0,
) -> BeatRecord:
    return BeatRecord(
        beat_index=i,
        segment_tick=i,
        versor_condition=versor_condition,
        field_valid=field_valid,
        facts_consolidated=1 if did_work else 0,
        proposals_created=0,
        pending_proposals=0,
        did_work=did_work,
        vault_size=vault_size,
        booted_segment=segment,
    )


def _soak(
    records: list[BeatRecord],
    *,
    reboot_at: tuple[int, ...] = (),
    resumed_cleanly: bool = True,
    learned_fact_survived: bool | None = True,
) -> HeartbeatSoakResult:
    return HeartbeatSoakResult(
        n_beats=len(records),
        reboot_at=reboot_at,
        records=tuple(records),
        identity="sha256:soak",
        resumed_cleanly=resumed_cleanly,
        learned_fact_survived=learned_fact_survived,
    )


# --------------------------------------------------------------------------- #
# H1 — closure over idle uptime                                                 #
# --------------------------------------------------------------------------- #
def test_h1_closure_holds_on_real_soak(tmp_path: Path) -> None:
    result = run_heartbeat_soak(_SOAK_N, engine_state_dir=tmp_path / "es")
    outcome = evaluate_h1_closure(result)
    assert outcome.passed, outcome.detail
    assert outcome.metrics["observed_beats"] >= 1  # the field really existed (non-vacuous)
    assert outcome.metrics["worst_versor_condition"] < VERSOR_CEILING


def test_h1_bites_on_breached_versor() -> None:
    bad = _soak([_beat(0), _beat(1, versor_condition=1e-3, field_valid=False), _beat(2)])
    outcome = evaluate_h1_closure(bad)
    assert not outcome.passed
    assert (1, 1e-3) in outcome.metrics["violations"]


def test_h1_bites_on_no_field_observed() -> None:
    # A life whose field never existed must NOT pass H1 vacuously.
    vacuous = _soak([_beat(0, versor_condition=None), _beat(1, versor_condition=None)])
    outcome = evaluate_h1_closure(vacuous)
    assert not outcome.passed
    assert "vacuous" in outcome.detail


# --------------------------------------------------------------------------- #
# H2 — bounded idle (no leak on no-work beats)                                   #
# --------------------------------------------------------------------------- #
def test_h2_bounded_idle_holds_on_real_soak(tmp_path: Path) -> None:
    result = run_heartbeat_soak(_SOAK_N, engine_state_dir=tmp_path / "es")
    outcome = evaluate_h2_bounded_idle(result)
    assert outcome.passed, outcome.detail


def test_h2_bites_on_idle_vault_growth() -> None:
    # A no-work beat that grows the vault is an idle resource leak.
    leaky = _soak(
        [
            _beat(0, did_work=True, vault_size=3),
            _beat(1, did_work=False, vault_size=7),  # idle but grew 3 -> 7
            _beat(2, did_work=False, vault_size=7),
        ]
    )
    outcome = evaluate_h2_bounded_idle(leaky)
    assert not outcome.passed
    assert outcome.metrics["idle_leaks"] and outcome.metrics["idle_leaks"][0][0] == 1


# --------------------------------------------------------------------------- #
# H3 — convergence (settles and stays settled)                                  #
# --------------------------------------------------------------------------- #
def test_h3_convergence_holds_on_real_soak(tmp_path: Path) -> None:
    result = run_heartbeat_soak(_SOAK_N, engine_state_dir=tmp_path / "es")
    outcome = evaluate_h3_convergence(result)
    assert outcome.passed, outcome.detail
    assert outcome.metrics["converged_tail_len"] >= 2
    assert outcome.metrics["reawakenings"] == []


def test_h3_bites_on_never_settling() -> None:
    churning = _soak([_beat(i, did_work=True, vault_size=2 + i) for i in range(4)])
    outcome = evaluate_h3_convergence(churning)
    assert not outcome.passed


def test_h3_bites_on_reawakening() -> None:
    # Went to rest, then a beat did work again — a nondeterministic idle re-awakening.
    reawaken = _soak(
        [_beat(0, did_work=False), _beat(1, did_work=True, vault_size=3), _beat(2, did_work=False)]
    )
    outcome = evaluate_h3_convergence(reawaken)
    assert not outcome.passed
    assert 1 in outcome.metrics["reawakenings"]


# --------------------------------------------------------------------------- #
# H4 — reboot mid-soak resumes the SAME life                                    #
# --------------------------------------------------------------------------- #
def test_h4_reboot_resume_holds_on_real_soak(tmp_path: Path) -> None:
    result = run_heartbeat_soak(_SOAK_N, engine_state_dir=tmp_path / "es", reboot_at=(6,))
    outcome = evaluate_h4_reboot_resume(result)
    assert outcome.passed, outcome.detail
    assert result.resumed_cleanly is True
    assert result.learned_fact_survived is True  # the pre-reboot DERIVED fact was recalled


def test_h4_bites_on_failed_resume() -> None:
    broke = _soak([_beat(0, segment=0), _beat(1, segment=1)], reboot_at=(1,), resumed_cleanly=False)
    outcome = evaluate_h4_reboot_resume(broke)
    assert not outcome.passed
    assert "IdentityContinuityError" in outcome.detail


def test_h4_bites_on_lost_learning() -> None:
    lost = _soak(
        [_beat(0, segment=0), _beat(1, segment=1)],
        reboot_at=(1,),
        learned_fact_survived=False,
    )
    outcome = evaluate_h4_reboot_resume(lost)
    assert not outcome.passed
    assert "did NOT survive" in outcome.detail


def test_h4_requires_a_reboot_leg() -> None:
    with pytest.raises(ValueError):
        evaluate_h4_reboot_resume(_soak([_beat(0)]))
