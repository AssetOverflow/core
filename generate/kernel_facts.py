"""Kernel fact and provenance primitives for the substrate layer.

Tranche 1 — broad base-layer foundations.

Immutable, typed records that form the canonical substrate fact model.
All records are frozen dataclasses per the codebase immutability convention.

Provenance rules enforced at construction time:
  - ``problem_text`` facts require exact source spans
  - ``derived`` facts require input_fact_ids
  - Pack/world facts must not masquerade as problem text
  - ``speculative`` facts cannot be consumed by serving

These primitives are domain-agnostic — they are not tied to GSM8K or
any specific benchmark.  They provide the shared vocabulary that future
organs and the ProblemFrame IR will consume.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Literal, Union

# ---------------------------------------------------------------------------
# Provenance kinds — closed set per Tranche 1 brief.
# ---------------------------------------------------------------------------
PROVENANCE_KINDS: frozenset[str] = frozenset({
    "problem_text",
    "derived",
    "kernel_unit",
    "kernel_calendar",
    "kernel_math",
    "kernel_world_fact",
    "reviewed_pack",
    "speculative",
})

# Provenance kinds that require exact source spans.
_SPAN_REQUIRED_KINDS: frozenset[str] = frozenset({"problem_text"})

# Provenance kinds that require input_fact_ids.
_INPUT_REQUIRED_KINDS: frozenset[str] = frozenset({"derived"})

# Provenance kinds that are NOT allowed to carry source spans
# (they must not masquerade as problem text).
_SPAN_FORBIDDEN_KINDS: frozenset[str] = frozenset({
    "kernel_unit",
    "kernel_calendar",
    "kernel_math",
    "kernel_world_fact",
    "reviewed_pack",
})

# Fact types for SubstrateFact.
FACT_TYPES: frozenset[str] = frozenset({
    "grounded_scalar",
    "grounded_unit",
    "candidate_relation",
})


# ---------------------------------------------------------------------------
# Source span — exact character range in problem text.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class SourceSpan:
    """Exact character range in the original problem text.

    ``start`` and ``end`` are zero-indexed character offsets (inclusive start,
    exclusive end — matching Python slice semantics).  ``sentence_index`` is
    an optional zero-indexed sentence ordinal within the problem.
    """
    text: str
    start: int
    end: int
    sentence_index: int | None = None

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError(f"SourceSpan.start must be >= 0, got {self.start}")
        if self.end < self.start:
            raise ValueError(
                f"SourceSpan.end ({self.end}) must be >= start ({self.start})"
            )


# ---------------------------------------------------------------------------
# Kernel provenance — tracks origin of every substrate fact.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class KernelProvenance:
    """Provenance record for a substrate fact.

    Construction enforces:
      - ``kind`` must be in :data:`PROVENANCE_KINDS`
      - ``problem_text`` requires non-empty ``source_spans``
      - ``derived`` requires non-empty ``input_fact_ids``
      - Pack/world kinds must not carry source spans
    """
    kind: str
    source_spans: tuple[SourceSpan, ...] = ()
    input_fact_ids: tuple[str, ...] = ()
    pack_id: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in PROVENANCE_KINDS:
            raise ValueError(
                f"KernelProvenance.kind must be one of {sorted(PROVENANCE_KINDS)}, "
                f"got {self.kind!r}"
            )
        if self.kind in _SPAN_REQUIRED_KINDS and not self.source_spans:
            raise ValueError(
                f"Provenance kind {self.kind!r} requires non-empty source_spans"
            )
        if self.kind in _INPUT_REQUIRED_KINDS and not self.input_fact_ids:
            raise ValueError(
                f"Provenance kind {self.kind!r} requires non-empty input_fact_ids"
            )
        if self.kind in _SPAN_FORBIDDEN_KINDS and self.source_spans:
            raise ValueError(
                f"Provenance kind {self.kind!r} must not carry source_spans "
                f"(pack/world facts must not masquerade as problem text)"
            )


# ---------------------------------------------------------------------------
# Kernel hazard — annotates risk on a fact or surface.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class KernelHazard:
    """An ambiguity or risk annotation on a substrate fact or surface.

    The hazard registry (:mod:`language_packs.ambiguity_hazards`) owns the
    canonical set of hazard categories; this record carries a reference to
    one of them.
    """
    hazard_id: str
    category: str
    surface: str
    description: str
    context_required: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Grounded scalar — exact rational value from problem text or pack.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class GroundedScalar:
    """A grounded scalar quantity as an exact rational number.

    ``value`` is always a :class:`~fractions.Fraction` — never a float.
    The ``provenance`` tracks where this scalar came from.
    """
    fact_id: str
    surface: str
    value: Fraction
    provenance: KernelProvenance
    hazards: tuple[KernelHazard, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.value, Fraction):
            raise TypeError(
                f"GroundedScalar.value must be Fraction, got {type(self.value).__name__}"
            )


# ---------------------------------------------------------------------------
# Grounded unit — unit fact with dimension classification.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class GroundedUnit:
    """A unit fact with its dimension classification.

    ``dimension`` is the dimension class name (e.g., ``'length'``, ``'money'``).
    """
    fact_id: str
    surface: str
    dimension: str
    singular: str
    provenance: KernelProvenance


# ---------------------------------------------------------------------------
# Relation role — role in a candidate relation.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class RelationRole:
    """A typed role within a :class:`CandidateRelation`."""
    name: str
    required: bool
    description: str


# ---------------------------------------------------------------------------
# Candidate relation — typed relation between quantities/entities.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class CandidateRelation:
    """A typed candidate relation between quantities, entities, or both.

    This is a *candidate* — it annotates structure, not a solved answer.
    """
    relation_id: str
    relation_type: str
    roles: tuple[RelationRole, ...] = ()
    provenance: KernelProvenance | None = None
    hazards: tuple[KernelHazard, ...] = ()


# ---------------------------------------------------------------------------
# Span-grounded mention and binding primitives.
# ---------------------------------------------------------------------------
MentionKind = Literal["entity", "actor", "object", "quantity", "unit"]
BindingKind = Literal["quantity_entity", "quantity_unit"]


@dataclass(frozen=True, slots=True)
class GroundedMention:
    """A deterministic, source-grounded mention; never a derived answer."""

    mention_id: str
    kind: MentionKind
    surface: str
    span: SourceSpan
    fact_id: str | None = None


@dataclass(frozen=True, slots=True)
class MentionBinding:
    """A typed edge between two grounded mentions."""

    binding_id: str
    binding_type: BindingKind
    source_mention_id: str
    target_mention_id: str
    evidence_spans: tuple[SourceSpan, ...]


@dataclass(frozen=True, slots=True)
class BoundRole:
    """A declared relation role bound to a mention or substrate fact."""

    role: str
    target_id: str
    target_kind: str
    evidence_spans: tuple[SourceSpan, ...]


@dataclass(frozen=True, slots=True)
class BoundRelation:
    """A candidate relation whose roles have explicit grounded referents."""

    relation_id: str
    relation_type: str
    roles: tuple[BoundRole, ...]
    evidence_spans: tuple[SourceSpan, ...]


# ---------------------------------------------------------------------------
# Substrate fact — the canonical union wrapper.
# ---------------------------------------------------------------------------

# Content type union for SubstrateFact.
SubstrateContent = Union[GroundedScalar, GroundedUnit, CandidateRelation]


@dataclass(frozen=True, slots=True)
class SubstrateFact:
    """Union wrapper — the canonical substrate fact record.

    ``fact_type`` must be one of :data:`FACT_TYPES` and must match the
    runtime type of ``content``.

    ``speculative`` provenance facts are blocked from serving consumption —
    the provenance check is on the ``provenance`` field of this wrapper.
    """
    fact_id: str
    fact_type: str
    content: SubstrateContent
    provenance: KernelProvenance
    hazards: tuple[KernelHazard, ...] = ()

    def __post_init__(self) -> None:
        if self.fact_type not in FACT_TYPES:
            raise ValueError(
                f"SubstrateFact.fact_type must be one of {sorted(FACT_TYPES)}, "
                f"got {self.fact_type!r}"
            )
        # Verify content type matches fact_type.
        _CONTENT_TYPE_MAP = {
            "grounded_scalar": GroundedScalar,
            "grounded_unit": GroundedUnit,
            "candidate_relation": CandidateRelation,
        }
        expected = _CONTENT_TYPE_MAP[self.fact_type]
        if not isinstance(self.content, expected):
            raise TypeError(
                f"SubstrateFact with fact_type={self.fact_type!r} expects "
                f"{expected.__name__} content, got {type(self.content).__name__}"
            )

    @property
    def is_speculative(self) -> bool:
        """True if this fact has speculative provenance and must not be
        consumed by serving."""
        return self.provenance.kind == "speculative"
