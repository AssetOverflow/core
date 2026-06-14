"""Lived Life surface — the read-only projection of a persisted always-on run.

These prove the surface is HONEST BY CONSTRUCTION: an absent artifact is honest absence,
a recorded artifact projects faithfully, and a TAMPERED artifact (a beat that lies about
its closure, an inflated aggregate, a miscounted total) makes ``validate`` raise rather
than render a false continuity claim. That fail-loud-on-tamper property is the wrong=0
analogue for the continuity surface (CLAUDE.md Schema-Defined Proof Obligations): each
mutation below would silently pass if the gate were decoration.
"""

from __future__ import annotations

import pytest

from chat.always_on import (
    AlwaysOnReport,
    HeartbeatRecord,
    serialize_report,
    write_lived_life,
)
from workbench import readers
from workbench.lived_life import (
    lived_life_from_payload,
    missing_lived_life,
    validate,
)
from workbench.schemas import LivedLife, LivedLifeHeartbeat


def _report() -> AlwaysOnReport:
    """A representative life: closure observed + held, learns on beat 0, at rest on beat 1."""
    records = (
        HeartbeatRecord(
            tick=0,
            versor_condition=8.2e-13,
            field_valid=True,
            facts_consolidated=1,
            proposals_created=0,
            pending_proposals=0,
            did_work=True,
        ),
        HeartbeatRecord(
            tick=1,
            versor_condition=8.2e-13,
            field_valid=True,
            facts_consolidated=0,
            proposals_created=0,
            pending_proposals=0,
            did_work=False,
        ),
    )
    return AlwaysOnReport(
        records=records,
        identity="sha256:lived-life-test",
        closure_observed=True,
        closure_held=True,
        final_checkpoint_ok=True,
        total_facts_consolidated=1,
        total_proposals_created=0,
    )


def test_missing_artifact_is_honest_absence() -> None:
    surface = missing_lived_life("no always-on run has been persisted yet")
    assert surface.status == "missing_evidence"
    assert surface.identity is None
    assert surface.heartbeats == 0
    # An absent life claims nothing.
    assert surface.closure_observed is False and surface.closure_held is False
    assert surface.records == []


def test_recorded_artifact_projects_faithfully() -> None:
    surface = lived_life_from_payload(serialize_report(_report()))
    assert surface.status == "recorded"
    assert surface.identity == "sha256:lived-life-test"
    assert surface.heartbeats == 2
    assert surface.closure_observed and surface.closure_held
    assert surface.total_facts_consolidated == 1
    # CONVERGED is derived from the records (final beat at rest), not trusted from bytes.
    assert surface.converged is True
    assert [b.tick for b in surface.records] == [0, 1]
    # No current identity supplied -> the resume verdict is honestly unknown.
    assert surface.resume_status == "unknown"


def test_resume_verdict_tracks_identity_vs_substrate() -> None:
    payload = serialize_report(_report())  # identity == "sha256:lived-life-test"
    # Matching substrate identity -> a reboot resumes THIS life.
    same = lived_life_from_payload(payload, current_identity="sha256:lived-life-test")
    assert same.resume_status == "would_resume"
    assert "resumes this life" in same.resume_summary
    # Changed substrate identity -> a reboot would refuse (IdentityContinuityError).
    changed = lived_life_from_payload(payload, current_identity="sha256:other")
    assert changed.resume_status == "substrate_changed"
    assert "refuse" in changed.resume_summary
    # No recomputable substrate identity -> honest unknown.
    unknown = lived_life_from_payload(payload, current_identity=None)
    assert unknown.resume_status == "unknown"


def test_reader_reads_persisted_artifact(tmp_path, monkeypatch) -> None:
    state_dir = tmp_path / "engine_state"
    state_dir.mkdir()
    write_lived_life(_report(), state_dir / "lived_life.json")
    monkeypatch.setattr(readers, "ENGINE_STATE_ROOT", state_dir)

    surface = readers.lived_life()
    assert surface.status == "recorded"
    assert surface.closure_held and surface.converged
    # The surface links to the raw artifact for provenance.
    assert surface.artifact is not None
    assert surface.artifact.kind == "lived_life"


