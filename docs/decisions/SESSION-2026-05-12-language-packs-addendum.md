# Session Log Addendum: 2026-05-12 — Language Pack Design

**Project:** AssetOverflow/core  
**Session type:** Architecture design addendum  
**Related ADR:** ADR-0005

---

## 21:02 — Language Pack Direction Confirmed

**What happened:**
The decision was made to move from general discussion of language integration
toward a formal, meticulous language pack contract for CORE.

**Why:**
The foundational languages are not optional output skins. They are part of
the native articulation and semantic design of the system. Therefore the next
clean artifact is a strict contract and scaffold, not an informal note.

**Decision:**
Create ADR-0005 and establish the `packs/` structure with shared contracts,
schemas, trilingual anchor templates, and initial `en`, `he`, and `el` pack
scaffolds.

---

## Design Notes Recorded

### Language choice rationale

The three languages were chosen because of the range of depth they bring:

- **English** is the default base (any language could serve this role in a
  custom CORE instance, but English is the default).
- **Hebrew** and **Koine Greek** are the depth languages. John 1:1–2: the
  universe itself was spoken into existence, and John articulated it in both
  Hebrew thought and Greek expression — almost certainly a nod from the Holy
  Spirit. The hidden layer of intelligence in CORE's vocabulary manifold is
  grounded in this. This is why and how CORE finds its truth and power in its
  design and communication — being primary, being a core.

### Pack design decisions

- Packs are **lemma-first**, not token-first.
- Morphology is **native** to the pack contract, especially for Hebrew and
  Koine Greek where morphology is semantically load-bearing.
- **Readback belongs to the pack**, not to a global postprocessor.
- Semantic lift must target **shared field primitives**.
- Pack activation is **gate-based**, not file-existence-based.
- Cross-language alignment is an **explicit probe surface**, not an
  emergent hope.
- Runtime boundary files raise `NotImplementedError` at unimplemented
  semantic edges — honest structure, not fake behavior.

### LLM as ingest extraction: rejected

Using a general-purpose LLM as the extraction engine for large document
ingest was considered and explicitly rejected. The reason: it introduces a
D3 nondeterministic oracle at the normalization site, and its interpretations
are silently embedded in the field state without provenance. Semantic Rigor
forbids this. The replacement is a deterministic, structure-aware segmenter
(StructuralSegmenter) that carves at form boundaries — document structure,
verse markers, code delimiters — not at interpreted content boundaries.
For Hebrew and Koine Greek this is even cleaner: canonical verse and pericope
boundaries have been fixed for centuries and constitute D0 segmentation.

---

## Build Order Established

| Batch | Contents |
|-------|----------|
| 1 | ADR-0005, this session addendum |
| 2 | `packs/common/` — contract, schemas, anchor template |
| 3 | `en`, `he`, `el` pack manifests and orthography files |
| 4 | Lexical seed sets — lemmas, morphology, frames, senses, probes |
| 5 | Runtime boundary files — lift rules, readback rules, validators |
