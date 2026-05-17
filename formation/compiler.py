"""Stage 5 — Compile.  ``CourseYAML`` -> ``FormationPlan``.

The plan is a deterministic, content-addressed sequence of ``PlanStep``
objects.  Each step carries the typed payload the Runner needs to issue a
single ``CognitiveTurnPipeline.run()`` invocation.

Same ``CourseYAML`` -> same ``FormationPlan`` -> same ``plan_sha256``.  This
property is load-bearing for replay determinism and the ratify gates.
"""

from __future__ import annotations

from typing import Any

import yaml

from formation.course import CourseYAML, FormationPlan, PlanStep
from formation.hashing import sha256_of


def compile_course(course: CourseYAML) -> FormationPlan:
    """Convert a ``CourseYAML`` to a deterministic ``FormationPlan``."""
    body = yaml.safe_load(course.yaml_bytes)
    if not isinstance(body, dict):
        raise ValueError("compile_course: course body must be a mapping")
    # The Definition template emits course fields at the top level; we accept
    # either a wrapped ``course:`` mapping (future templates) or the bare form.
    course_block = body.get("course") if "course" in body else body
    if not isinstance(course_block, dict):
        raise ValueError("compile_course: course payload must be a mapping")

    steps: list[PlanStep] = []
    steps.extend(_seed_concept_steps(course_block))
    steps.extend(_introduce_relation_steps(course_block))
    steps.extend(_walk_step_steps(course_block))
    steps.extend(_adversarial_probe_steps(course_block))
    steps.extend(_replay_assertion_steps(course_block))

    plan_sha = sha256_of({
        "course_id": course.course_id,
        "course_sha256": course.course_sha256,
        "steps": [
            {"step_type": s.step_type, "payload": _canonicalize(s.payload)}
            for s in steps
        ],
    })
    return FormationPlan(
        course_id=course.course_id,
        course_sha256=course.course_sha256,
        steps=tuple(steps),
        plan_sha256=plan_sha,
    )


# ---------- per-phase extractors ----------


def _seed_concept_steps(course: dict[str, Any]) -> list[PlanStep]:
    phase = course.get("phase_1_ontological_seeding", {}) or {}
    items = phase.get("concepts", []) or []
    out: list[PlanStep] = []
    for c in items:
        if not isinstance(c, dict):
            continue
        term = str(c.get("canonical_term", ""))
        definition = str(c.get("definition", ""))
        if not term:
            continue
        out.append(PlanStep(
            step_type="seed_concept",
            payload={
                "canonical_term": term,
                "definition": definition,
                "utterance": f"What is {term}?",
            },
        ))
    return out


def _introduce_relation_steps(course: dict[str, Any]) -> list[PlanStep]:
    phase = course.get("phase_2_axiomatic_rotor_scaffolding", {}) or {}
    items = phase.get("relations", []) or []
    out: list[PlanStep] = []
    for r in items:
        if not isinstance(r, dict):
            continue
        head = str(r.get("head", ""))
        relation = str(r.get("relation", ""))
        tail = str(r.get("tail", ""))
        if not head or not relation or not tail:
            continue
        out.append(PlanStep(
            step_type="introduce_relation",
            payload={
                "head": head,
                "relation": relation,
                "tail": tail,
                "utterance": f"{head} {relation.replace('_', ' ')} {tail}.",
            },
        ))
    return out


def _walk_step_steps(course: dict[str, Any]) -> list[PlanStep]:
    phase = course.get("phase_3_holonomic_syllabus_walk", {}) or {}
    # Accept the Definition template's ``walks:`` key as well as the future
    # ``ordered_walks:`` form proposed in the plan doc.
    walks = phase.get("walks") or phase.get("ordered_walks") or []
    out: list[PlanStep] = []
    for walk in walks:
        if not isinstance(walk, dict):
            continue
        edges = walk.get("steps") or walk.get("edges") or []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            head = str(edge.get("head", ""))
            relation = str(edge.get("relation", ""))
            tail = str(edge.get("tail", ""))
            if not head or not relation or not tail:
                continue
            out.append(PlanStep(
                step_type="walk_step",
                payload={
                    "head": head,
                    "relation": relation,
                    "tail": tail,
                    "utterance": f"What does {head} {relation.replace('_', ' ')}?",
                },
            ))
    return out


def _adversarial_probe_steps(course: dict[str, Any]) -> list[PlanStep]:
    phase = course.get("phase_4_epistemic_boundary_hardening", {}) or {}
    out: list[PlanStep] = []
    for false_claim in phase.get("false_claims", []) or []:
        if not isinstance(false_claim, dict):
            continue
        head = str(false_claim.get("head", ""))
        relation = str(false_claim.get("relation", ""))
        tail = str(false_claim.get("tail", ""))
        if not head or not relation or not tail:
            continue
        out.append(PlanStep(
            step_type="adversarial_probe",
            payload={
                "head": head,
                "relation": relation,
                "tail": tail,
                "kind": "false_claim",
                "utterance": f"{head} {relation.replace('_', ' ')} {tail}.",
            },
        ))
    for probe in phase.get("adversarial_corrections", []) or []:
        if isinstance(probe, dict):
            utterance = str(probe.get("prompt") or probe.get("utterance") or "")
            probe_id = str(probe.get("probe_id", ""))
        else:
            utterance = str(probe)
            probe_id = ""
        if not utterance:
            continue
        out.append(PlanStep(
            step_type="adversarial_probe",
            payload={
                "kind": "identity_override",
                "probe_id": probe_id,
                "utterance": utterance,
            },
        ))
    return out


def _replay_assertion_steps(course: dict[str, Any]) -> list[PlanStep]:
    phase = course.get("phase_5_ratified_consolidation", {}) or {}
    replay = phase.get("replay")
    if isinstance(replay, dict):
        if not replay.get("deterministic", False):
            return []
        return [PlanStep(
            step_type="replay_assertion",
            payload={
                "prior_regression_allowed": bool(
                    replay.get("prior_regression_allowed", False)
                ),
            },
        )]
    # Definition template form: presence of ``ratification_gates`` implies a
    # deterministic replay step.
    gates = phase.get("ratification_gates")
    if isinstance(gates, list) and gates:
        return [PlanStep(
            step_type="replay_assertion",
            payload={"gates": [str(g) for g in gates]},
        )]
    return []


# ---------- helpers ----------


def _canonicalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with stable iteration order — dict literal already sorts via sha256_of."""
    return dict(payload)
