"""D1/D2 guided determinism tour — a curated narrative over the real demos.

The tour is the first-run, provider-agnostic story: bring a claim from any
model and watch the deterministic engine decide it, refuse it, or replay it —
proposer authority ignored.  Each demo step is BOUND to a real entry in the
demo registry: the honesty cards (``what_this_proves`` /
``what_this_does_not_prove``) and the demo title are pulled from the spec, never
re-authored, so the tour can never claim more than the demo it points at.  A
step that references a missing demo is a fail-closed error, not a dead link.
"""

from __future__ import annotations

from workbench.readers import DEMO_SPECS
from workbench.schemas import DeterminismTour, TourStep, TourStepKind

_THESIS = (
    "CORE is the deterministic engine the opaque transformer defines itself "
    "against. Bring a claim — from any model, including your own — and watch the "
    "engine decide it, refuse it, or replay it to the same hash. The proposing "
    "model's authority is ignored; only verified evidence promotes."
)

# (step_id, kind, headline, narrative, demo_id, route_hint)
_TourPlanRow = tuple[str, TourStepKind, str, str, str | None, str | None]

_TOUR_PLAN: tuple[_TourPlanRow, ...] = (
    (
        "intro",
        "intro",
        "Determinism you can check",
        "These are not screenshots or animations. Each step runs a real demo "
        "over pinned fixtures, end to end. Watch the engine apply discipline you "
        "can re-run and verify yourself.",
        None,
        "/demos",
    ),
    (
        "decide",
        "demo",
        "Bring a claim — the engine decides",
        "A formal claim is served as entailed, refuted, or unknown only when the "
        "pinned ROBDD engine and an independent oracle agree. Disagree, and it "
        "refuses. The proposer never gets to assert the answer.",
        "deductive_entailment_authority",
        "/demos/deductive_entailment_authority",
    ),
    (
        "refuse",
        "demo",
        "A wrong proposer gets refused",
        "When a proposer tries to smuggle an unsupported truth-state, the engine "
        "rejects it. You are watching a wrong answer get refused rather than "
        "served — the discipline that makes wrong=0 real.",
        "epistemic_truth_state",
        "/demos/epistemic_truth_state",
    ),
    (
        "promote",
        "demo",
        "Only a verified certificate promotes",
        "Promotion into the vault happens only through an owner-applied verified "
        "certificate. Proposer status is ignored entirely — authority lives in "
        "the evidence, not the model.",
        "proof_carrying_promotion",
        "/demos/proof_carrying_promotion",
    ),
    (
        "payoff",
        "payoff",
        "Replay to the same hash, export the proof",
        "Every decision above replays to the same trace hash, and any turn "
        "exports as a content-addressed evidence bundle you can cite and "
        "reproduce. Determinism isn't a claim here; it's a deliverable.",
        None,
        "/replay",
    ),
)


def _build_tour(plan: tuple[_TourPlanRow, ...]) -> DeterminismTour:
    steps: list[TourStep] = []
    for order, (step_id, kind, headline, narrative, demo_id, route_hint) in enumerate(plan):
        demo_title = proves = not_proves = None
        if demo_id is not None:
            spec = DEMO_SPECS.get(demo_id)
            if spec is None:
                raise KeyError(
                    f"determinism tour references unknown demo: {demo_id}"
                )
            demo_title = spec.title
            proves = spec.what_this_proves
            not_proves = spec.what_this_does_not_prove
        steps.append(
            TourStep(
                step_id=step_id,
                order=order,
                kind=kind,
                headline=headline,
                narrative=narrative,
                demo_id=demo_id,
                demo_title=demo_title,
                what_this_proves=proves,
                what_this_does_not_prove=not_proves,
                route_hint=route_hint,
            )
        )
    return DeterminismTour(
        schema_version="determinism_tour_v1",
        title="The Determinism Tour",
        thesis=_THESIS,
        steps=steps,
    )


def determinism_tour() -> DeterminismTour:
    """Build the curated determinism tour, bound to the live demo registry."""

    return _build_tour(_TOUR_PLAN)
