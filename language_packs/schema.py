"""
Schemas for CORE compiled linguistic manifolds.

A language pack is not a dataset. It is a deterministic, checksummed,
compiled linguistic manifold: lexical surfaces, morphology, grammar
attractors, cross-language resonances, and holonomy-level proof cases.

These schemas intentionally do not load corpora. They define the contract the
Supervised Seeding Epoch must satisfy before Hebrew and Koine Greek gates can
engage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Sequence


class LanguageRole(str, Enum):
    """Architectural role of a language pack in CORE-Logos."""

    OPERATIONAL_BASE = "operational_base"
    ARTICULATION_SURFACE = "articulation_surface"
    DEPTH_ROOT = "depth_root"
    DEPTH_RELATION = "depth_relation"


class OOVPolicy(str, Enum):
    """Out-of-vocabulary behavior for a pack."""

    FAIL_CLOSED = "fail_closed"
    TAGGED_FALLBACK = "tagged_fallback"
    PROPOSE_VOCAB_EXPANSION = "propose_vocab_expansion"


@dataclass(frozen=True, slots=True)
class LanguagePackManifest:
    """Pinned manifest for one compiled language pack."""

    pack_id: str
    language: str
    role: LanguageRole
    script: str
    normalization_policy: str
    source_manifest: str
    determinism_class: str
    checksum: str
    version: str = "1.0.0"
    gate_engaged: bool = False
    oov_policy: OOVPolicy = OOVPolicy.FAIL_CLOSED
    # Optional dual-checksum for the companion ``glosses.jsonl`` file.
    # When present, the loader verifies the bytes-on-disk match this
    # SHA-256 just like the lexicon checksum.  Absent on legacy packs
    # that ship no glosses (back-compat — never raised in that case).
    # Glosses are an additive overlay; bumping ``glosses_checksum`` does
    # NOT perturb the immutable ``checksum`` (lexicon seal).
    glosses_checksum: str | None = None
    # ADR-0084 — pack-level opt-in for the definitional layer.  When
    # True, every gloss entry must carry the extended schema
    # (``definitional_atoms``, ``predicates_invited``,
    # ``definition_version``) and pass the closure rule.  Default False
    # leaves every existing pack byte-identical.
    definitional_layer: bool = False

    def __post_init__(self) -> None:
        if not self.pack_id:
            raise ValueError("LanguagePackManifest.pack_id is required.")
        if not self.language:
            raise ValueError("LanguagePackManifest.language is required.")
        if not self.checksum:
            raise ValueError("LanguagePackManifest.checksum is required.")
        if self.role in {LanguageRole.DEPTH_ROOT, LanguageRole.DEPTH_RELATION}:
            if self.gate_engaged and self.oov_policy is not OOVPolicy.FAIL_CLOSED:
                raise ValueError(
                    "Depth packs must fail closed while gate_engaged=True; "
                    "unknown Hebrew/Greek surfaces must not collapse to a fallback point."
                )


@dataclass(frozen=True, slots=True)
class MorphologyEntry:
    """
    Morphological decomposition for a surface form.

    Ordering is load-bearing. For Semitic root morphology and Koine grammar,
    non-commutative composition means prefix/stem/inflection/suffix order must
    be preserved exactly.
    """

    morphology_id: str
    surface: str
    lemma: str
    language: str
    root: str | None = None
    prefix_chain: tuple[str, ...] = field(default_factory=tuple)
    stem: str | None = None
    inflection: Mapping[str, str] = field(default_factory=dict)
    suffix_chain: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.morphology_id:
            raise ValueError("MorphologyEntry.morphology_id is required.")
        if not self.surface:
            raise ValueError("MorphologyEntry.surface is required.")
        if not self.lemma:
            raise ValueError("MorphologyEntry.lemma is required.")
        if not self.language:
            raise ValueError("MorphologyEntry.language is required.")


@dataclass(frozen=True, slots=True)
class LexicalEntry:
    """One surface/lemma entry in a compiled linguistic manifold.

    `epistemic_status` follows ADR-0021: it is a *position in the
    revision graph*, not a source-trust tier.  The default is
    ``"speculative"`` per ADR-0021 §Schema impact: "transitions to
    COHERENT / CONTESTED / FALSIFIED only via the review path."  A pack
    lexicon row that wants to be admissible as evidence
    (``ADMISSIBLE_AS_EVIDENCE``) must declare
    ``"epistemic_status": "coherent"`` explicitly; the declaration is
    itself the curator's stamp.  Pack authority alone is not coherence
    judgment — defaulting unmarked rows to COHERENT would re-import the
    bias ADR-0021 refuses (see ``docs/truth_seeking_schema.md`` §1).
    """

    entry_id: str
    surface: str
    lemma: str
    language: str
    part_of_speech: str | None = None
    pos: str | None = None
    morphology_id: str | None = None
    morphology_tags: tuple[str, ...] = field(default_factory=tuple)
    semantic_domains: tuple[str, ...] = field(default_factory=tuple)
    manifold_point_checksum: str | None = None
    provenance_ids: tuple[str, ...] = field(default_factory=tuple)
    epistemic_status: str = "speculative"


@dataclass(frozen=True, slots=True)
class GrammarAttractor:
    """
    Structural grammar attractor seeded into the shared manifold.

    Morphology is operator composition. Semantic domain is attractor geometry.
    Alignment is resonance. This class represents the attractor layer only.
    """

    attractor_id: str
    language: str
    role: str
    description: str
    operator_order: tuple[str, ...] = field(default_factory=tuple)
    checksum: str | None = None


@dataclass(frozen=True, slots=True)
class AlignmentEdge:
    """Weighted directional resonance between entries or concepts."""

    source_id: str
    target_id: str
    relation: str
    weight: float
    evidence_ids: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("AlignmentEdge.weight must be in [0, 1].")


@dataclass(frozen=True, slots=True)
class HolonomyAlignmentCase:
    """
    Crown proof case for the three-language design.

    The language system succeeds when aligned canonical clauses produce nearby
    holonomies without flattening their distinctions. This is not token-level
    translation; it is dynamic field-path resonance.
    """

    case_id: str
    description: str
    source_refs: tuple[str, ...]
    pack_ids: tuple[str, ...]
    expected_relation: str
    negative_source_refs: tuple[str, ...] = field(default_factory=tuple)
    tolerance: float | None = None

    def __post_init__(self) -> None:
        if len(self.source_refs) < 2:
            raise ValueError("HolonomyAlignmentCase requires at least two source_refs.")
        if len(self.pack_ids) < 2:
            raise ValueError("HolonomyAlignmentCase requires at least two pack_ids.")
