# ADR-0015 — Language Packs as Compiled Linguistic Manifolds

**Status:** Accepted  
**Date:** 2026-05-13

---

## Context

CORE's language philosophy is not localization. English, Hebrew, and Koine Greek
serve distinct architectural roles in CORE-Logos:

| Language | Role |
|---|---|
| English | Operational base and articulation surface |
| Hebrew | Depth-root language: root morphology, semantic compression, creation-word density |
| Koine Greek | Depth-relation language: Logos precision, case/aspect/voice/mood, clause relation |

The existing `sensorium/adapters/text.py` scaffold mounted `en`, `he`, and `grc`,
but the packs were only token lookup wrappers. That is insufficient for CORE.
A language pack must not be a dataset or a translation table. It must be a
compiled linguistic manifold.

---

## Decision

A CORE language pack is a deterministic, checksummed, compiled linguistic
manifold containing:

- a manifest with language role, script, normalization policy, source manifest,
  determinism class, checksum, gate state, and OOV policy;
- lexical entries and morphology entries;
- grammar attractors;
- cross-language resonance edges;
- holonomy alignment cases proving that aligned clauses produce coherent field
  path resonance.

## Terminology Boundary

This distinction is mandatory:

| Term | Meaning |
|---|---|
| Vocabulary point / manifold point | Position in the field; surface token entry |
| Transition rotor | Operator between points, constructed by algebra |
| Persona motor | Field-bias operator |
| Grammar attractor | Structural pressure seeded from recurring linguistic form |

Vocabulary entries are not transition rotors. Conflating point and operator is
an algebraic category error. The vocabulary may store multivectors/null points;
rotor construction belongs to the algebra layer.

## OOV Policy

Unknown surfaces must not silently collapse to a shared point.

| Pack role | OOV behavior |
|---|---|
| English operational/articulation | Tagged fallback may be used during early operation |
| Hebrew depth-root | Fail closed during and after seeding unless explicit expansion path is active |
| Koine Greek depth-relation | Fail closed during and after seeding unless explicit expansion path is active |
| Post-seeding expansion | OOV creates a vocab-expansion proposal; it is not projected silently |

Returning the same `e1` point for every unknown Hebrew or Greek form erases the
distinctions those languages exist to preserve; it is anti-Logos.

## Morphology / Semantics / Alignment

Morphology is operator composition. Semantic domain is attractor geometry.
Alignment is resonance. These must not be collapsed into one multiplication.

For Hebrew, composition order is load-bearing:

```text
V_surface = (((V_root · M_stem) · M_inflection) · M_affix_chain)
```

For Koine Greek, the pack should compose lemma anchors with case/aspect/voice/
mood/clause-role operators. The grammar relation is structural, not metadata.

Semantic domains seed attractors rather than becoming opaque morphology factors.
Cross-language alignment is a weighted graph, not a translation table.

## Crown Proof: Holonomy Resonance

Token-level alignment is necessary but insufficient. The decisive proof of the
three-language design is dynamic:

```text
holonomy(hebrew canonical clause)
  resonates with
holonomy(koine greek canonical clause)
  and maps coherently to
holonomy(english articulation clause)
```

Aligned clauses should produce nearby/coherent holonomies without flattening
their distinctions. Unrelated clauses should remain geometrically distinct.
Word-order changes should change holonomy. This is the CORE-Logos proof that
language packs preserve ordered field paths rather than merely mapping tokens.

The first holonomy alignment cases should be small and exact: Logos, beginning,
light, life, spirit, truth, covenant, grace, kingdom, creation.

---

## Consequences

**Positive:**
- Prevents future agents from treating language packs as datasets.
- Gives Hebrew and Koine Greek concrete architectural roles.
- Prevents silent OOV collapse in depth languages.
- Establishes holonomy-level resonance as the validation gate.

**Negative:**
- Requires a real Supervised Seeding Epoch before Hebrew/Greek gates engage.
- Requires deterministic morphology and grammar scaffolds before depth packs are
  operational.
- Requires carefully pinned canonical texts and checksums for D0 ingestion.

---

## Implementation Order

1. Terminology and schema foundation (`language_packs/schema.py`).
2. Pack roles and OOV policy in `sensorium`.
3. Split text adapters into English, Hebrew, Koine Greek specializations.
4. Add grammar scaffold artifacts.
5. Add tri-language resonance graph.
6. Add holonomy resonance proof cases.

No LLM extraction may feed the gate. Structural segmentation only.
