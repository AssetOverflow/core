"""E gold-lane runner — committed ledger + license verdicts for the converse-guess.

Folds ``run_practice`` (the sealed ADR-0199 engine) over the gold lane and reads the
resulting per-predicate ``ClassTally`` through the reliability gate. The report is the
falsifiable artifact: it shows the gate DISCRIMINATING — the symmetric class earns the
SERVE license, the directed class does not — and carries the committed counts the
ratified ledger artifact (E-2) freezes.
"""

from __future__ import annotations

from typing import Any

from core.learning_arena.engine import run_practice
from core.reliability_gate import Action, Ceilings, ClassTally, license_for
from evals.determination_estimation.gold import (
    LICENSED_PREDICATE,
    REFUSED_PREDICATE,
    ConverseSolver,
    SymmetryGoldTether,
    all_gold_problems,
    generate_gold_problems,
)
from generate.determine.estimate import converse_class_name


def build_ledger() -> dict[str, ClassTally]:
    """Run sealed practice over the gold lane → the committed per-class ledger."""
    report = run_practice(all_gold_problems(), ConverseSolver(), SymmetryGoldTether())
    return dict(report.ledger)


def _tally_dict(tally: ClassTally) -> dict[str, Any]:
    return {
        "class_name": tally.class_name,
        "correct": tally.correct,
        "wrong": tally.wrong,
        "refused": tally.refused,
        "committed": tally.committed,
        "reliability": tally.reliability,
        "coverage": tally.coverage,
    }


def run(ceilings: Ceilings | None = None) -> dict[str, Any]:
    """Build the ledger and report the SERVE/PROPOSE license verdict per class."""
    ceilings = ceilings if ceilings is not None else Ceilings.default()
    ledger = build_ledger()
    licensed_cls = converse_class_name(LICENSED_PREDICATE)
    refused_cls = converse_class_name(REFUSED_PREDICATE)

    classes: dict[str, Any] = {}
    for cls, tally in sorted(ledger.items()):
        serve = license_for(tally, Action.SERVE, ceilings)
        propose = license_for(tally, Action.PROPOSE, ceilings)
        classes[cls] = {
            "tally": _tally_dict(tally),
            "serve_licensed": serve.licensed,
            "serve_ratio": serve.ratio,
            "propose_licensed": propose.licensed,
        }

    licensed_serves = classes.get(licensed_cls, {}).get("serve_licensed", False)
    refused_serves = classes.get(refused_cls, {}).get("serve_licensed", True)
    # The whole point: the gate discriminates — symmetric earns SERVE, directed does not.
    discriminates = bool(licensed_serves) and not bool(refused_serves)

    return {
        "lane": "determination-estimation",
        "licensed_class": licensed_cls,
        "refused_class": refused_cls,
        "classes": classes,
        "gate_discriminates": discriminates,
    }


def reliability_at(predicate: str, n: int) -> float:
    """The committed reliability of ``predicate``'s converse-guess over ``n`` cases —
    used to prove the SERVE volume floor binds (below 657, a symmetric class is unlicensed)."""
    report = run_practice(
        generate_gold_problems(predicate, n), ConverseSolver(), SymmetryGoldTether()
    )
    tally = report.ledger[converse_class_name(predicate)]
    return tally.reliability


__all__ = ["build_ledger", "reliability_at", "run"]
