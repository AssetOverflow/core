"""Deterministic Phase 1 anti-unification over taught token sequences."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from recognition.outcome import (
    EVIDENCED,
    UNDETERMINED,
    BoundFeature,
    EvidenceSpan,
    FeatureBundle,
    FeatureEvidence,
    NegativeEvidence,
    RecognitionOutcome,
    RecognitionProvenance,
    ShapeRefusal,
)

TokenSequence = Sequence[str]
Scalar = str | int | float


@dataclass(frozen=True, slots=True)
class Constant:
    token: str

    def as_dict(self) -> dict[str, str]:
        return {"kind": "constant", "token": self.token}


@dataclass(frozen=True, slots=True)
class TypedSlot:
    feature_name: str
    slot_type: str
    min_width: int = 1
    max_width: int = 1
    ignored_prefix_tokens: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "ignored_prefix_tokens": list(self.ignored_prefix_tokens),
            "kind": "typed_slot",
            "max_width": self.max_width,
            "min_width": self.min_width,
            "slot_type": self.slot_type,
        }


PatternElement = Constant | TypedSlot


@dataclass(frozen=True, slots=True)
class DerivedRecognizer:
    pattern: tuple[PatternElement, ...]
    teaching_set_id: str
    constant_features: Mapping[str, Scalar]
    absent_features: Mapping[str, Scalar]

    def as_dict(self) -> dict[str, Any]:
        return {
            "absent_features": dict(sorted(self.absent_features.items())),
            "constant_features": dict(sorted(self.constant_features.items())),
            "pattern": [_pattern_element_as_dict(element) for element in self.pattern],
            "teaching_set_id": self.teaching_set_id,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_json(cls, payload: str) -> "DerivedRecognizer":
        raw = json.loads(payload)
        return cls(
            pattern=tuple(_pattern_element_from_dict(element) for element in raw["pattern"]),
            teaching_set_id=str(raw["teaching_set_id"]),
            constant_features=dict(raw["constant_features"]),
            absent_features=dict(raw["absent_features"]),
        )


def derive_recognizer(examples: Sequence[tuple[TokenSequence, FeatureBundle]]) -> DerivedRecognizer:
    if not examples:
        raise ValueError("derive_recognizer requires at least one teaching example")

    normalized = tuple((tuple(tokens), bundle) for tokens, bundle in examples)
    teaching_set_id = _teaching_set_id(tokens for tokens, _bundle in normalized)
    feature_names = _feature_names(normalized)
    slot_names = _slot_feature_names(normalized, feature_names)
    absent_features = _absent_uniform_features(normalized, feature_names, slot_names)

    relation = _uniform_feature_value(normalized, "relation")
    relation_token = str(relation)
    anchors = tuple(_single_token_index(tokens, relation_token) for tokens, _bundle in normalized)

    prefix_widths = tuple(anchor for anchor in anchors)
    suffix_widths = tuple(len(tokens) - anchor - 1 for (tokens, _bundle), anchor in zip(normalized, anchors))
    if min(prefix_widths) < 1:
        raise ValueError("agent slot must contain at least one token")
    if set(suffix_widths) != {2}:
        raise ValueError("Phase 1 expects count and unit slots after the relation anchor")

    constant_features = {"relation": relation}
    ignored_prefix_tokens = _ignored_prefix_tokens(normalized, "agent")
    pattern: tuple[PatternElement, ...] = (
        TypedSlot(
            feature_name="agent",
            slot_type=_slot_type(normalized, "agent"),
            min_width=min(prefix_widths),
            max_width=max(prefix_widths),
            ignored_prefix_tokens=ignored_prefix_tokens,
        ),
        Constant(relation_token),
        TypedSlot(feature_name="count", slot_type=_slot_type(normalized, "count")),
        TypedSlot(feature_name="unit", slot_type=_slot_type(normalized, "unit")),
    )
    return DerivedRecognizer(
        pattern=pattern,
        teaching_set_id=teaching_set_id,
        constant_features=constant_features,
        absent_features=absent_features,
    )


def recognize(recognizer: DerivedRecognizer, token_sequence: TokenSequence) -> RecognitionOutcome:
    tokens = tuple(token_sequence)
    provenance = RecognitionProvenance(
        mechanism="anti_unification",
        teaching_set_id=recognizer.teaching_set_id,
        resolution_level="chunk",
        replay_seed="",
    )
    matches = _match_pattern(recognizer.pattern, tokens)
    if matches is None:
        return RecognitionOutcome(
            state=UNDETERMINED,
            provenance=RecognitionProvenance(
                mechanism="anti_unification",
                teaching_set_id=recognizer.teaching_set_id,
                resolution_level="shape",
                replay_seed="",
            ),
            refusal_reason=ShapeRefusal(
                reason=f"shape_mismatch:{_shape_description(recognizer.pattern)}"
            ),
        )

    feature_evidence: dict[str, tuple[Scalar, FeatureEvidence]] = {}
    for feature_name, value in recognizer.constant_features.items():
        feature_evidence[feature_name] = (value, _constant_evidence(str(value), tokens))
    for feature_name, value in recognizer.absent_features.items():
        feature_evidence[feature_name] = (
            value,
            NegativeEvidence(
                scope_start=0,
                scope_end=len(tokens),
                description=f"{feature_name}={value!r} evidenced by absence of taught counter-marker",
            ),
        )
    for slot, span in matches.items():
        value, evidence = _lift_slot(slot, tokens, span)
        feature_evidence[slot.feature_name] = (value, evidence)

    proposition = FeatureBundle.from_mapping(feature_evidence)
    return RecognitionOutcome(
        state=EVIDENCED,
        provenance=provenance,
        proposition=proposition,
        refusal_reason=None,
    )


def _feature_names(examples: Sequence[tuple[tuple[str, ...], FeatureBundle]]) -> tuple[str, ...]:
    names = tuple(feature.name for feature in examples[0][1].features)
    for _tokens, bundle in examples[1:]:
        if tuple(feature.name for feature in bundle.features) != names:
            raise ValueError("all teaching bundles must expose the same feature set")
    return names


def _slot_feature_names(
    examples: Sequence[tuple[tuple[str, ...], FeatureBundle]], feature_names: tuple[str, ...]
) -> frozenset[str]:
    slots = []
    for name in feature_names:
        evidences = tuple(_feature(bundle, name).evidence for _tokens, bundle in examples)
        if all(isinstance(evidence, EvidenceSpan) for evidence in evidences):
            values = tuple(_feature(bundle, name).value for _tokens, bundle in examples)
            if len(set(values)) > 1:
                slots.append(name)
    return frozenset(slots)


def _absent_uniform_features(
    examples: Sequence[tuple[tuple[str, ...], FeatureBundle]],
    feature_names: tuple[str, ...],
    slot_names: frozenset[str],
) -> dict[str, Scalar]:
    absent: dict[str, Scalar] = {}
    for name in feature_names:
        if name in slot_names or name == "relation":
            continue
        feature_values = tuple(_feature(bundle, name).value for _tokens, bundle in examples)
        if len(set(feature_values)) == 1:
            absent[name] = feature_values[0]
    return absent


def _uniform_feature_value(examples: Sequence[tuple[tuple[str, ...], FeatureBundle]], name: str) -> Scalar:
    values = tuple(_feature(bundle, name).value for _tokens, bundle in examples)
    if len(set(values)) != 1:
        raise ValueError(f"feature must be uniform in Phase 1: {name}")
    return values[0]


def _feature(bundle: FeatureBundle, name: str) -> BoundFeature:
    feature = bundle.get(name)
    if feature is None:
        raise ValueError(f"missing feature in teaching bundle: {name}")
    return feature


def _slot_type(examples: Sequence[tuple[tuple[str, ...], FeatureBundle]], name: str) -> str:
    values = tuple(_feature(bundle, name).value for _tokens, bundle in examples)
    if all(isinstance(value, int) for value in values):
        return "int"
    if all(isinstance(value, float) for value in values):
        return "float"
    return "str"


def _ignored_prefix_tokens(examples: Sequence[tuple[tuple[str, ...], FeatureBundle]], name: str) -> tuple[str, ...]:
    ignored = set()
    for tokens, bundle in examples:
        evidence = _feature(bundle, name).evidence
        if isinstance(evidence, EvidenceSpan):
            ignored.update(token.lower() for token in tokens[: evidence.start])
    return tuple(sorted(ignored))


def _single_token_index(tokens: tuple[str, ...], token: str) -> int:
    indexes = [index for index, candidate in enumerate(tokens) if candidate == token]
    if len(indexes) != 1:
        raise ValueError(f"constant anchor must occur exactly once: {token!r}")
    return indexes[0]


def _teaching_set_id(token_sequences: Iterable[tuple[str, ...]]) -> str:
    canonical = json.dumps(sorted(token_sequences), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _match_pattern(pattern: tuple[PatternElement, ...], tokens: tuple[str, ...]) -> dict[TypedSlot, tuple[int, int]] | None:
    def walk(index: int, cursor: int, spans: dict[TypedSlot, tuple[int, int]]) -> dict[TypedSlot, tuple[int, int]] | None:
        if index == len(pattern):
            return spans if cursor == len(tokens) else None
        element = pattern[index]
        if isinstance(element, Constant):
            if cursor < len(tokens) and tokens[cursor] == element.token:
                return walk(index + 1, cursor + 1, spans)
            return None

        remaining_min = _minimum_width(pattern[index + 1 :])
        max_end = min(cursor + element.max_width, len(tokens) - remaining_min)
        for end in range(cursor + element.min_width, max_end + 1):
            next_spans = dict(spans)
            next_spans[element] = (cursor, end)
            matched = walk(index + 1, end, next_spans)
            if matched is not None:
                return matched
        return None

    return walk(0, 0, {})


def _minimum_width(pattern: Sequence[PatternElement]) -> int:
    return sum(1 if isinstance(element, Constant) else element.min_width for element in pattern)


def _lift_slot(slot: TypedSlot, tokens: tuple[str, ...], span: tuple[int, int]) -> tuple[Scalar, EvidenceSpan]:
    raw_tokens = tokens[span[0] : span[1]]
    start = span[0]
    if slot.ignored_prefix_tokens and raw_tokens and raw_tokens[0].lower() in slot.ignored_prefix_tokens:
        raw_tokens = raw_tokens[1:]
        start += 1
    if not raw_tokens:
        raise ValueError(f"slot {slot.feature_name!r} had no evidence tokens after prefix removal")

    text = " ".join(raw_tokens)
    if slot.slot_type == "int":
        if len(raw_tokens) != 1 or not raw_tokens[0].isdigit():
            raise ValueError(f"slot {slot.feature_name!r} expected one integer token")
        return int(raw_tokens[0]), EvidenceSpan(start=start, end=start + 1, text=raw_tokens[0])
    if slot.slot_type == "float":
        if len(raw_tokens) != 1:
            raise ValueError(f"slot {slot.feature_name!r} expected one float token")
        return float(raw_tokens[0]), EvidenceSpan(start=start, end=start + 1, text=raw_tokens[0])
    if slot.feature_name == "unit":
        return _singularize(raw_tokens[-1]), EvidenceSpan(start=span[1] - 1, end=span[1], text=raw_tokens[-1])
    return text, EvidenceSpan(start=start, end=span[1], text=text)


def _constant_evidence(value: str, tokens: tuple[str, ...]) -> EvidenceSpan:
    for index, token in enumerate(tokens):
        if token == value:
            return EvidenceSpan(start=index, end=index + 1, text=token)
    raise ValueError(f"constant feature had no evidence in matched token sequence: {value!r}")


def _singularize(token: str) -> str:
    lowered = token.lower()
    if lowered.endswith("ves") and len(lowered) > 3:
        return lowered[:-3] + "f"
    if lowered.endswith("ies") and len(lowered) > 3:
        return lowered[:-3] + "y"
    if lowered.endswith("s") and len(lowered) > 1:
        return lowered[:-1]
    return lowered


def _shape_description(pattern: tuple[PatternElement, ...]) -> str:
    pieces = []
    for element in pattern:
        if isinstance(element, Constant):
            pieces.append(repr(element.token))
        else:
            pieces.append(f"<{element.feature_name}:{element.slot_type}[{element.min_width},{element.max_width}]>")
    return " ".join(pieces)


def _pattern_element_as_dict(element: PatternElement) -> dict[str, Any]:
    return element.as_dict()


def _pattern_element_from_dict(raw: Mapping[str, Any]) -> PatternElement:
    if raw["kind"] == "constant":
        return Constant(token=str(raw["token"]))
    if raw["kind"] == "typed_slot":
        return TypedSlot(
            feature_name=str(raw["feature_name"]),
            slot_type=str(raw["slot_type"]),
            min_width=int(raw["min_width"]),
            max_width=int(raw["max_width"]),
            ignored_prefix_tokens=tuple(str(token) for token in raw.get("ignored_prefix_tokens", ())),
        )
    raise ValueError(f"unknown pattern element kind: {raw['kind']!r}")


__all__ = [
    "Constant",
    "DerivedRecognizer",
    "TypedSlot",
    "derive_recognizer",
    "recognize",
]
