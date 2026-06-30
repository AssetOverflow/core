# ADR-0012 — `core_ingest` Governance Layer

**Status:** Accepted  
**Date:** 2026-05-13  
**Supersedes:** ADR-0002 (Ingest Layer Design — original)

---

## Context

`ingest/gate.py` is the single normalization site in CORE: the one point where any input becomes a versor in Cl(4,1) and enters the field. That contract must be inviolable.

The original ingest design (ADR-0002) proposed using a large language model (LLM) as the heavy-lifting extraction engine for large documents — parsing structure, extracting SVO triples, and producing typed evidence packets. The idea was motivated by LLMs' demonstrated capability at document understanding and the desire to reduce hand-written parsing code.

This design was rejected after analysis. The root cause: an LLM upstream of the gate is a D3 nondeterministic oracle feeding the only normalization site in the system. More fundamentally, an LLM does not parse — it *interprets*. Its semantic projections would be silently embedded in the field state without provenance or determinism accountability. This violates both **Semantic Rigor** (exactness as a non-negotiable standard) and **Dual-Correction** (every forward claim must carry its own reliability metadata, not inherit opacity from an oracle).

---

## Decision

Add a `core_ingest/` layer upstream of `ingest/gate.py`. The gate is not modified.

### The `StructuralSegmenter` (D0 Extraction)

Every surface source is carved by a **deterministic, structure-aware segmenter** that operates on the *form* of the source, not its content. Form signals — headings, paragraph breaks, verse markers, code block delimiters, LaTeX boundaries — are deterministic. A segmenter following these boundaries produces content-addressed candidate spans without interpretation.

For Hebrew and Koine Greek, structural determinism is the natural condition. Canonical verse and pericope boundaries have been fixed for centuries. A parser following those boundaries is D0 by definition: fully deterministic, pinned inputs, no interpretation required.

The meaning of every span stays inside the versor field, where it belongs.

### `CandidateGeometricPressure`

Every candidate span is lifted into a `CandidateGeometricPressure` envelope — a frozen, immutable dataclass carrying:

- `kind` and `modality` — claim type and source medium
- `provenance` — tuple of `SourceSpan` records with byte offsets, page, region, and SHA-256 of the source
- `frontend_trace` — identity and `DeterminismClass` of the proposing instrument
- `confidence` and `uncertainty` — explicit probability fields in `[0.0, 1.0]`
- `payload_json` — structured claim content, normalized to canonical JSON on construction
- `pressure_id` — SHA-256 over the full canonical packet (structural deduplication)
- `semantic_key` — SHA-256 over semantic fields only (convergent-evidence detection)

Two packets with the same `semantic_key` assert the same claim from different provenance sources. The `IngestCompiler` surfaces this as a confidence signal.

### `DeterminismClass`

| Class | Meaning | Auto-Accept Eligible? |
|---|---|---|
| D0 | Fully deterministic, pinned inputs and code | ✅ |
| D1 | Deterministic with pinned external artifact | ✅ |
| D2 | Nondeterministic but replay-captured | ❌ |
| D3 | External unpinned model or API | ❌ |
| D4 | Human / operator proposal | ❌ |

A D2–D4 frontend is **structurally forbidden** from claiming `AUTO_ACCEPT_ELIGIBLE`. This invariant is enforced in `CandidateGeometricPressure.__post_init__` — it cannot be bypassed at construction time.

### `ReviewLevel`

Each candidate carries one of: `AUTO_REJECT`, `AUTO_ACCEPT_ELIGIBLE`, `OPERATOR_REVIEW_REQUIRED`, or `ARCHITECT_REVIEW_REQUIRED`.

### Three-Gate Validation (`IngestCompiler`)

```
CandidateGeometricPressure batch
    → ProvenanceGate    # SourceSpan integrity, SHA-256 of source material
    → SemanticGate      # span completeness, balanced delimiters, non-empty
    → GovernanceGate    # ReviewLevel, DeterminismClass, ReviewDecision overrides
    → ValidationReport  # per-packet disposition (not a transformed copy)
    → LearningArtifact  # accepted packets → train/ export path
```

The compiler produces a `ValidationReport` alongside the original immutable packet. It does not store a transformed copy — `Reconstruction-over-Storage` is observed.

### `SegmentManifold` (Index)

A lightweight index mapping `semantic_key` → structural position in the source document. Given a vault recall hit, the original provenance span can be recovered exactly. This extends `Reconstruction-over-Storage` to the pre-injection layer.

---

## Consequences

**Positive:**
- D0/D1-dominant input corpus means governance gates can wave through at scale without human review
- Provenance is cryptographically anchored at the boundary, not reconstructed later
- LLM interpretation is excluded by type contract, not convention
- `ingest/gate.py` is unchanged — zero risk to the normalization invariant

**Negative:**
- `StructuralSegmenter` implementations must be written per source type (prose, scripture, code, math)
- Semantic interpretation that an LLM would perform for free must now happen inside the field during propagation — which is where it belongs, but it means the field does more work

---

## Alternatives Considered

**LLM extraction (rejected):** D3 nondeterministic oracle feeding the normalization site. Semantic projections silently embedded. Violates Semantic Rigor and Dual-Correction. See Context above.

**Rule-based NLP pipelines (spaCy, stanza) (rejected):** These parse content, not form. They would produce interpreted outputs (POS tags, dependency arcs) that are still semantic projections, just deterministic ones. The field should own semantic interpretation. A D0 form segmenter is sufficient for the governance boundary.

**No pre-gate layer (rejected):** `ingest/gate.py` alone has no provenance tracking, no governance disposition, and no convergent-evidence detection. As the corpus grows (especially with Hebrew and Koine Greek depth texts), these become necessary for quality control of the learning path.
