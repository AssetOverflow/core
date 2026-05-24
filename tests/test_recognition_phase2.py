from __future__ import annotations

import json
from recognition.anti_unifier import DerivedRecognizer, derive_recognizer, recognize
from recognition.outcome import (
    EVIDENCED,
    UNDETERMINED,
    CONTRADICTED,
    EvidenceSpan,
    FeatureBundle,
    NegativeEvidence,
    ShapeRefusal,
    FeatureEvidenceRefusal,
    FeatureConsistencyRefusal,
)

def _span(tokens: tuple[str, ...], start: int, end: int) -> EvidenceSpan:
    return EvidenceSpan(start=start, end=end, text=" ".join(tokens[start:end]))

def _examples() -> list[tuple[tuple[str, ...], FeatureBundle]]:
    # 1. "A baker has 24 loaves"
    c1 = ("A", "baker", "has", "24", "loaves")
    b1 = FeatureBundle.from_mapping({
        "agent": ("baker", _span(c1, 1, 2)),
        "count": (24, _span(c1, 3, 4)),
        "unit": ("loaf", _span(c1, 4, 5)),
        "relation": ("has", _span(c1, 2, 3)),
        "tense": ("present", _span(c1, 2, 3)),
        "polarity": ("+", NegativeEvidence(0, len(c1), "no negator present")),
        "modality": ("actual", NegativeEvidence(0, len(c1), "no modal counter-marker present")),
        "intentionality": ("possession", _span(c1, 1, 3)),
    })

    # 2. "A baker does not have 24 loaves"
    c2 = ("A", "baker", "does", "not", "have", "24", "loaves")
    b2 = FeatureBundle.from_mapping({
        "agent": ("baker", _span(c2, 1, 2)),
        "count": (24, _span(c2, 5, 6)),
        "unit": ("loaf", _span(c2, 6, 7)),
        "relation": ("have", _span(c2, 4, 5)),
        "tense": ("present", _span(c2, 2, 3)),
        "polarity": ("-", _span(c2, 3, 4)),
        "modality": ("actual", NegativeEvidence(0, len(c2), "no modal counter-marker present")),
        "intentionality": ("possession", _span(c2, 1, 5)),
    })

    # 3. "A baker may have 24 loaves"
    c3 = ("A", "baker", "may", "have", "24", "loaves")
    b3 = FeatureBundle.from_mapping({
        "agent": ("baker", _span(c3, 1, 2)),
        "count": (24, _span(c3, 4, 5)),
        "unit": ("loaf", _span(c3, 5, 6)),
        "relation": ("have", _span(c3, 3, 4)),
        "tense": ("present", _span(c3, 2, 3)),
        "polarity": ("+", NegativeEvidence(0, len(c3), "no negator present")),
        "modality": ("possibility", _span(c3, 2, 3)),
        "intentionality": ("possession", _span(c3, 1, 4)),
    })

    # 4. "A baker had 24 loaves"
    c4 = ("A", "baker", "had", "24", "loaves")
    b4 = FeatureBundle.from_mapping({
        "agent": ("baker", _span(c4, 1, 2)),
        "count": (24, _span(c4, 3, 4)),
        "unit": ("loaf", _span(c4, 4, 5)),
        "relation": ("had", _span(c4, 2, 3)),
        "tense": ("past", _span(c4, 2, 3)),
        "polarity": ("+", NegativeEvidence(0, len(c4), "no negator present")),
        "modality": ("actual", NegativeEvidence(0, len(c4), "no modal counter-marker present")),
        "intentionality": ("possession", _span(c4, 1, 3)),
    })

    # 5. "A baker will have 24 loaves"
    c5 = ("A", "baker", "will", "have", "24", "loaves")
    b5 = FeatureBundle.from_mapping({
        "agent": ("baker", _span(c5, 1, 2)),
        "count": (24, _span(c5, 4, 5)),
        "unit": ("loaf", _span(c5, 5, 6)),
        "relation": ("have", _span(c5, 3, 4)),
        "tense": ("future", _span(c5, 2, 3)),
        "polarity": ("+", NegativeEvidence(0, len(c5), "no negator present")),
        "modality": ("actual", NegativeEvidence(0, len(c5), "no modal counter-marker present")),
        "intentionality": ("possession", _span(c5, 1, 4)),
    })

    return [(c1, b1), (c2, b2), (c3, b3), (c4, b4), (c5, b5)]

