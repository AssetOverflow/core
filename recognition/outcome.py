"""RecognitionOutcome and all supporting types for teaching-derived recognition.

ADR-0143: the recognizer produces exactly one of four epistemic states —
EVIDENCED (admitted with full feature bundle), UNDETERMINED (shape refused),
CONTRADICTED (feature contradiction), AMBIGUOUS (unresolvable ambiguity).
VERIFIED and DECODED are downstream of substrate cross-reference work and
are never emitted here.

Every admitted bundle carries evidence on every feature.  No silent defaults.
Every refusal carries a typed reason naming exactly what is missing or wrong.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EvidenceSpan:
    """A contiguous span in the input token sequence that evidences a feature.

    ``start`` and ``end`` are token indices (half-open, i.e. tokens[start:end]).
    ``text`` is the verbatim text of that span for audit display; it is
    informational only and must not be used for matching logic.
    """

    start: int
    end: int
    text: str

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError(f"EvidenceSpan.start must be >= 0, got {self.start}")
        if self.end <= self.start:
            raise ValueError(
                f"EvidenceSpan.end must be > start, got start={self.start} end={self.end}"
            )

    def as_dict(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "text": self.text}


@dataclass(frozen=True, slots=True)
class NegativeEvidence:
    """Evidence derived from the *absence* of a token or marker in the input.

    Used for features like ``polarity=affirmative`` which are established by
    the absence of a negator rather than the presence of a positive marker.
    ``scope`` names the span over which the absence was confirmed (the full
    input token range by default); ``description`` is a human-readable
    explanation for audit.
    """

    scope_start: int
    scope_end: int
    description: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "scope_start": self.scope_start,
            "scope_end": self.scope_end,
            "description": self.description,
        }


# A feature evidence is either a positive span or a negative-evidence record.
FeatureEvidence = EvidenceSpan | NegativeEvidence


# ---------------------------------------------------------------------------
# Feature bundle
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BoundFeature:
    """A single feature in a recognized bundle: value + evidence.

    ``value`` is the typed feature value (str, int, float — never None on an
    admitted bundle).  ``evidence`` is the span or negative-evidence record
    that supports this value.  Both are required; there are no silent defaults.
    """

    name: str
    value: str | int | float
    evidence: FeatureEvidence

    def as_dict(self) -> dict[str, Any]:
        ev = (
            self.evidence.as_dict()
            if isinstance(self.evidence, (EvidenceSpan, NegativeEvidence))
            else {}
        )
        ev_type = (
            "span" if isinstance(self.evidence, EvidenceSpan) else "negative"
        )
        return {
            "name": self.name,
            "value": self.value,
            "evidence": ev,
            "evidence_type": ev_type,
        }


@dataclass(frozen=True, slots=True)
class FeatureBundle:
    """A complete set of bound features for a recognized proposition.

    ``features`` is a tuple of ``BoundFeature`` in canonical (sorted-by-name)
    order.  Canonical order ensures byte-identical serialization regardless
    of the order in which features were lifted during recognition.

    A bundle is only emitted when every expected feature slot is filled.
    Partial bundles must not be returned — the recognizer must either complete
    the bundle or refuse with a typed reason.
    """

    features: tuple[BoundFeature, ...]

    def __post_init__(self) -> None:
        names = [f.name for f in self.features]
        if len(names) != len(set(names)):
            raise ValueError(f"FeatureBundle has duplicate feature names: {names}")
        # Enforce canonical order.
        expected = sorted(names)
        if names != expected:
            raise ValueError(
                f"FeatureBundle.features must be in sorted-by-name order. "
                f"Got {names}, expected {expected}."
            )

    def get(self, name: str) -> BoundFeature | None:
        for f in self.features:
            if f.name == name:
                return f
        return None

    def as_dict(self) -> dict[str, Any]:
        return {"features": [f.as_dict() for f in self.features]}

    @classmethod
    def from_mapping(
        cls, mapping: dict[str, tuple[str | int | float, FeatureEvidence]]
    ) -> "FeatureBundle":
        """Convenience constructor: {name: (value, evidence)} → FeatureBundle.

        Sorts features by name to guarantee canonical order.
        """
        features = tuple(
            BoundFeature(name=k, value=v, evidence=ev)
            for k, (v, ev) in sorted(mapping.items())
        )
        return cls(features=features)


# ---------------------------------------------------------------------------
# Typed refusal reasons
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ShapeRefusal:
    """Layer 1 refusal: input token sequence does not match any derived pattern.

    ``nearest_patterns`` is an optional tuple of (teaching_set_id, distance)
    pairs for the closest patterns the recognizer tried — informational, not
    load-bearing.
    """

    reason: str
    nearest_patterns: tuple[tuple[str, float], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "layer": 1,
            "type": "shape",
            "reason": self.reason,
            "nearest_patterns": list(self.nearest_patterns),
        }


@dataclass(frozen=True, slots=True)
class FeatureEvidenceRefusal:
    """Layer 2 refusal: shape matched but a required feature has no evidence span.

    ``missing_feature`` names the feature slot that could not be filled.
    ``unrecognized_token`` is the token (if any) that was present but not in
    the decoded vocabulary for this feature — useful for teaching targeting.
    """

    missing_feature: str
    reason: str
    unrecognized_token: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "layer": 2,
            "type": "feature_evidence",
            "missing_feature": self.missing_feature,
            "reason": self.reason,
            "unrecognized_token": self.unrecognized_token,
        }


@dataclass(frozen=True, slots=True)
class FeatureConsistencyRefusal:
    """Layer 3 refusal: two evidence spans contradict each other on the same feature.

    ``feature`` names the feature where contradiction was detected.
    ``spans`` lists the conflicting evidence spans (at least two).
    """

    feature: str
    reason: str
    spans: tuple[EvidenceSpan, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "layer": 3,
            "type": "feature_consistency",
            "feature": self.feature,
            "reason": self.reason,
            "spans": [s.as_dict() for s in self.spans],
        }


RefusalReason = ShapeRefusal | FeatureEvidenceRefusal | FeatureConsistencyRefusal


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RecognitionProvenance:
    """Structured provenance record for a RecognitionOutcome.

    Every output — admitted or refused — carries provenance so it can be
    replayed, audited, and targeted by the teaching loop.

    Fields:
      mechanism         : always "anti_unification" for ADR-0143 outputs.
      teaching_set_id   : SHA-256 of the canonical teaching example set used
                          to derive the recognizer.  Byte-identical across runs
                          on the same examples (determinism guarantee).
      resolution_level  : "chunk" if chunk-level anti-unification succeeded;
                          "word" if word-level fallback was used; "shape" if
                          refused at shape level before feature lifting.
      replay_seed       : reserved for future use; empty string for Phase 1.
    """

    mechanism: str
    teaching_set_id: str
    resolution_level: str
    replay_seed: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "mechanism": self.mechanism,
            "teaching_set_id": self.teaching_set_id,
            "resolution_level": self.resolution_level,
            "replay_seed": self.replay_seed,
        }


# ---------------------------------------------------------------------------
# RecognitionOutcome
# ---------------------------------------------------------------------------

# Epistemic states the recognizer may emit (subset of the 14-state taxonomy).
# VERIFIED and DECODED are downstream of substrate cross-reference work and
# are never emitted by the recognizer itself.
EVIDENCED = "evidenced"
CONTRADICTED = "contradicted"
AMBIGUOUS = "ambiguous"
UNDETERMINED = "undetermined"

_VALID_STATES = frozenset({EVIDENCED, CONTRADICTED, AMBIGUOUS, UNDETERMINED})


@dataclass(frozen=True, slots=True)
class RecognitionOutcome:
    """The canonical output of the teaching-derived recognizer.

    Invariants:
      - If ``state == EVIDENCED``: ``proposition`` is a complete FeatureBundle
        with evidence on every feature; ``refusal_reason`` is None.
      - If ``state`` is a refusal class (UNDETERMINED / CONTRADICTED /
        AMBIGUOUS): ``proposition`` is None; ``refusal_reason`` is a typed
        RefusalReason.
      - ``provenance`` is always present regardless of state.
      - ``state`` is always one of the four values above.
    """

    state: str
    provenance: RecognitionProvenance
    proposition: FeatureBundle | None = None
    refusal_reason: RefusalReason | None = None

    def __post_init__(self) -> None:
        if self.state not in _VALID_STATES:
            raise ValueError(
                f"RecognitionOutcome.state must be one of {sorted(_VALID_STATES)}, "
                f"got {self.state!r}"
            )
        if self.state == EVIDENCED:
            if self.proposition is None:
                raise ValueError(
                    "RecognitionOutcome with state=EVIDENCED must have a proposition."
                )
            if self.refusal_reason is not None:
                raise ValueError(
                    "RecognitionOutcome with state=EVIDENCED must not have a refusal_reason."
                )
        else:
            if self.proposition is not None:
                raise ValueError(
                    f"RecognitionOutcome with state={self.state} must not have a proposition."
                )
            if self.refusal_reason is None:
                raise ValueError(
                    f"RecognitionOutcome with state={self.state} must have a refusal_reason."
                )

    @property
    def admitted(self) -> bool:
        return self.state == EVIDENCED

    @property
    def refused(self) -> bool:
        return self.state != EVIDENCED

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "provenance": self.provenance.as_dict(),
            "proposition": self.proposition.as_dict() if self.proposition else None,
            "refusal_reason": (
                self.refusal_reason.as_dict() if self.refusal_reason else None
            ),
        }


__all__ = [
    "AMBIGUOUS",
    "BoundFeature",
    "CONTRADICTED",
    "EVIDENCED",
    "EvidenceSpan",
    "FeatureBundle",
    "FeatureConsistencyRefusal",
    "FeatureEvidence",
    "FeatureEvidenceRefusal",
    "NegativeEvidence",
    "RecognitionOutcome",
    "RecognitionProvenance",
    "RefusalReason",
    "ShapeRefusal",
    "UNDETERMINED",
]
