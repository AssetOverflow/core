"""L10 lived-life surface — read-only projection of the persisted always-on run.

The always-on heartbeat (``chat.always_on``) holds CORE alive over uptime and persists
its evidence to ``engine_state/lived_life.json`` (``write_lived_life``).  This module
projects that artifact into the read-only :class:`~workbench.schemas.LivedLife` model the
workbench renders, and fail-closes: a ``recorded`` surface must be CONSISTENT with the
persisted per-beat measurements — it can never claim the field stayed valid while a beat
breached the ``versor_condition`` ceiling (the wrong=0 analogue for the continuity
surface).

No engine math is re-implemented here.  The scalars (``versor_condition``, the closure
ceiling, the learning counts) are exactly what ``chat.always_on`` measured and persisted;
this module only re-projects and re-checks them.
"""

from __future__ import annotations

from typing import Any, Literal

from chat.always_on import CLOSURE_CEILING, LIVED_LIFE_SCHEMA_VERSION
from workbench.schemas import ArtifactRef, LivedLife, LivedLifeHeartbeat

ResumeStatus = Literal["would_resume", "substrate_changed", "unknown"]

_RESUME_SUMMARY: dict[ResumeStatus, str] = {
    "would_resume": "a reboot resumes this life — its identity matches the current substrate",
    "substrate_changed": "the substrate changed — a reboot would refuse (IdentityContinuityError)",
    "unknown": "resume verdict unavailable — the current substrate identity could not be recomputed",
}


def _resume_status(identity: str | None, current_identity: str | None) -> ResumeStatus:
    """The L11 reboot guarantee as a self-contained verdict: a reboot recomputes the engine
    identity and refuses if it differs from the persisted one, so ``would_resume`` ⟺ the
    persisted life's identity equals the current substrate identity."""
    if not identity or not current_identity:
        return "unknown"
    return "would_resume" if identity == current_identity else "substrate_changed"


def missing_lived_life(reason: str) -> LivedLife:
    """Honest absence — no always-on run has been persisted yet."""

    return LivedLife(
        schema_version="lived_life_v1",
        status="missing_evidence",
        missing_reason=reason,
        identity=None,
        heartbeats=0,
        closure_observed=False,
        closure_held=False,
        closure_ceiling=CLOSURE_CEILING,
        final_checkpoint_ok=False,
        converged=False,
        total_facts_consolidated=0,
        total_proposals_created=0,
        current_identity=None,
        resume_status="unknown",
        resume_summary=_RESUME_SUMMARY["unknown"],
        records=[],
        artifact=None,
    )


def validate(record: LivedLife) -> None:
    """Fail-closed honesty gate for a recorded lived-life surface.

    Every claim the surface makes must agree EXACTLY with the per-beat measurements it is
    built from, so the continuity card can never overstate the life:

      * each beat's ``field_valid`` agrees with ``versor_condition (None or < ceiling)``;
      * ``closure_observed`` agrees with "some beat observed a field";
      * ``closure_held`` agrees with "every OBSERVED versor_condition < ceiling";
      * ``heartbeats`` and the learning totals agree with the records;
      * ``converged`` agrees with "records exist and the final beat did no work".

    This is the wrong=0 analogue for the continuity surface: a tampered artifact (a beat
    whose ``field_valid`` lies about a breached ceiling, an inflated ``closure_held``, a
    miscounted total) makes ``validate`` raise rather than render a false claim.
    """

    if record.status != "recorded":
        return

    for beat in record.records:
        expected_valid = (
            beat.versor_condition is None
            or beat.versor_condition < record.closure_ceiling
        )
        if beat.field_valid != expected_valid:
            raise ValueError(
                f"lived-life beat {beat.tick}: field_valid={beat.field_valid} disagrees "
                f"with versor_condition vs ceiling "
                f"({beat.versor_condition} / {record.closure_ceiling:.3e})"
            )

    observed = [
        b.versor_condition for b in record.records if b.versor_condition is not None
    ]
    if record.closure_observed != bool(observed):
        raise ValueError(
            "lived-life closure_observed disagrees with the per-beat measurements"
        )
    if record.closure_held != all(vc < record.closure_ceiling for vc in observed):
        raise ValueError(
            "lived-life closure_held disagrees with the per-beat measurements"
        )

    if record.heartbeats != len(record.records):
        raise ValueError("lived-life heartbeats disagrees with the record count")
    if record.total_facts_consolidated != sum(
        b.facts_consolidated for b in record.records
    ):
        raise ValueError(
            "lived-life total_facts_consolidated disagrees with the records"
        )
    if record.total_proposals_created != sum(
        b.proposals_created for b in record.records
    ):
        raise ValueError(
            "lived-life total_proposals_created disagrees with the records"
        )

    expected_converged = bool(record.records) and not record.records[-1].did_work
    if record.converged != expected_converged:
        raise ValueError("lived-life converged disagrees with the final beat")

    expected_resume = _resume_status(record.identity, record.current_identity)
    if record.resume_status != expected_resume:
        raise ValueError(
            "lived-life resume_status disagrees with identity vs current_identity"
        )
    if record.resume_summary != _RESUME_SUMMARY[record.resume_status]:
        raise ValueError("lived-life resume_summary disagrees with resume_status")


