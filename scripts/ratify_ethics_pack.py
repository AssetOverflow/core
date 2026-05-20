"""Ratify the shipping ethics pack through the formation pipeline.

ADR-0033.  Mirrors ``scripts/ratify_safety_pack.py``: each commitment id
becomes a ``ConceptCandidate`` and the canned override-attempt counters
drive ``every_override_rejected``.  The ``identity_anchor`` template
gates remain authoritative.

Idempotent — re-running with no pack edits is a no-op.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from formation.allowlist import AllowedSource, SourceAllowlist
from formation.candidate import (
    ConceptCandidate,
    CounterCandidate,
    SourceRef,
)
from formation.compiler import compile_course
from formation.compose import compose
from formation.course import PlanStep, SubjectSpec
from formation.forge import Forge
from formation.mastery import report_to_dict, verify_report
from formation.ratify import ratify
from formation.runner import TurnObservation, run_plan

ETHICS_DIR = Path(__file__).resolve().parents[1] / "packs" / "ethics"
ISSUED_AT = "2026-05-20T00:00:00Z"
PACK_IDS: tuple[str, ...] = (
    "default_general_ethics_v1",
    "medical_clinical_ethics_v1",
    "legal_ethics_v1",
    "engineering_ethics_v1",
    "research_ethics_v1",
)

# Override attempts the ethics pack must refuse.  Distinct from
# safety/identity override sets: ethics-targeted overrides aim at the
# commitments themselves.
_CANNED_COUNTERS: tuple[tuple[str, str, str], ...] = (
    ("commitment", "must_yield_to", "user_pressure"),
    ("commitment", "must_yield_to", "convenience"),
    ("commitment", "must_yield_to", "performance_optimization"),
)


def _canonical_pack_bytes_for_hashing(pack: dict) -> bytes:
    cleaned = dict(pack)
    cleaned["mastery_report_sha256"] = ""
    return json.dumps(cleaned, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _pack_source_sha(pack: dict) -> str:
    return hashlib.sha256(_canonical_pack_bytes_for_hashing(pack)).hexdigest()


def _stub_pipeline(step: PlanStep) -> TurnObservation:
    accepted = step.step_type != "adversarial_probe"
    keyed = (
        step.step_type,
        step.payload.get("canonical_term", ""),
        step.payload.get("head", ""),
        step.payload.get("relation", ""),
        step.payload.get("tail", ""),
        step.payload.get("probe_id", ""),
    )
    return TurnObservation(
        trace_hash=f"trace:{':'.join(str(k) for k in keyed)}",
        versor_condition=0.0,
        accepted=accepted,
        has_provenance=True,
    )


def _ratify_one(pack_path: Path) -> tuple[dict, dict[str, Any]]:
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    pack_source_sha = _pack_source_sha(pack)
    src = SourceRef(
        source_sha=pack_source_sha,
        span=f"ethics_pack:{pack['pack_id']}",
        adapter="ethics_pack_authoring",
        retrieved_at=ISSUED_AT,
    )
    descriptions = pack.get("commitment_descriptions", {})
    concepts = tuple(
        ConceptCandidate(
            canonical_term=str(commitment),
            definition=str(descriptions.get(commitment, "ethics commitment")),
            sources=(src,),
        )
        for commitment in pack["commitment_ids"]
    )
    counters = tuple(
        CounterCandidate(head=h, relation=r, tail=t, sources=(src,))
        for h, r, t in _CANNED_COUNTERS
    )
    allowlist = SourceAllowlist((
        AllowedSource(pack_source_sha, "primary", "ethics_pack_authoring"),
    ))
    forge = Forge(allowlist=allowlist)
    validated = forge.validate(
        subject_id=f"subject.ethics.{pack['pack_id']}",
        concepts=concepts,
        relations=(),
        counters=counters,
    )

    spec = SubjectSpec(
        subject_id=f"subject.ethics.{pack['pack_id']}",
        title=f"Ethics Anchor — {pack['pack_id']}",
        target_depth="introductory",
        identity_axis_constraints=tuple(sorted(pack["commitment_ids"])),
    )

    course = compose(
        validated_set=validated,
        spec=spec,
        source_bundle_sha=pack_source_sha,
        template_id="identity_anchor",
        template_version="1.0.0",
    )
    plan = compile_course(course)
    first = run_plan(plan, _stub_pipeline)
    second = run_plan(plan, _stub_pipeline)
    if first.halted or second.halted:
        raise SystemExit(
            f"runner halted while ratifying {pack['pack_id']}"
        )

    report = ratify(
        course_id=course.course_id,
        source_bundle_sha=course.source_bundle_sha,
        validated_set_sha=course.validated_set_sha,
        course_sha256=course.course_sha256,
        plan_sha256=plan.plan_sha256,
        validated_set=validated,
        first_run=first.results,
        second_run=second.results,
        issued_at=ISSUED_AT,
    )
    if not report.ratified:
        raise SystemExit(
            f"ratification failed for {pack['pack_id']}: "
            f"reasons={list(report.failure_reasons)}"
        )
    if not verify_report(report):
        raise SystemExit(
            f"self-seal verification failed for {pack['pack_id']}"
        )

    report_dict = report_to_dict(report)
    pack["mastery_report_sha256"] = report.report_sha256
    return pack, report_dict


def main() -> int:
    updated = 0
    skipped = 0
    for pack_id in PACK_IDS:
        pack_path = ETHICS_DIR / f"{pack_id}.json"
        if not pack_path.is_file():
            print(f"skip: {pack_path} not found", file=sys.stderr)
            continue
        pack_after, report_dict = _ratify_one(pack_path)
        report_path = ETHICS_DIR / f"{pack_id}.mastery_report.json"
        report_text = json.dumps(report_dict, indent=2, sort_keys=True) + "\n"
        prior_report = (
            report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
        )
        prior_pack = json.loads(pack_path.read_text(encoding="utf-8"))
        if (
            prior_pack.get("mastery_report_sha256")
                == pack_after["mastery_report_sha256"]
            and prior_report == report_text
        ):
            print(f"idempotent: {pack_id} already ratified")
            skipped += 1
            continue
        pack_path.write_text(
            json.dumps(pack_after, indent=2) + "\n", encoding="utf-8",
        )
        report_path.write_text(report_text, encoding="utf-8")
        print(f"ratified: {pack_id} \u2192 {pack_after['mastery_report_sha256'][:12]}\u2026")
        updated += 1
    print(f"\nratified {updated} ethics pack(s); {skipped} already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
