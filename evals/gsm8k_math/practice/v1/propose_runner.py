"""ADR-0175 PROPOSE runner — close the autonomous loop end-to-end.

    run_practice  (attempt → gold-tether score → ClassTally ledger)
      → propose_from_ledger  (the PROPOSE gate: reliability ≥ θ on N ≥ N_MIN)
      → ratification_queue.json  (the HITL queue — NEVER a serving change)

This is the wiring that was missing: the attempt/score/ledger half already
existed; nothing consulted the gate to turn earned reliability into a
ratifiable proposal. The output is *proposal-only* — a queue for the reviewed
teaching corridor, not a serving mutation. No serving module imports this.

The attempt ``scorer`` is injectable. The default is the practice lane's own
scorer (the serving candidate-graph). Injecting an *aggressive* sealed scorer
(e.g. ``resolve_pooled``) is what makes this a real attempt-and-eliminate
regime — the gate then filters classes the aggressive reader gets wrong while
proposing the ones it reads reliably.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from core.reliability_gate import Action, Ceilings, propose_from_ledger
from evals.gsm8k_math.practice.v1.runner import (
    PracticeReport,
    _load_practice_cases,
    run_practice,
    write_report,
)

_HERE = Path(__file__).resolve().parent
_QUEUE_PATH = _HERE / "ratification_queue.json"


def resolve_pooled_scorer(adapted: dict[str, Any]) -> Any:
    """An AGGRESSIVE sealed scorer: attempt with the derivation reader
    (``resolve_pooled``) and score against gold (the wrong=0 tether).

    Unlike the conservative serving scorer, this reader *commits* on shapes
    serving refuses — so its practice ledger carries real ``wrong``. That is
    the attempt-and-eliminate regime: the PROPOSE gate then proposes only the
    classes it reads *reliably* and leaves the rest sealed.
    """
    from evals.gsm8k_math.runner import CaseOutcome
    from generate.derivation.pool import resolve_pooled

    expected = float(adapted["expected_answer"])
    unit = adapted.get("expected_unit", "") or ""
    resolution = resolve_pooled(adapted["problem"])
    if resolution is None:
        return CaseOutcome(
            case_id=adapted["id"], outcome="refused",
            reason="resolve_pooled: no resolution", expected_answer=expected,
            expected_unit=unit, actual_answer=None, actual_unit=None,
            trace_hash=None, realized_prose=None,
        )
    value = float(resolution.answer)
    correct = abs(value - expected) < 1e-6
    return CaseOutcome(
        case_id=adapted["id"], outcome="correct" if correct else "wrong",
        reason="resolve_pooled", expected_answer=expected, expected_unit=unit,
        actual_answer=value, actual_unit=getattr(resolution, "answer_unit", None),
        trace_hash=None, realized_prose=None,
    )


def build_queue_from_report(
    report: PracticeReport,
    *,
    ceilings: Ceilings | None = None,
) -> dict[str, Any]:
    """Project a finished practice ``report`` into the HITL ratification queue.

    Split out so report.json and the queue can be emitted from ONE practice
    pass (see :func:`regenerate_practice_artifacts`) — guaranteeing they never
    drift, since both are projections of the same ledger.
    """
    ceilings = ceilings if ceilings is not None else Ceilings(())
    proposals = propose_from_ledger(report.ledger, ceilings, action=Action.PROPOSE)
    return {
        "schema_version": 1,
        "adr": "0175",
        "regime": "propose",
        "note": "proposal-only ratification queue; never a serving mutation",
        "practice_counts": dict(sorted(report.counts.items())),
        "proposals": [p.as_json() for p in proposals],
        "proposal_count": len(proposals),
    }


def build_ratification_queue(
    *,
    ceilings: Ceilings | None = None,
    scorer: Callable[[dict[str, Any]], Any] | None = None,
    cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run practice, consult the PROPOSE gate, return the ratification queue."""
    report = run_practice(
        cases if cases is not None else _load_practice_cases(), scorer=scorer
    )
    return build_queue_from_report(report, ceilings=ceilings)


def write_queue(queue: dict[str, Any], path: Path = _QUEUE_PATH) -> None:
    path.write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def regenerate_practice_artifacts(
    *,
    ceilings: Ceilings | None = None,
) -> tuple[PracticeReport, dict[str, Any]]:
    """One sealed ``resolve_pooled`` practice pass → BOTH committed artifacts.

    ``report.json`` (the per-class ledger the calibration reader consumes) and
    ``ratification_queue.json`` (the HITL proposals) are two projections of the
    SAME pass. Emitting them together makes them coherent by construction and
    byte-reproducible by re-running this entry point — closing the gap where a
    hand-copied report.json agreed with the queue but no runner produced it.
    PROPOSE regime / proposal-only; ``resolve_pooled`` is the aggressive sealed
    scorer (unsafe for *serving*, legitimate for attempt-and-eliminate here).
    """
    report = run_practice(_load_practice_cases(), scorer=resolve_pooled_scorer)
    write_report(report)
    queue = build_queue_from_report(report, ceilings=ceilings)
    write_queue(queue)
    return report, queue


def main() -> int:
    # The aggressive sealed regime: report.json + ratification_queue.json are
    # emitted from one pass so the gate filters real wrong>0 and the two
    # artifacts cannot drift — the point of attempt-and-eliminate.
    _, queue = regenerate_practice_artifacts()
    print(f"practice counts: {queue['practice_counts']}")
    print(f"ratifiable proposals: {queue['proposal_count']}")
    for p in queue["proposals"]:
        print(
            f"  {p['class_name']}: reliability={p['measured']:.4f} "
            f">= {p['required']} (correct={p['correct']} wrong={p['wrong']} "
            f"committed={p['committed']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