def test_derive_recognizer_phase2_is_byte_identical() -> None:
    first = derive_recognizer(_examples())
    second = derive_recognizer(_examples())

    assert first == second
    assert first.to_json() == second.to_json()
    assert DerivedRecognizer.from_json(first.to_json()) == first
    assert json.dumps(json.loads(first.to_json()), sort_keys=True, separators=(",", ":")) == first.to_json()

def test_positive_cases_admitted() -> None:
    recognizer = derive_recognizer(_examples())

    # Case 1
    o1 = recognize(recognizer, ("A", "baker", "has", "24", "loaves"))
    assert o1.state == EVIDENCED
    assert o1.refusal_reason is None
    assert o1.proposition is not None
    assert o1.proposition.get("agent").value == "baker"
    assert o1.proposition.get("agent").evidence == EvidenceSpan(1, 2, "baker")
    assert o1.proposition.get("count").value == 24
    assert o1.proposition.get("count").evidence == EvidenceSpan(3, 4, "24")
    assert o1.proposition.get("unit").value == "loaf"
    assert o1.proposition.get("unit").evidence == EvidenceSpan(4, 5, "loaves")
    assert o1.proposition.get("relation").value == "has"
    assert o1.proposition.get("relation").evidence == EvidenceSpan(2, 3, "has")
    assert o1.proposition.get("tense").value == "present"
    assert o1.proposition.get("tense").evidence == EvidenceSpan(2, 3, "has")
    assert o1.proposition.get("polarity").value == "+"
    assert isinstance(o1.proposition.get("polarity").evidence, NegativeEvidence)
    assert o1.proposition.get("modality").value == "actual"
    assert isinstance(o1.proposition.get("modality").evidence, NegativeEvidence)
    assert o1.proposition.get("intentionality").value == "possession"
    assert o1.proposition.get("intentionality").evidence == EvidenceSpan(1, 3, "baker has")

    # Case 2
    o2 = recognize(recognizer, ("A", "baker", "does", "not", "have", "24", "loaves"))
    assert o2.state == EVIDENCED
    assert o2.refusal_reason is None
    assert o2.proposition is not None
    assert o2.proposition.get("agent").value == "baker"
    assert o2.proposition.get("count").value == 24
    assert o2.proposition.get("unit").value == "loaf"
    assert o2.proposition.get("relation").value == "have"
    assert o2.proposition.get("relation").evidence == EvidenceSpan(4, 5, "have")
    assert o2.proposition.get("tense").value == "present"
    assert o2.proposition.get("tense").evidence == EvidenceSpan(2, 3, "does")
    assert o2.proposition.get("polarity").value == "-"
    assert o2.proposition.get("polarity").evidence == EvidenceSpan(3, 4, "not")
    assert o2.proposition.get("modality").value == "actual"
    assert isinstance(o2.proposition.get("modality").evidence, NegativeEvidence)
    assert o2.proposition.get("intentionality").value == "possession"
    assert o2.proposition.get("intentionality").evidence == EvidenceSpan(1, 5, "baker does not have")

    # Case 3
    o3 = recognize(recognizer, ("A", "baker", "may", "have", "24", "loaves"))
    assert o3.state == EVIDENCED
    assert o3.refusal_reason is None
    assert o3.proposition is not None
    assert o3.proposition.get("agent").value == "baker"
    assert o3.proposition.get("count").value == 24
    assert o3.proposition.get("unit").value == "loaf"
    assert o3.proposition.get("relation").value == "have"
    assert o3.proposition.get("relation").evidence == EvidenceSpan(3, 4, "have")
    assert o3.proposition.get("tense").value == "present"
    assert o3.proposition.get("tense").evidence == EvidenceSpan(2, 3, "may")
    assert o3.proposition.get("polarity").value == "+"
    assert isinstance(o3.proposition.get("polarity").evidence, NegativeEvidence)
    assert o3.proposition.get("modality").value == "possibility"
    assert o3.proposition.get("modality").evidence == EvidenceSpan(2, 3, "may")
    assert o3.proposition.get("intentionality").value == "possession"
    assert o3.proposition.get("intentionality").evidence == EvidenceSpan(1, 4, "baker may have")

    # Case 4
    o4 = recognize(recognizer, ("A", "baker", "had", "24", "loaves"))
    assert o4.state == EVIDENCED
    assert o4.refusal_reason is None
    assert o4.proposition is not None
    assert o4.proposition.get("agent").value == "baker"
    assert o4.proposition.get("count").value == 24
    assert o4.proposition.get("unit").value == "loaf"
    assert o4.proposition.get("relation").value == "had"
    assert o4.proposition.get("relation").evidence == EvidenceSpan(2, 3, "had")
    assert o4.proposition.get("tense").value == "past"
    assert o4.proposition.get("tense").evidence == EvidenceSpan(2, 3, "had")
    assert o4.proposition.get("polarity").value == "+"
    assert isinstance(o4.proposition.get("polarity").evidence, NegativeEvidence)
    assert o4.proposition.get("modality").value == "actual"
    assert isinstance(o4.proposition.get("modality").evidence, NegativeEvidence)
    assert o4.proposition.get("intentionality").value == "possession"
    assert o4.proposition.get("intentionality").evidence == EvidenceSpan(1, 3, "baker had")

    # Case 5
    o5 = recognize(recognizer, ("A", "baker", "will", "have", "24", "loaves"))
    assert o5.state == EVIDENCED
    assert o5.refusal_reason is None
    assert o5.proposition is not None
    assert o5.proposition.get("agent").value == "baker"
    assert o5.proposition.get("count").value == 24
    assert o5.proposition.get("unit").value == "loaf"
    assert o5.proposition.get("relation").value == "have"
    assert o5.proposition.get("relation").evidence == EvidenceSpan(3, 4, "have")
    assert o5.proposition.get("tense").value == "future"
    assert o5.proposition.get("tense").evidence == EvidenceSpan(2, 3, "will")
    assert o5.proposition.get("polarity").value == "+"
    assert isinstance(o5.proposition.get("polarity").evidence, NegativeEvidence)
    assert o5.proposition.get("modality").value == "actual"
    assert isinstance(o5.proposition.get("modality").evidence, NegativeEvidence)
    assert o5.proposition.get("intentionality").value == "possession"
    assert o5.proposition.get("intentionality").evidence == EvidenceSpan(1, 4, "baker will have")

