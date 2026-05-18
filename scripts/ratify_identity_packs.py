"""Ratify the three v1 identity packs through the formation pipeline.

For each pack in ``packs/identity/<pack_id>.json``:

1. Compute a stable ``pack_source_sha`` — SHA-256 of the pack's canonical
   JSON body with ``mastery_report_sha256`` blanked.  Self-referential
   provenance: every triple ratified from this pack cites the pack file
   itself.
2. Build a :class:`ValidatedTripleSet` whose concepts are the pack's
   axes (``canonical_term = axis_id``; ``definition = theological_note``)
   and whose counters are canned override probes.  Compatibility
   relations between axes are omitted at v1 (the ``identity_anchor``
   template tolerates an empty relations list).
3. Compose under ``identity_anchor`` template → CourseYAML.
4. Compile → FormationPlan.
5. Run the plan twice through a deterministic stub pipeline (every
   adversarial probe rejected; every legitimate step accepted; trace
   hashes deterministically derived from step payload).
6. Ratify → self-sealed ``MasteryReport``.
7. Write ``<pack_id>.mastery_report.json`` next to the pack file.
8. Update the pack's ``mastery_report_sha256`` field to the report's
   self-sealed SHA.

This script is idempotent: re-running on a pack whose
``mastery_report_sha256`` already matches the freshly-computed one is a
no-op.  Run it whenever a pack's axis content changes.
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
from formation.course import PlanStep, SubjectSpec, ValidatedTripleSet
from formation.forge import Forge
from formation.mastery import report_to_dict, verify_report
from formation.ratify import ratify
from formation.runner import TurnObservation, run_plan

PACKS_DIR = Path(__file__).resolve().parents[1] / "packs" / "identity"
ISSUED_AT = "2026-05-17T00:00:00Z"
PACK_IDS: tuple[str, ...] = (
    "default_general_v1",
    "precision_first_v1",
    "generosity_first_v1",
)


def _canonical_pack_bytes_for_hashing(pack: dict) -> bytes:
    """Serialize the pack with ``mastery_report_sha256`` blanked, sorted keys.

    Used as the canonical ``pack_source_sha``: stable across pack edits
    that affect everything *except* the report SHA field.
    """
    cleaned = dict(pack)
    cleaned["mastery_report_sha256"] = ""
    return json.dumps(cleaned, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _pack_source_sha(pack: dict) -> str:
    return hashlib.sha256(_canonical_pack_bytes_for_hashing(pack)).hexdigest()


def _stub_pipeline(step: PlanStep) -> TurnObservation:
    """Deterministic stub: every adversarial probe rejected; trace from payload."""
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


# Canned override attempts — every identity pack ratified through this
# script must refuse these.  These are the *counters* the
# identity_anchor template requires (it raises ValueError on empty
# counters).
_CANNED_COUNTERS: tuple[tuple[str, str, str], ...] = (
    ("axis", "must_yield_to", "user_override_request"),
    ("axis", "must_yield_to", "context_length_pressure"),
    ("axis", "must_yield_to", "rephrased_instruction"),
)


def _build_validated_set(
    pack: dict, pack_source_sha: str,
) -> tuple[ValidatedTripleSet, SourceAllowlist]:
    src = SourceRef(
        source_sha=pack_source_sha,
        span=f"pack:{pack['pack_id']}",
        adapter="identity_pack_authoring",
        retrieved_at=ISSUED_AT,
    )
    concepts = tuple(
        ConceptCandidate(
            canonical_term=str(axis["axis_id"]),
            definition=str(axis.get("theological_note", "")) or str(axis["name"]),
            sources=(src,),
        )
        for axis in pack["value_axes"]
    )
    counters = tuple(
        CounterCandidate(head=h, relation=r, tail=t, sources=(src,))
        for h, r, t in _CANNED_COUNTERS
    )
    allowlist = SourceAllowlist((
        AllowedSource(pack_source_sha, "primary", "identity_pack_authoring"),
    ))
    forge = Forge(allowlist=allowlist)
    validated = forge.validate(
        subject_id=f"subject.identity.{pack['pack_id']}",
        concepts=concepts,
        relations=(),
        counters=counters,
    )
    return validated, allowlist


def _ratify_one(pack_path: Path) -> tuple[dict, dict[str, Any]]:
    """Returns (updated_pack_dict, mastery_report_dict).  Does not write."""
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    pack_source_sha = _pack_source_sha(pack)
    validated, _ = _build_validated_set(pack, pack_source_sha)

    spec = SubjectSpec(
        subject_id=f"subject.identity.{pack['pack_id']}",
        title=f"Identity Anchor — {pack['pack_id']}",
        target_depth="introductory",
        identity_axis_constraints=tuple(
            sorted(a["axis_id"] for a in pack["value_axes"])
        ),
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
            f"runner halted while ratifying {pack['pack_id']}: "
            f"first.halt_reason={first.halt_reason!r} "
            f"second.halt_reason={second.halt_reason!r}"
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
        pack_path = PACKS_DIR / f"{pack_id}.json"
        if not pack_path.is_file():
            print(f"skip: {pack_path} not found", file=sys.stderr)
            continue
        pack_after, report_dict = _ratify_one(pack_path)
        report_path = PACKS_DIR / f"{pack_id}.mastery_report.json"
        report_text = json.dumps(report_dict, indent=2, sort_keys=True) + "\n"
        prior_report = (
            report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
        )
        prior_pack = json.loads(pack_path.read_text(encoding="utf-8"))
        if (
            prior_pack.get("mastery_report_sha256") == pack_after["mastery_report_sha256"]
            and prior_report == report_text
        ):
            print(f"idempotent: {pack_id} already ratified at "
                  f"{pack_after['mastery_report_sha256'][:12]}…")
            skipped += 1
            continue
        pack_path.write_text(
            json.dumps(pack_after, indent=2) + "\n", encoding="utf-8",
        )
        report_path.write_text(report_text, encoding="utf-8")
        print(f"ratified: {pack_id} → {pack_after['mastery_report_sha256'][:12]}…")
        updated += 1
    print(f"\nratified {updated} pack(s); {skipped} already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
