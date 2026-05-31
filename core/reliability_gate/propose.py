"""ADR-0175 PROPOSE step — turn a practice ledger into ratifiable proposals.

This is the missing seam of the autonomous attempt-and-eliminate loop:

    attempt (sealed practice)  ->  gold-tether score  ->  ClassTally ledger
        ->  **propose_from_ledger (this module)**  ->  HITL ratification queue

The attempt/score/ledger half already exists (``evals/gsm8k_math/practice``
populates a ``dict[str, ClassTally]`` of correct/wrong/refused scored against
gold — the wrong=0 tether). What was missing is the gate consultation that
turns earned reliability into a *ratifiable proposal*: for each class, ask
:func:`license_for` whether the class has cleared its θ for the action.

Doctrine (ADR-0175):

- Reliability is the **conservative Wilson floor** on commitment precision
  (``correct / (correct+wrong)``); it is **0 below N_MIN committed trials**, so
  a class proposes only on sufficient evidence. Refusals never penalize it.
- A proposal is *proposal-only*. It NEVER touches the serving path — it is a
  queue entry for the reviewed teaching corridor to ratify. The engine earns
  the right to *ask*, not to *serve*.
- Deterministic: proposals are sorted by class name; the same ledger yields
  byte-identical proposals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.reliability_gate.ceilings import Action, Ceilings
from core.reliability_gate.gate import license_for
from core.reliability_gate.ledger import ClassTally


@dataclass(frozen=True, slots=True)
class RatifiableProposal:
    """A class whose earned practice reliability licenses a promotion proposal.

    Inspectable by construction — it carries the numbers behind the verdict so
    a reviewer ratifies on evidence, not on a bare boolean.
    """

    class_name: str
    action: str  # the licensed action ("propose" / "serve")
    checker: str  # which earned number gated it ("reliability" / "t2_precision")
    measured: float  # the conservative floor the class earned
    required: float  # the θ it cleared
    correct: int
    wrong: int
    committed: int

    def as_json(self) -> dict[str, Any]:
        return {
            "class_name": self.class_name,
            "action": self.action,
            "checker": self.checker,
            "measured": self.measured,
            "required": self.required,
            "correct": self.correct,
            "wrong": self.wrong,
            "committed": self.committed,
        }


def propose_from_ledger(
    ledger: Mapping[str, ClassTally],
    ceilings: Ceilings,
    *,
    action: Action = Action.PROPOSE,
    checker: str = "reliability",
) -> tuple[RatifiableProposal, ...]:
    """Emit a ratifiable proposal for every class that clears the gate.

    For each class tally, consult :func:`license_for`. A class earns a proposal
    iff the gate licenses ``action`` — i.e. its earned number (reliability, the
    conservative Wilson floor that is 0 below ``N_MIN`` committed trials) is
    ``>=`` the class's θ for ``action``. ``action`` defaults to
    :attr:`Action.PROPOSE` (θ=0.85); pass :attr:`Action.SERVE` (θ=0.99) to
    query the stricter serve gate.

    Returns a deterministic tuple sorted by class name. This is the loop's
    output — a ratification queue, never a serving mutation.
    """
    proposals: list[RatifiableProposal] = []
    for class_name in sorted(ledger):
        tally = ledger[class_name]
        decision = license_for(tally, action, ceilings, checker=checker)
        if not decision.licensed:
            continue
        proposals.append(
            RatifiableProposal(
                class_name=class_name,
                action=action.value,
                checker=decision.checker,
                measured=decision.measured,
                required=decision.required,
                correct=tally.correct,
                wrong=tally.wrong,
                committed=tally.committed,
            )
        )
    return tuple(proposals)