def _coerce_heartbeat(raw: Any) -> LivedLifeHeartbeat:
    if not isinstance(raw, dict):
        raise ValueError("lived-life record must be an object")
    versor_condition = raw.get("versor_condition")
    return LivedLifeHeartbeat(
        tick=int(raw["tick"]),
        versor_condition=(
            None if versor_condition is None else float(versor_condition)
        ),
        field_valid=bool(raw["field_valid"]),
        facts_consolidated=int(raw["facts_consolidated"]),
        proposals_created=int(raw["proposals_created"]),
        pending_proposals=int(raw["pending_proposals"]),
        did_work=bool(raw["did_work"]),
    )


def lived_life_from_payload(
    raw: Any,
    *,
    artifact: ArtifactRef | None = None,
    current_identity: str | None = None,
) -> LivedLife:
    """Project a persisted ``lived_life.json`` payload into the validated read model.

    An unrecognized ``schema_version`` is honest absence (a forward/old artifact), not an
    error.  ``converged`` and ``resume_status`` are DERIVED here (not trusted from the
    artifact) — ``resume_status`` from the persisted ``identity`` vs the caller-supplied
    ``current_identity`` (the live substrate identity); ``validate`` then re-checks every
    artifact-sourced claim against the records.
    """

    if not isinstance(raw, dict):
        raise ValueError("lived_life artifact must be an object")
    if raw.get("schema_version") != LIVED_LIFE_SCHEMA_VERSION:
        return missing_lived_life(
            f"unrecognized lived_life schema_version: {raw.get('schema_version')!r}"
        )

    records = [_coerce_heartbeat(item) for item in raw.get("records", [])]
    identity = str(raw["identity"]) if raw.get("identity") else None
    resume_status = _resume_status(identity, current_identity)
    record = LivedLife(
        schema_version="lived_life_v1",
        status="recorded",
        missing_reason=None,
        identity=identity,
        heartbeats=int(raw.get("heartbeats", len(records))),
        closure_observed=bool(raw["closure_observed"]),
        closure_held=bool(raw["closure_held"]),
        closure_ceiling=float(raw.get("closure_ceiling", CLOSURE_CEILING)),
        final_checkpoint_ok=bool(raw["final_checkpoint_ok"]),
        converged=bool(records) and not records[-1].did_work,
        total_facts_consolidated=int(raw["total_facts_consolidated"]),
        total_proposals_created=int(raw["total_proposals_created"]),
        current_identity=current_identity,
        resume_status=resume_status,
        resume_summary=_RESUME_SUMMARY[resume_status],
        records=records,
        artifact=artifact,
    )
    validate(record)
    return record
