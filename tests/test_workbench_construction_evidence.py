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


def test_dict_deserialization_success() -> None:
    payload = {
        "schema_version": "construction_evidence_v1",
        "turn_id": 12,
        "status": "recorded",
        "missing_reason": None,
        "problem_text": "Lena has 3 red marbles.",
        "proposals": [
            {
                "family_id": "fraction_decrease",
                "relation_type": "decrease",
                "candidate_organ": "assess_fraction_decrease",
                "status": "proposed",
                "evidence_spans": [{"start": 9, "end": 10, "text": "3"}],
                "role_obligations": [
                    {"role": "quantity", "required": True, "description": "amount"}
                ],
                "diagnostic_only": True,
                "serving_allowed": False,
            }
        ],
        "mentions": [
            {
                "mention_id": "m1",
                "kind": "quantity",
                "surface": "3",
                "span": {"start": 9, "end": 10, "text": "3"},
                "fact_id": "f1",
            }
        ],
        "bindings": [
            {
                "binding_type": "mention_binding",
                "source_mention_id": "m1",
                "target_mention_id": "m1",
                "evidence_spans": [{"start": 9, "end": 10, "text": "3"}],
            }
        ],
        "bound_relations": [
            {
                "relation_type": "decrease",
                "roles": [
                    {
                        "role": "quantity",
                        "target_id": "m1",
                        "evidence_spans": [{"start": 9, "end": 10, "text": "3"}],
                    }
                ],
                "evidence_spans": [{"start": 9, "end": 10, "text": "3"}],
            }
        ],
        "contract_assessments": [
            {
                "candidate_organ": "assess_fraction_decrease",
                "family_id": "fraction_decrease",
                "missing_bindings": [],
                "unresolved_hazards": [],
                "runnable": True,
                "explanation": "good to go",
                "evidence_spans": [{"start": 9, "end": 10, "text": "3"}],
            }
        ],
        "diagnostic_only": True,
        "serving_allowed": False,
    }

    @dataclass(frozen=True, slots=True)
    class EntryWithDict:
        turn_id: int
        construction_evidence: dict

    evidence = construction_evidence_from_journal_entry(EntryWithDict(12, payload))

    assert evidence.status == "recorded"
    assert evidence.turn_id == 12
    assert evidence.problem_text == "Lena has 3 red marbles."
    assert len(evidence.proposals) == 1
    assert evidence.proposals[0].family_id == "fraction_decrease"
    assert len(evidence.proposals[0].evidence_spans) == 1
    assert evidence.proposals[0].evidence_spans[0].text == "3"
    assert len(evidence.mentions) == 1
    assert evidence.mentions[0].mention_id == "m1"
    assert evidence.mentions[0].span.start == 9
    assert len(evidence.bindings) == 1
    assert evidence.bindings[0].binding_type == "mention_binding"
    assert len(evidence.bound_relations) == 1
    assert evidence.bound_relations[0].roles[0].target_id == "m1"
    assert len(evidence.contract_assessments) == 1
    assert evidence.contract_assessments[0].runnable is True


def test_dict_deserialization_span_mismatch_refuses() -> None:
    payload = {
        "schema_version": "construction_evidence_v1",
        "turn_id": 13,
        "status": "recorded",
        "missing_reason": None,
        "problem_text": "Lena has 3 red marbles.",
        "mentions": [
            {
                "mention_id": "m1",
                "kind": "quantity",
                "surface": "3",
                "span": {"start": 9, "end": 10, "text": "wrong"},  # text mismatch!
                "fact_id": "f1",
            }
        ],
    }

    @dataclass(frozen=True, slots=True)
    class EntryWithDict:
        turn_id: int
        construction_evidence: dict

    evidence = construction_evidence_from_journal_entry(EntryWithDict(13, payload))

    assert evidence.status == "missing_evidence"
    assert evidence.turn_id == 13
    assert "exact span validation failed" in evidence.missing_reason


def test_dict_deserialization_bad_schema_fails() -> None:
    payload = {
        "schema_version": "wrong_version_v2",
        "turn_id": 14,
        "status": "recorded",
        "problem_text": "hello",
    }

    @dataclass(frozen=True, slots=True)
    class EntryWithDict:
        turn_id: int
        construction_evidence: dict

    evidence = construction_evidence_from_journal_entry(EntryWithDict(14, payload))

    assert evidence.status == "missing_evidence"
    assert "unsupported schema version" in evidence.missing_reason
