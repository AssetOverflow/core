"""Demo narrative scaffolding for Workbench proof theater.

A demo narrative is an authored path over real evidence routes. It must state both
what a step proves and what it does not prove, so demo polish cannot outrun
substrate evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

DemoStepKind = Literal["intro", "evidence", "replay", "proposal", "audit", "payoff"]


@dataclass(frozen=True, slots=True)
class DemoEvidenceLink:
    label: str
    route: str
    artifact_id: str | None = None
    digest: str | None = None
    reproducer: str | None = None


@dataclass(frozen=True, slots=True)
class DemoNarrativeStep:
    step_id: str
    order: int
    kind: DemoStepKind
    title: str
    claim: str
    what_this_proves: str
    what_this_does_not_prove: str
    evidence_links: list[DemoEvidenceLink] = field(default_factory=list)
    failure_mode: str | None = None


@dataclass(frozen=True, slots=True)
class DemoNarrative:
    narrative_id: str
    title: str
    summary: str
    steps: list[DemoNarrativeStep] = field(default_factory=list)


def validate_demo_narrative(narrative: DemoNarrative) -> list[str]:
    """Return validation blockers for a Workbench demo narrative."""

    blockers: list[str] = []
    seen: set[str] = set()
    for step in narrative.steps:
        if step.step_id in seen:
            blockers.append(f"duplicate step_id: {step.step_id}")
        seen.add(step.step_id)
        if not step.what_this_proves.strip():
            blockers.append(f"step {step.step_id} is missing what_this_proves")
        if not step.what_this_does_not_prove.strip():
            blockers.append(f"step {step.step_id} is missing what_this_does_not_prove")
        for link in step.evidence_links:
            if not link.route.startswith("/"):
                blockers.append(f"step {step.step_id} has non-route evidence link: {link.route}")
    orders = [step.order for step in narrative.steps]
    if orders != sorted(orders):
        blockers.append("steps must be sorted by order")
    return blockers


def demo_partner_blurb() -> str:
    return (
        "A frontier model can propose. CORE can govern. Workbench can prove what "
        "happened, what was refused, what replayed, and what remains only a proposal."
    )
