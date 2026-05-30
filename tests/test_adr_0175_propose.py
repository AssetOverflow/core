"""ADR-0175 PROPOSE step — failing-under-violation guards.

The autonomous loop earns the right to *ask* (propose) only when a class clears
its θ on sufficient evidence. Each test fails if the gate is silently bypassed.
"""

from __future__ import annotations

from core.reliability_gate import (
    Action,
    Ceilings,
    ClassTally,
    N_MIN,
    propose_from_ledger,
)

_CEILINGS = Ceilings(())  # global defaults: PROPOSE θ=0.85, SERVE θ=0.99


def _reliable() -> ClassTally:
    # 50 committed, all correct → Wilson floor well above 0.85.
    return ClassTally("reliable").record(correct=50)


def _below_theta() -> ClassTally:
    # Enough evidence but imprecise → floor below 0.85.
    return ClassTally("sloppy").record(correct=10).record(wrong=5)


def _insufficient() -> ClassTally:
    # Perfect but under N_MIN committed → reliability is 0 (no evidence).
    return ClassTally("thin").record(correct=N_MIN - 1)


def _all_refused() -> ClassTally:
    return ClassTally("shy").record(refused=20)


def test_reliable_class_proposes() -> None:
    props = propose_from_ledger({"reliable": _reliable()}, _CEILINGS)
    assert [p.class_name for p in props] == ["reliable"]
    p = props[0]
    assert p.action == "propose"
    assert p.measured >= p.required >= 0.85
    assert p.correct == 50 and p.wrong == 0 and p.committed == 50


def test_below_theta_does_not_propose() -> None:
    assert propose_from_ledger({"sloppy": _below_theta()}, _CEILINGS) == ()


def test_insufficient_evidence_does_not_propose() -> None:
    # The N_MIN floor: a perfect-but-thin class earns NO proposal.
    assert propose_from_ledger({"thin": _insufficient()}, _CEILINGS) == ()


def test_all_refused_does_not_propose() -> None:
    # Refusals never earn a proposal (committed == 0 → reliability 0).
    assert propose_from_ledger({"shy": _all_refused()}, _CEILINGS) == ()


def test_serve_gate_is_stricter_than_propose() -> None:
    # A class licensed to PROPOSE (θ=0.85) need not be licensed to SERVE (θ=0.99).
    ledger = {"reliable": _reliable()}
    proposes = propose_from_ledger(ledger, _CEILINGS, action=Action.PROPOSE)
    serves = propose_from_ledger(ledger, _CEILINGS, action=Action.SERVE)
    assert proposes and not serves


def test_deterministic_and_sorted() -> None:
    ledger = {
        "zeta": _reliable(),
        "alpha": ClassTally("alpha").record(correct=40),
        "sloppy": _below_theta(),
    }
    a = propose_from_ledger(ledger, _CEILINGS)
    b = propose_from_ledger(ledger, _CEILINGS)
    assert a == b
    assert [p.class_name for p in a] == ["alpha", "zeta"]  # sorted; sloppy dropped


def test_mixed_ledger_only_reliable_classes_propose() -> None:
    ledger = {
        "reliable": _reliable(),
        "sloppy": _below_theta(),
        "thin": _insufficient(),
        "shy": _all_refused(),
    }
    props = propose_from_ledger(ledger, _CEILINGS)
    assert [p.class_name for p in props] == ["reliable"]