def test_reader_absent_artifact(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(readers, "ENGINE_STATE_ROOT", tmp_path / "engine_state")
    surface = readers.lived_life()
    assert surface.status == "missing_evidence"


def test_unrecognized_schema_is_absence_not_error() -> None:
    payload = serialize_report(_report())
    payload["schema_version"] = "lived_life_v999"
    surface = lived_life_from_payload(payload)
    assert surface.status == "missing_evidence"
    assert "schema_version" in (surface.missing_reason or "")


# --- Non-vacuous tamper rejections: each mutation MUST make validate raise. ---


def test_tamper_field_valid_lies_about_breach_is_rejected() -> None:
    payload = serialize_report(_report())
    # A beat breaches the ceiling but still claims a valid field.
    payload["records"][0]["versor_condition"] = 5e-3
    payload["records"][0]["field_valid"] = True
    with pytest.raises(ValueError, match="field_valid"):
        lived_life_from_payload(payload)


def test_tamper_inflated_closure_held_is_rejected() -> None:
    payload = serialize_report(_report())
    # An honest beat breaches the ceiling, but the aggregate lies that closure held.
    payload["records"][0]["versor_condition"] = 5e-3
    payload["records"][0]["field_valid"] = False
    payload["closure_held"] = True
    with pytest.raises(ValueError, match="closure_held"):
        lived_life_from_payload(payload)


def test_tamper_closure_observed_is_rejected() -> None:
    payload = serialize_report(_report())
    # No beat observed a field, but the surface claims one did.
    for rec in payload["records"]:
        rec["versor_condition"] = None
        rec["field_valid"] = True
    payload["closure_observed"] = True
    payload["closure_held"] = True
    with pytest.raises(ValueError, match="closure_observed"):
        lived_life_from_payload(payload)


def test_tamper_miscounted_total_is_rejected() -> None:
    payload = serialize_report(_report())
    payload["total_facts_consolidated"] = 99  # records sum to 1
    with pytest.raises(ValueError, match="total_facts_consolidated"):
        lived_life_from_payload(payload)


def test_tamper_converged_mismatch_is_rejected() -> None:
    # Direct construction: a recorded surface whose `converged` contradicts the final beat.
    beats = [
        LivedLifeHeartbeat(
            tick=0,
            versor_condition=8.2e-13,
            field_valid=True,
            facts_consolidated=0,
            proposals_created=0,
            pending_proposals=0,
            did_work=True,  # final beat still working -> NOT converged
        )
    ]
    surface = LivedLife(
        schema_version="lived_life_v1",
        status="recorded",
        missing_reason=None,
        identity="sha256:x",
        heartbeats=1,
        closure_observed=True,
        closure_held=True,
        closure_ceiling=1e-6,
        final_checkpoint_ok=True,
        converged=True,  # lies: the final beat did work
        total_facts_consolidated=0,
        total_proposals_created=0,
        current_identity="sha256:x",
        resume_status="would_resume",
        resume_summary="a reboot resumes this life — its identity matches the current substrate",
        records=beats,
    )
    with pytest.raises(ValueError, match="converged"):
        validate(surface)


def test_tamper_resume_status_mismatch_is_rejected() -> None:
    # Direct construction: a surface that claims "would_resume" while the persisted identity
    # differs from the current substrate identity — a reboot would actually refuse.
    surface = LivedLife(
        schema_version="lived_life_v1",
        status="recorded",
        missing_reason=None,
        identity="sha256:persisted",
        heartbeats=0,
        closure_observed=False,
        closure_held=True,  # vacuously true with no observed field (passes the closure gate)
        closure_ceiling=1e-6,
        final_checkpoint_ok=True,
        converged=False,
        total_facts_consolidated=0,
        total_proposals_created=0,
        current_identity="sha256:current-DIFFERENT",
        resume_status="would_resume",  # lies: identities differ -> substrate_changed
        resume_summary="a reboot resumes this life — its identity matches the current substrate",
        records=[],
    )
    with pytest.raises(ValueError, match="resume_status"):
        validate(surface)


def test_persist_is_deterministic() -> None:
    report = _report()
    once = serialize_report(report)
    twice = serialize_report(report)
    assert once == twice
    # And the written bytes are stable (sorted keys), so the artifact is replay-citable.
    import json

    assert json.dumps(once, sort_keys=True) == json.dumps(twice, sort_keys=True)
