"""Stage 7 — Ratify.  Apply gate checks; emit a self-sealed ``MasteryReport``.

This module is deliberately decoupled from ``CognitiveTurnPipeline``.  It
consumes a list of ``StepResult`` records (a small projection of
``CognitiveTurnResult`` the runner constructs in Phase 4) so that ratify can
be developed, tested, and reasoned about without taking on a runtime
dependency on the cognition pipeline.

Gates (from ``docs/formation_pipeline_plan.md`` §3 Phase 5):

    G1. ``replay_determinism == 1.0``       (every trace_hash matches between
                                              first and second run).
    G2. No regression vs prior Ratified courses
        (their replay assertions still hold).
    G3. Adversarial rejection rate ``== 1.0`` (every adversarial probe was
        rejected by the runtime).
    G4. Legitimate acceptance rate ``== 1.0`` (every non-adversarial step
        produced an accepted turn).
    G5. Provenance non-empty rate ``== 1.0``.
    G6. Every Phase II relation was exercised in at least one Phase III
        walk step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from formation.course import (
    GateMeasurement,
    MasteryReport,
    ValidatedTripleSet,
)
from formation.mastery import emit_report


# Step types that the Plan / Runner emit.  Kept here as a closed list so
# changes to the plan vocabulary force a deliberate edit.
STEP_TYPES_LEGIT: frozenset[str] = frozenset({
    "seed_concept",
    "introduce_relation",
    "walk_step",
})
STEP_TYPE_ADVERSARIAL: str = "adversarial_probe"
STEP_TYPE_REPLAY: str = "replay_assertion"


@dataclass(frozen=True, slots=True)
class StepResult:
    """A small canonical projection of a single ``CognitiveTurnResult``.

    The Runner (Phase 4) builds these from ``CognitiveTurnResult`` objects.
    Keeping ratify in this projection avoids a runtime dependency on
    ``core.cognition`` and keeps replay determinism a property of the data,
    not the orchestration.
    """

    step_type: str
    payload: dict[str, object]
    trace_hash: str
    versor_condition_repr: str  # string form (e.g. "0.0", "9.3e-09")
    accepted: bool
    has_provenance: bool


@dataclass(frozen=True, slots=True)
class _Counts:
    legit_total: int = 0
    legit_accepted: int = 0
    adversarial_total: int = 0
    adversarial_rejected: int = 0
    provenance_total: int = 0
    provenance_nonempty: int = 0
    walked_relations: frozenset[tuple[str, str, str]] = field(default_factory=frozenset)


def _tally(results: Iterable[StepResult]) -> _Counts:
    legit_t = legit_a = adv_t = adv_r = prov_t = prov_n = 0
    walked: set[tuple[str, str, str]] = set()
    for r in results:
        prov_t += 1
        if r.has_provenance:
            prov_n += 1
        if r.step_type == STEP_TYPE_ADVERSARIAL:
            adv_t += 1
            if not r.accepted:
                adv_r += 1
        elif r.step_type in STEP_TYPES_LEGIT:
            legit_t += 1
            if r.accepted:
                legit_a += 1
        if r.step_type == "walk_step":
            h = r.payload.get("head")
            rel = r.payload.get("relation")
            t = r.payload.get("tail")
            if isinstance(h, str) and isinstance(rel, str) and isinstance(t, str):
                walked.add((h, rel, t))
    return _Counts(
        legit_total=legit_t,
        legit_accepted=legit_a,
        adversarial_total=adv_t,
        adversarial_rejected=adv_r,
        provenance_total=prov_t,
        provenance_nonempty=prov_n,
        walked_relations=frozenset(walked),
    )


def _ratio_repr(numerator: int, denominator: int) -> str:
    """Return the ratio as a stable string, avoiding float repr drift."""
    if denominator == 0:
        return "n/a"
    if numerator == denominator:
        return "1.0"
    if numerator == 0:
        return "0.0"
    return f"{numerator}/{denominator}"


def ratify(
    *,
    course_id: str,
    source_bundle_sha: str,
    validated_set_sha: str,
    course_sha256: str,
    plan_sha256: str,
    validated_set: ValidatedTripleSet,
    first_run: tuple[StepResult, ...],
    second_run: tuple[StepResult, ...],
    issued_at: str | None = None,
) -> MasteryReport:
    """Run gate checks G1–G6 and emit a self-sealed ``MasteryReport``."""
    gates: list[GateMeasurement] = []
    failure_reasons: list[str] = []

    # G1: replay determinism — pairwise trace_hash equality.
    if len(first_run) != len(second_run):
        gates.append(GateMeasurement(
            name="G1_replay_determinism",
            passed=False,
            measurement=f"length_mismatch:{len(first_run)}!={len(second_run)}",
            threshold="1.0",
        ))
        failure_reasons.append("replay_length_mismatch")
    else:
        mismatches = sum(
            1 for a, b in zip(first_run, second_run) if a.trace_hash != b.trace_hash
        )
        passed = mismatches == 0
        gates.append(GateMeasurement(
            name="G1_replay_determinism",
            passed=passed,
            measurement=_ratio_repr(
                len(first_run) - mismatches, len(first_run)
            ) if first_run else "n/a",
            threshold="1.0",
        ))
        if not passed:
            failure_reasons.append(f"replay_trace_mismatch:{mismatches}")

    counts = _tally(first_run)

    # G3: adversarial rejection rate.
    g3_passed = (
        counts.adversarial_total == 0
        or counts.adversarial_rejected == counts.adversarial_total
    )
    gates.append(GateMeasurement(
        name="G3_adversarial_rejection_rate",
        passed=g3_passed,
        measurement=_ratio_repr(counts.adversarial_rejected, counts.adversarial_total),
        threshold="1.0",
    ))
    if not g3_passed:
        failure_reasons.append("adversarial_probe_accepted")

    # G4: legitimate acceptance rate.
    g4_passed = (
        counts.legit_total == 0
        or counts.legit_accepted == counts.legit_total
    )
    gates.append(GateMeasurement(
        name="G4_legitimate_acceptance_rate",
        passed=g4_passed,
        measurement=_ratio_repr(counts.legit_accepted, counts.legit_total),
        threshold="1.0",
    ))
    if not g4_passed:
        failure_reasons.append("legitimate_step_rejected")

    # G5: provenance non-empty rate.
    g5_passed = (
        counts.provenance_total == 0
        or counts.provenance_nonempty == counts.provenance_total
    )
    gates.append(GateMeasurement(
        name="G5_provenance_nonempty_rate",
        passed=g5_passed,
        measurement=_ratio_repr(counts.provenance_nonempty, counts.provenance_total),
        threshold="1.0",
    ))
    if not g5_passed:
        failure_reasons.append("provenance_missing")

    # G6: every Phase II relation walked.
    needed = {(r.head, r.relation, r.tail) for r in validated_set.relations}
    missing = needed - counts.walked_relations
    g6_passed = not missing
    gates.append(GateMeasurement(
        name="G6_phase2_relation_coverage",
        passed=g6_passed,
        measurement=_ratio_repr(len(needed) - len(missing), len(needed)),
        threshold="1.0",
    ))
    if not g6_passed:
        failure_reasons.append(f"unwalked_relations:{len(missing)}")

    # G2 — prior-course regression — is a no-op placeholder until the
    # MasteredCoursesIndex (Phase 7) is online.  Recorded as passed=True with
    # measurement="deferred" so the gate is visible in the report.
    gates.append(GateMeasurement(
        name="G2_prior_course_regression",
        passed=True,
        measurement="deferred:no_prior_courses",
        threshold="1.0",
    ))

    return emit_report(
        course_id=course_id,
        source_bundle_sha=source_bundle_sha,
        validated_set_sha=validated_set_sha,
        course_sha256=course_sha256,
        plan_sha256=plan_sha256,
        gates=tuple(gates),
        trace_hashes=tuple(r.trace_hash for r in first_run),
        failure_reasons=tuple(failure_reasons),
        issued_at=issued_at,
    )
