# ADR-0002: Ingest Layer Architecture

**Date:** 2026-05-12  
**Status:** Accepted

## Context

CORE needs a boundary that converts external information — text, code, scripture,
mathematical objects, audio — into CORE-native pressure before it enters the
field. The initial `core_ingest` design (from `core-ai`) proposed using a modern
LLM as the extraction engine for large document ingestion, on the basis that
current LLMs are strong at structured extraction from long documents.

The question was whether to port this design into `AssetOverflow/core`, scrap
it, or revise it.

## Decision

Port the structural elements of `core_ingest` into the `ingest/` layer, but
**replace the LLM extraction engine with a deterministic StructuralSegmenter**.

What is retained:
- `CandidateGeometricPressure` as the canonical pre-injection envelope
- Dual-path architecture: runtime ingest (transient) vs. durable ingest (governed)
- Content addressing via SHA-256 `pressure_id` and `semantic_key`
- `IngestCompiler` with three sequential gates: Provenance, Semantic, Governance
- `DeterminismClass` (D0–D4) and `ReviewLevel` embedded in packet type contracts
- `LearningArtifact` as the durable export form

What is rejected:
- LLM as extraction engine for document segmentation and SVO triple extraction

What is added:
- `StructuralSegmenter`: a D0/D1-class instrument per modality that segments
  documents at *form* boundaries (headings, verse markers, code delimiters,
  LaTeX boundaries) rather than semantic ones. Interpretation happens inside
  the field during propagation, not before injection.
- `SegmentManifold`: lightweight index mapping `semantic_key` → structural
  position in the source document, enabling provenance reconstruction.

## Rationale

Using an LLM as extractor introduces a **D3 (external unpinned) oracle** at the
only normalization site in the system. D3 packets cannot claim
`AUTO_ACCEPT_ELIGIBLE` status — enforced by the type contract — which means
every LLM-extracted claim requires human review before becoming pressure. This
defeats the utility at scale.

More fundamentally: an LLM doesn’t parse — it *interprets*. Its projection of
what a document means becomes silently embedded in the field state. That
violates **Semantic Rigor** (we own our semantics) and **Third Door** (we don’t
use external models to define our own representations).

Structural segmentation is deterministic and model-free. For Hebrew and Koine
Greek specifically, canonical verse/pericope boundaries are fixed and centuries
old — a D0 parser by definition.

Serves **Propagation-over-Mutation**: incoming claims don’t modify state;
they are proposed, validated, and either accepted as `LearningArtifact` objects
or rejected with a full audit trail.

Serves **Reconstruction-over-Storage**: the `SegmentManifold` stores enough
structured state to trace any vault recall back to its exact source provenance
span without storing full document copies.

## Consequences

- **Easier:** D0/D1 instruments dominate the ingest path, meaning the governance
  gates can wave through the majority of ingested content at scale without
  human review.
- **Harder:** Modality-specific `StructuralSegmenter` implementations must be
  built per content type. This is the right cost.
- **Forbidden:** LLMs, external NLP models, or any D3/D4 instrument producing
  `AUTO_ACCEPT_ELIGIBLE` packets — the `__post_init__` invariant on
  `CandidateGeometricPressure` makes this structurally impossible.

## Alternatives Considered

- **LLM extraction with human review of all output:** Rejected. Scales to zero.
- **General-purpose NLP library (spaCy, stanza) for SVO extraction:** Rejected.
  External libraries define the semantics. Third Door.
- **Scrap ingest layer entirely:** Rejected. The boundary is necessary. Without
  a governed injection point, external information enters the field without
  provenance, confidence, or governance metadata.
