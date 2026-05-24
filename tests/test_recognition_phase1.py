from __future__ import annotations

import json

from recognition.anti_unifier import DerivedRecognizer, derive_recognizer, recognize
from recognition.outcome import (
    EVIDENCED,
    UNDETERMINED,
    EvidenceSpan,
    FeatureBundle,
    NegativeEvidence,
    ShapeRefusal,
)


def _span(tokens: tuple[str, ...], start: int, end: int) -> EvidenceSpan:
    return EvidenceSpan(start=start, end=end, text=" ".join(tokens[start:end]))


def _bundle(tokens: tuple[str, ...], agent_span: tuple[int, int], count_span: tuple[int, int], unit_span: tuple[int, int], agent: str, count: int, unit: str) -> FeatureBundle:
    return FeatureBundle.from_mapping(
        {
            "agent": (agent, _span(tokens, *agent_span)),
            "count": (count, _span(tokens, *count_span)),
            "intentionality": ("possession", _span(tokens, 1 if tokens[0] in {"A", "The"} else 0, 3 if tokens[0] in {"A", "The"} else 2)),
            "modality": ("actual", NegativeEvidence(0, len(tokens), "no modal counter-marker present")),
            "polarity": ("+", NegativeEvidence(0, len(tokens), "no negator present")),
            "relation": ("has", _span(tokens, count_span[0] - 1, count_span[0])),
            "tense": ("present", _span(tokens, count_span[0] - 1, count_span[0])),
            "unit": (unit, _span(tokens, *unit_span)),
        }
    )


def _examples() -> list[tuple[tuple[str, ...], FeatureBundle]]:
    john = ("John", "has", "5", "apples")
    mary = ("Mary", "has", "3", "books")
    school = ("A", "school", "has", "100", "students")
    library = ("The", "library", "has", "12", "chairs")
    return [
        (john, _bundle(john, (0, 1), (2, 3), (3, 4), "John", 5, "apple")),
        (mary, _bundle(mary, (0, 1), (2, 3), (3, 4), "Mary", 3, "book")),
        (school, _bundle(school, (1, 2), (3, 4), (4, 5), "school", 100, "student")),
        (library, _bundle(library, (1, 2), (3, 4), (4, 5), "library", 12, "chair")),
    ]


def test_derive_recognizer_is_byte_identical_for_same_teaching_input() -> None:
    first = derive_recognizer(_examples())
    second = derive_recognizer(_examples())

    assert first == second
    assert first.to_json() == second.to_json()
    assert DerivedRecognizer.from_json(first.to_json()) == first
    assert json.dumps(json.loads(first.to_json()), sort_keys=True, separators=(",", ":")) == first.to_json()


def test_positive_heldout_is_admitted_with_full_feature_bundle_and_evidence_spans() -> None:
    recognizer = derive_recognizer(_examples())

    outcome = recognize(recognizer, ("A", "baker", "has", "24", "loaves"))

    assert outcome.state == EVIDENCED
    assert outcome.refusal_reason is None
    assert outcome.proposition is not None
    assert outcome.proposition.get("agent").value == "baker"  # type: ignore[union-attr]
    assert outcome.proposition.get("relation").value == "has"  # type: ignore[union-attr]
    assert outcome.proposition.get("count").value == 24  # type: ignore[union-attr]
    assert outcome.proposition.get("unit").value == "loaf"  # type: ignore[union-attr]
    assert outcome.proposition.get("polarity").value == "+"  # type: ignore[union-attr]
    assert outcome.proposition.get("modality").value == "actual"  # type: ignore[union-attr]
    assert outcome.proposition.get("tense").value == "present"  # type: ignore[union-attr]
    assert outcome.proposition.get("intentionality").value == "possession"  # type: ignore[union-attr]
    assert outcome.proposition.get("agent").evidence == EvidenceSpan(1, 2, "baker")  # type: ignore[union-attr]
    assert outcome.proposition.get("count").evidence == EvidenceSpan(3, 4, "24")  # type: ignore[union-attr]
    assert outcome.proposition.get("unit").evidence == EvidenceSpan(4, 5, "loaves")  # type: ignore[union-attr]


def test_negative_heldout_is_undetermined_with_shape_refusal() -> None:
    recognizer = derive_recognizer(_examples())

    outcome = recognize(recognizer, ("John", "gave", "5", "apples", "to", "Mary"))

    assert outcome.state == UNDETERMINED
    assert outcome.proposition is None
    assert isinstance(outcome.refusal_reason, ShapeRefusal)


def test_every_feature_in_admitted_bundle_has_non_none_evidence() -> None:
    recognizer = derive_recognizer(_examples())

    outcome = recognize(recognizer, ("A", "baker", "has", "24", "loaves"))

    assert outcome.proposition is not None
    for feature in outcome.proposition.features:
        assert feature.evidence is not None
