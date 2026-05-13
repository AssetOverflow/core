# ADR-0012: `core_ingest` Governance Layer

**Status:** Accepted  
**Date:** 2026-05-13  
**Supersedes:** ADR-0002 (ingest layer design — archived, see below)

---

## Context

The current `ingest/gate.py` is the single normalization site: it accepts a token sequence, converts it to a versor via holonomy encoding, and injects it into the field. It does one thing and does it correctly. However, it has no concept of *where the input came from*, *how reliably it was produced*, or *whether it should be accepted at all* before touching the manifold.

As CORE grows — ingesting structured documents, biblical texts, code, mathematical objects, and eventually non-text modalities — the gate will be approached by inputs of radically different reliability classes. Without a pre-gate envelope layer, the gate has no choice but to accept everything equally. That is structurally unsound.

A previous design (`core_ingest` from the `core-ai` era, documented in ADR-0002) proposed using a large language model as the extraction engine for large document ingestion — parsing structure, extracting SVO triples, and chunking intelligently. This ADR supersedes that design and records the reason the LLM-extraction path was rejected.

---

## Decision

Add a `core_ingest/` package that sits **upstream of `ingest/gate.py`** as a pre-gate governance boundary. The gate itself is not modified.

### Why LLM Extraction Was Rejected

The entire CORE architecture is built on the principle that the injection gate is the single, deterministic normalization site. Inserting an LLM upstream introduces a D3 nondeterministic oracle into the only path that feeds that site.

The `DeterminismClass` system (see below) handles this correctly in isolation: a D3-proposed packet cannot claim `AUTO_ACCEPT_ELIGIBLE` status. But in practice this means every large document ingested through an LLM extraction path lands in `ARCHITECT_REVIEW_REQUIRED` territory — a human or second system must approve every extracted claim before it can become field pressure. This defeats the utility of the layer at any meaningful scale.

The deeper issue is architectural: an LLM does not merely *parse* a document — it *interprets* it. An SVO triple extracted by a language model is that model's projection of what it believes the document means. That interpretation is then silently embedded inside the field state. This violates Semantic Rigor: the vocabulary manifold is the only permitted semantic interpretation surface inside CORE.

**Rejected path:** LLM extraction engine → `CandidateGeometricPressure` → gate  
**Accepted path:** Deterministic `StructuralSegmenter` → `CandidateGeometricPressure` → gate

### The `StructuralSegmenter`

Large documents (PDFs, prose, code, biblical texts, mathematical objects) carry deterministic structural signals: headings, section breaks, paragraph boundaries, verse markers, code blocks, LaTeX delimiters. A D0/D1-class instrument that follows those structural signals produces candidate spans without interpretation.

- For prose: carves at heading and paragraph boundaries  
- For code: carves at function/class/block boundaries  
- For biblical texts: carves at canonical verse/pericope boundaries (fixed for centuries — inherently D0)  
- For mathematical objects: carves at LaTeX delimiter pairs  

Each span is tagged with its structural role (`§ heading`, `¶ body`, `⌥ code`, `✦ scripture`, `Σ math`) which maps to the `modality` and `kind` fields in `CandidateGeometricPressure`. The meaning of the span remains *inside the field* where it belongs.

### The `CandidateGeometricPressure` Envelope

Every piece of incoming information — regardless of source — is lifted into a typed, immutable, content-addressed envelope before the gate sees it:

```python
@dataclass(frozen=True)
class CandidateGeometricPressure:
    kind: str                          # structural role
    modality: str                      # medium (text, code, scripture, math, ...)
    provenance: tuple[SourceSpan, ...] # byte offsets, page, region, SHA-256 of source
    frontend_trace: FrontendTrace      # instrument identity + DeterminismClass
    confidence: float                  # bounded [0.0, 1.0]
    uncertainty: float                 # bounded [0.0, 1.0]
    payload_json: str                  # canonical JSON, normalized at construction
    pressure_id: str                   # SHA-256 over full canonical packet
    semantic_key: str                  # SHA-256 over semantic fields only
    review_level: ReviewLevel          # governance disposition
```

The `pressure_id` enables structural deduplication. The `semantic_key` enables convergent-evidence detection: two packets asserting the same semantic claim from independent sources share a `semantic_key` without being structural duplicates.

### The `DeterminismClass` System

| Class | Meaning | Auto-Accept Eligible? |
|---|---|---|
| D0 | Fully deterministic, pinned inputs and code | ✅ Yes |
| D1 | Deterministic with pinned external artifact | ✅ Yes |
| D2 | Nondeterministic but replay-captured | ❌ No |
| D3 | External unpinned model or API | ❌ No |
| D4 | Human / operator proposal | ❌ No |

A nondeterministic or unpinned frontend (D2–D4) is structurally forbidden from claiming `AUTO_ACCEPT_ELIGIBLE` status. This invariant is enforced in `CandidateGeometricPressure.__post_init__`, making it impossible to bypass at construction time.

### The `IngestCompiler` and Three-Gate Flow

The `IngestCompiler` processes batches of candidate packets through three sequential gates:

1. **`ProvenanceGate`** — verifies `SourceSpan` integrity and SHA-256 of source material
2. **`SemanticGate`** — verifies span completeness (no mid-sentence truncation, balanced delimiters, non-empty content)
3. **`GovernanceGate`** — applies `ReviewLevel` and `DeterminismClass` constraints; issues or blocks `LearningArtifact` export

The compiler simultaneously tracks structural deduplication by `pressure_id` and convergent-evidence accumulation by `semantic_key`. Accepted packets are exported as `LearningArtifact` objects for the durable learning path.

### The `SegmentManifold`

A lightweight index mapping `semantic_key` → structural position in the source document. Given a vault recall hit, the `SegmentManifold` traces back to the exact provenance span in the original document. This is `Reconstruction-over-Storage` extended to the pre-injection layer.

---

## Consequences

**Immediate:**
- `ingest/gate.py` is unchanged — it continues to accept `(32,)` multivectors and inject them
- `core_ingest/` is additive — it wraps before the gate without touching any existing layer
- D0/D1-dominant ingest paths (biblical texts, pinned corpora) can reach `AUTO_ACCEPT_ELIGIBLE` at scale without human review
- Every input to the system gains provenance, determinism class, and governance disposition as first-class typed data

**Future:**
- The `LearningArtifact` export path feeds the `train/` learning loop (ADR-0014) when that layer is built
- The `SegmentManifold` feeds cross-modal provenance tracing once non-text modalities are active (ADR-0013)

---

## ADR-0002 Archive Note

ADR-0002 (ingest layer design) described the original `core_ingest` concept from the `core-ai` era. The envelope design, `DeterminismClass` system, and governance gates from that ADR are preserved here. The LLM-as-extraction-engine component of that design is superseded and rejected. ADR-0002 is archived.
