from __future__ import annotations

from dataclasses import dataclass

from workbench.construction_evidence import (
    CONSTRUCTION_EVIDENCE_ABSENT,
    ConstructionEvidence,
    SourceSpanView,
    construction_evidence_from_journal_entry,
    missing_construction_evidence,
    span_is_exact,
)
from workbench.schemas import to_data


@dataclass(frozen=True, slots=True)
class _Entry:
    turn_id: int


def test_missing_construction_evidence_is_diagnostic_and_non_serving() -> None:
    evidence = missing_construction_evidence(7, "not persisted")

    assert evidence.schema_version == "construction_evidence_v1"
    assert evidence.turn_id == 7
    assert evidence.status == "missing_evidence"
    assert evidence.missing_reason == "not persisted"
    assert evidence.problem_text is None
    assert evidence.proposals == []
    assert evidence.mentions == []
    assert evidence.bindings == []
    assert evidence.bound_relations == []
    assert evidence.contract_assessments == []
    assert evidence.diagnostic_only is True
    assert evidence.serving_allowed is False


def test_construction_evidence_from_legacy_journal_entry_fails_closed() -> None:
    evidence = construction_evidence_from_journal_entry(_Entry(turn_id=3))

    assert evidence.status == "missing_evidence"
    assert evidence.turn_id == 3
    assert evidence.missing_reason == CONSTRUCTION_EVIDENCE_ABSENT
    assert evidence.diagnostic_only is True
    assert evidence.serving_allowed is False


def test_construction_evidence_to_data_serializes_dataclasses() -> None:
    payload = to_data(missing_construction_evidence(1, "absent"))

    assert payload == {
        "schema_version": "construction_evidence_v1",
        "turn_id": 1,
        "status": "missing_evidence",
        "missing_reason": "absent",
        "problem_text": None,
        "proposals": [],
        "mentions": [],
        "bindings": [],
        "bound_relations": [],
        "contract_assessments": [],
        "diagnostic_only": True,
        "serving_allowed": False,
    }


def test_span_is_exact_accepts_exact_slice() -> None:
    text = "Lena has 3 red marbles."
    assert span_is_exact(text, SourceSpanView(start=9, end=10, text="3")) is True


def test_span_is_exact_rejects_repaired_or_shifted_slice() -> None:
    text = "Lena has 3 red marbles."

    assert span_is_exact(text, SourceSpanView(start=9, end=10, text="three")) is False
    assert span_is_exact(text, SourceSpanView(start=8, end=9, text="3")) is False
    assert span_is_exact(text, SourceSpanView(start=-1, end=1, text="L")) is False
    assert span_is_exact(text, SourceSpanView(start=9, end=200, text="3")) is False
    assert span_is_exact(text, SourceSpanView(start=9, end=9, text="")) is False


def test_existing_construction_evidence_instance_round_trips() -> None:
    existing = ConstructionEvidence(
        schema_version="construction_evidence_v1",
        turn_id=11,
        status="recorded",
        missing_reason=None,
        problem_text="x",
        diagnostic_only=True,
        serving_allowed=False,
    )

    @dataclass(frozen=True, slots=True)
    class EntryWithPayload:
        turn_id: int
        construction_evidence: ConstructionEvidence

    assert construction_evidence_from_journal_entry(EntryWithPayload(11, existing)) is existing