def test_adversarial_refusals() -> None:
    recognizer = derive_recognizer(_examples())

    # Case 6: "John gave 5 apples to Mary" -> Layer 1 ShapeRefusal (wrong relation)
    o6 = recognize(recognizer, ("John", "gave", "5", "apples", "to", "Mary"))
    assert o6.state == UNDETERMINED
    assert o6.proposition is None
    assert isinstance(o6.refusal_reason, ShapeRefusal)

    # Case 7: "A baker has loaves" -> Layer 2 FeatureEvidenceRefusal (missing count)
    o7 = recognize(recognizer, ("A", "baker", "has", "loaves"))
    assert o7.state == UNDETERMINED
    assert o7.proposition is None
    assert isinstance(o7.refusal_reason, FeatureEvidenceRefusal)
    assert o7.refusal_reason.missing_feature == "count"

    # Case 8: "A baker has 24 loaves and 12 loaves" -> Layer 3 FeatureConsistencyRefusal (count contradiction)
    o8 = recognize(recognizer, ("A", "baker", "has", "24", "loaves", "and", "12", "loaves"))
    assert o8.state == CONTRADICTED
    assert o8.proposition is None
    assert isinstance(o8.refusal_reason, FeatureConsistencyRefusal)
    assert o8.refusal_reason.feature == "count"
    assert len(o8.refusal_reason.spans) == 2
    assert o8.refusal_reason.spans[0] == EvidenceSpan(3, 4, "24")
    assert o8.refusal_reason.spans[1] == EvidenceSpan(6, 7, "12")

def test_byte_identity_across_runs() -> None:
    recognizer = derive_recognizer(_examples())
    cases = [
        ("A", "baker", "has", "24", "loaves"),
        ("A", "baker", "does", "not", "have", "24", "loaves"),
        ("A", "baker", "may", "have", "24", "loaves"),
        ("A", "baker", "had", "24", "loaves"),
        ("A", "baker", "will", "have", "24", "loaves"),
        ("John", "gave", "5", "apples", "to", "Mary"),
        ("A", "baker", "has", "loaves"),
        ("A", "baker", "has", "24", "loaves", "and", "12", "loaves"),
    ]

    for case in cases:
        out1 = recognize(recognizer, case)
        out2 = recognize(recognizer, case)
        assert out1 == out2
        
        # Serialize and deserialize to ensure exact identical JSON payload
        d1 = out1.as_dict()
        d2 = out2.as_dict()
        assert d1 == d2
        
        j1 = json.dumps(d1, sort_keys=True, separators=(",", ":"))
        j2 = json.dumps(d2, sort_keys=True, separators=(",", ":"))
        assert j1 == j2
