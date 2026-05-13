"""
Canonical type definitions for the core_ingest governance layer.

All dataclasses are frozen and immutable. Packets are proposed, validated,
and exported — never modified in place.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from core_ingest.pressure import make_pressure_id, make_semantic_key


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Modality(str, Enum):
    """Source medium of the incoming signal."""
    TEXT   = "text"
    CODE   = "code"
    MATH   = "math"
    SCRIPTURE = "scripture"  # Hebrew / Koine Greek canonical texts
    VISION = "vision"
    AUDIO  = "audio"
    MOTOR  = "motor"


class DeterminismClass(str, Enum):
    """
    Reliability class of the proposing instrument.

    D0  Fully deterministic: pinned inputs, pinned code, identical output
        on every run. Auto-accept eligible.
    D1  Deterministic with a pinned external model artifact (e.g. a frozen
        embedding table at a fixed SHA). Auto-accept eligible.
    D2  Nondeterministic but replay-captured (output was logged and the log
        is being replayed). Requires review.
    D3  External unpinned model or API (live LLM call, external service).
        Requires review.
    D4  Human / operator proposal. Requires review.
    """
    D0 = "D0"
    D1 = "D1"
    D2 = "D2"
    D3 = "D3"
    D4 = "D4"

    @property
    def auto_accept_eligible(self) -> bool:
        return self in (DeterminismClass.D0, DeterminismClass.D1)


class ReviewLevel(str, Enum):
    AUTO_REJECT             = "auto_reject"
    AUTO_ACCEPT_ELIGIBLE    = "auto_accept_eligible"
    OPERATOR_REVIEW_REQUIRED  = "operator_review_required"
    ARCHITECT_REVIEW_REQUIRED = "architect_review_required"


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SourceSpan:
    """
    Exact location of a candidate within its source document.

    byte_start / byte_end  — byte offsets in the source bytestring
    page                   — page number (1-indexed), None for non-paginated
    region                 — structural region label (e.g. "heading", "body",
                             "verse:GEN.1.1", "code_block", "math_env")
    source_sha256          — SHA-256 hex digest of the full source document
                             at ingest time, for provenance anchoring
    """
    byte_start:   int
    byte_end:     int
    source_sha256: str
    page:         int | None = None
    region:       str | None = None

    def __post_init__(self) -> None:
        if self.byte_end <= self.byte_start:
            raise ValueError(
                f"SourceSpan byte_end ({self.byte_end}) must be > "
                f"byte_start ({self.byte_start})"
            )
        if len(self.source_sha256) != 64:
            raise ValueError(
                "source_sha256 must be a 64-character hex SHA-256 digest"
            )


@dataclass(frozen=True, slots=True)
class FrontendTrace:
    """
    Identity and determinism class of the instrument that proposed a packet.

    instrument_id    — stable, unique identifier for the proposing instrument
                       (e.g. "StructuralSegmenter/prose/v1",
                        "StructuralSegmenter/scripture-he/v1")
    determinism      — DeterminismClass of this instrument
    version          — semantic version string of the instrument
    """
    instrument_id:  str
    determinism:    DeterminismClass
    version:        str


# ---------------------------------------------------------------------------
# Candidate packet
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CandidateGeometricPressure:
    """
    A single proposed evidence packet at the input-to-pressure boundary.

    Every piece of incoming information — text, code, scripture, math —
    is lifted into this envelope before any validation or gate interaction.

    Fields
    ------
    kind         — claim type label (free string, e.g. "assertion",
                   "definition", "verse", "theorem")
    modality     — source medium (Modality enum)
    provenance   — tuple of SourceSpan records (at least one required)
    frontend     — identity + determinism class of the proposing instrument
    review_level — governance disposition for this packet
    confidence   — probability in [0.0, 1.0]: how confident the instrument is
    uncertainty  — probability in [0.0, 1.0]: explicit epistemic uncertainty
    lemma        — canonical surface form of the primary term (for semantic
                   key computation; empty string if not applicable)
    subject      — SVO subject (empty string if not applicable)
    verb         — SVO verb (empty string if not applicable)
    object_      — SVO object (empty string if not applicable)
    payload_json — structured claim content as a JSON string, normalized to
                   canonical (sorted-keys, no-whitespace) form on construction

    Computed in __post_init__
    -------------------------
    pressure_id  — SHA-256 over the full canonical packet (structural identity)
    semantic_key — SHA-256 over semantic fields only (claim-level identity;
                   two packets with the same semantic_key assert the same claim
                   regardless of provenance or instrument)

    Invariants (enforced at construction time)
    ------------------------------------------
    - A D2–D4 frontend is forbidden from claiming AUTO_ACCEPT_ELIGIBLE.
    - confidence and uncertainty must be in [0.0, 1.0].
    - provenance must be non-empty.
    - payload_json must be valid JSON.
    """
    kind:         str
    modality:     Modality
    provenance:   tuple[SourceSpan, ...]
    frontend:     FrontendTrace
    review_level: ReviewLevel
    confidence:   float
    uncertainty:  float
    lemma:        str = ""
    subject:      str = ""
    verb:         str = ""
    object_:      str = ""
    payload_json: str = "{}"

    # Computed — set by __post_init__, declared as class-level defaults
    # to satisfy the frozen dataclass protocol.
    pressure_id:  str = field(default="", init=False, compare=False, hash=False)
    semantic_key: str = field(default="", init=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        # Confidence bounds
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
        if not (0.0 <= self.uncertainty <= 1.0):
            raise ValueError(f"uncertainty must be in [0.0, 1.0], got {self.uncertainty}")

        # Provenance non-empty
        if not self.provenance:
            raise ValueError("provenance must contain at least one SourceSpan")

        # payload_json must be valid JSON; normalize to canonical form
        try:
            parsed = json.loads(self.payload_json)
            canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"payload_json is not valid JSON: {exc}") from exc
        if parsed == {}:
            raise ValueError("payload_json must contain at least one field")
        # Bypass frozen to set the normalized payload and computed fields
        object.__setattr__(self, "payload_json", canonical)

        # Governance invariant: D2-D4 cannot claim AUTO_ACCEPT_ELIGIBLE
        if (
            not self.frontend.determinism.auto_accept_eligible
            and self.review_level == ReviewLevel.AUTO_ACCEPT_ELIGIBLE
        ):
            raise ValueError(
                f"A {self.frontend.determinism} frontend cannot claim "
                "AUTO_ACCEPT_ELIGIBLE. Assign OPERATOR_REVIEW_REQUIRED or "
                "ARCHITECT_REVIEW_REQUIRED instead."
            )

        # Compute content-addressed identifiers
        pid = make_pressure_id(
            kind=self.kind,
            modality=self.modality.value,
            provenance=[
                {
                    "byte_start": s.byte_start,
                    "byte_end": s.byte_end,
                    "source_sha256": s.source_sha256,
                    "region": s.region,
                }
                for s in self.provenance
            ],
            frontend_id=self.frontend.instrument_id,
            frontend_version=self.frontend.version,
            determinism=self.frontend.determinism.value,
            review_level=self.review_level.value,
            confidence=self.confidence,
            uncertainty=self.uncertainty,
            lemma=self.lemma,
            subject=self.subject,
            verb=self.verb,
            object_=self.object_,
            payload_json=self.payload_json,
        )
        sk = make_semantic_key(
            kind=self.kind,
            modality=self.modality.value,
            lemma=self.lemma,
            subject=self.subject,
            verb=self.verb,
            object_=self.object_,
            payload_json=self.payload_json,
        )
        object.__setattr__(self, "pressure_id", pid)
        object.__setattr__(self, "semantic_key", sk)


# ---------------------------------------------------------------------------
# Validation outputs
# ---------------------------------------------------------------------------

class GateDisposition(str, Enum):
    ACCEPTED              = "accepted"
    REJECTED_PROVENANCE   = "rejected_provenance"
    REJECTED_SEMANTIC     = "rejected_semantic"
    REJECTED_GOVERNANCE   = "rejected_governance"
    REVIEW_REQUIRED       = "review_required"
    OVERRIDE_ACCEPTED     = "override_accepted"  # ReviewDecision authorized


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """
    Per-packet disposition from the IngestCompiler.

    The original packet is referenced by pressure_id, never mutated.
    warnings may contain 'semantic_convergence:<n>_prior_sources' when
    multiple independent packets share the same semantic_key.
    """
    pressure_id:       str
    semantic_key:      str
    disposition:       GateDisposition
    gate_failed:       str | None = None   # "provenance", "semantic", "governance"
    failure_reason:    str | None = None
    warnings:          tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """
    Full output of one IngestCompiler.compile() call.

    results        — one ValidationResult per input packet, in input order
    accepted_ids   — pressure_ids of packets that passed all three gates
    rejected_ids   — pressure_ids of rejected packets
    review_ids     — pressure_ids that require human/operator review
    """
    results:      tuple[ValidationResult, ...]
    accepted_ids: frozenset[str]
    rejected_ids: frozenset[str]
    review_ids:   frozenset[str]

    @property
    def acceptance_rate(self) -> float:
        total = len(self.results)
        return len(self.accepted_ids) / total if total else 0.0


@dataclass(frozen=True, slots=True)
class LearningArtifact:
    """
    A governance-cleared packet exported to the train/ layer.

    Carries the original immutable packet plus the validation result that
    authorized its export. The train/ layer must not modify either field.
    """
    packet:   CandidateGeometricPressure
    result:   ValidationResult


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    """
    An operator or architect decision to authorize a packet that would
    otherwise be blocked by a review_required disposition.

    Does not mutate the original packet. The IngestCompiler checks the
    authorized_ids set before applying the GovernanceGate rejection.
    """
    authorized_ids:  frozenset[str]   # pressure_ids authorized for acceptance
    authorized_by:   str              # operator or architect identifier
    reason:          str
