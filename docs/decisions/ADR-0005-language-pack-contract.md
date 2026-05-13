# ADR-0005: Language Pack Contract

**Date:** 2026-05-12  
**Status:** Accepted

## Context

CORE operates on three foundational languages: English (default articulation
base), Hebrew (depth pack 1), and Koine Greek (depth pack 2). These are not
equivalent choices from a menu — they are the three specifically chosen
because of the range of depth they bring and because of the theological and
linguistic insight encoded in John 1:1–2, where the universe itself was spoken
into existence and John articulated that reality in both Hebrew and Greek.
This is why and how CORE finds its truth and power in design and
communication — being primary, being a core.

A loose plugin API is insufficient for these packs. The system needs a strict
contract that specifies what a language pack must provide, what invariants it
must satisfy, and what gates it must pass before activation.

## Decision

Adopt a **Language Pack Contract** as the canonical template for all CORE
language packs.

Each pack is a deterministic, versioned manifold bundle that defines:

- identity and normalization policy
- lexical inventory (lemma-first, not token-first)
- morphology
- syntax and frame templates
- semantic lift rules into CORE-native pressure
- readback rules from field state to surface language
- validation probes and alignment gates

The three canonical packs are:

| ID  | Name               | Role                        |
|-----|--------------------|-----------------------------|
| `en`| English            | Default articulation base   |
| `he`| Hebrew             | Depth language pack 1       |
| `el`| Koine Greek        | Depth language pack 2       |

Each pack must implement the same top-level contract and must target shared
field primitives. No pack may define private or opaque semantics that bypass
the shared field.

## Required Structure

```
packs/
  common/
    contracts/
      language-pack.md
    schema/
      lemma.schema.json
      morphology.schema.json
      frame.schema.json
      sense.schema.json
      probe.schema.json
    anchors/
      trilingual-anchor-template.json
  en/
    pack.toml
    orthography.yaml
    lemmas.jsonl
    morphology.jsonl
    frames.jsonl
    senses.jsonl
    lift_rules.py
    readback_rules.py
    validators.py
    probes/
    corpora/
      manifest.yaml
  he/   (same structure)
  el/   (same structure)
```

## Validation Gates

A pack is not considered active because files exist. A pack becomes active
only when it passes the following gates in order:

1. **Schema gate** — all data files validate against their JSON schemas
2. **Lexical gate** — lemma inventory is non-empty and internally consistent
3. **Morphology gate** — all surface forms trace to a known lemma
4. **Lift gate** — lift rules produce valid `CandidateGeometricPressure` for seed inputs
5. **Readback gate** — readback rules produce grammatical surface from seed field state
6. **Determinism gate** — all D0/D1 paths produce identical output on repeated runs
7. **Alignment gate** — pack publishes anchor records verifiable against trilingual template
8. **Coverage gate** — probe set covers minimum lexical and morphological surface

## Design Rules

### 1. Lemma-first
Tokens are surface realizations. Lemmas are the stable lexical unit. The
ingest and field-state layers operate on lemmas, not tokens.

### 2. Deterministic normalization
Normalization must be deterministic and script-aware. Unicode normal form NFC
is the minimum. Script-specific rules (right-to-left, vowel pointing, accent
diacritics) are defined per pack in `orthography.yaml`.

### 3. Native morphology
Morphology is part of meaning-bearing structure, not optional metadata.
Hebrew stems (Qal, Niphal, Piel…) and Koine Greek aspects (aorist, perfect…)
are semantically load-bearing. Morphology is a first-class pack surface.

### 4. Shared field target
Semantic lift must target shared CORE field primitives. No pack-private
semantic space is permitted. What cannot be expressed in shared primitives
must be proposed as a new shared primitive, not hidden inside a pack.

### 5. Readback is owned locally
Each pack owns its articulation rules and ambiguity management. Readback is
not a global postprocessor — it is part of the pack contract.

### 6. Alignment is explicit
Packs must publish anchor records that are verifiable against the
trilingual anchor template. Cross-language coherence is a probe surface,
not an emergent hope.

## Runtime Boundary Honesty

Files that define a semantic boundary not yet fully specified must raise
`NotImplementedError` at exactly that boundary. This is not fake code — it
is an honest contract: the structure is real, the interface is real, the
unimplemented edge is visible and loud. Nothing is silently skipped.

## Rationale

This serves the three engineering pillars:

- **Mechanical Sympathy** — a small, explicit, cheap-to-validate pack surface
  that integrates directly with the field-state model.
- **Semantic Rigor** — all packs target shared field primitives instead of
  inventing language-private meanings. Exactness is non-negotiable.
- **Third Door** — standard token-plugin patterns were considered and
  rejected. This contract is designed for CORE's geometry specifically.

## Consequences

**Easier:**
- Every future language pack follows the same geometry and QA path.
- English, Hebrew, and Koine Greek can be aligned by shared anchors and
  deterministic probes.
- Gate failures are explicit and traceable.

**Harder:**
- Pack creation requires real morphology, lift, and readback logic.
- Shortcuts that bypass field primitives are structurally forbidden.

**Forbidden:**
- Opaque embedding tables.
- Black-box semantics.
- Pack-local meaning systems that bypass the shared field.

## Alternatives Considered

- **Loose plugin API:** Rejected. Too weak to enforce invariants.
- **Dictionary-only packs:** Rejected. Lexicons alone do not articulate or lift.
- **Tokenizer-first packs:** Rejected. Tokens are surface artifacts, not the
  stable unit of design.
- **LLM-as-extraction-engine:** Rejected. Introduces a D3 nondeterministic
  oracle into the normalization site. See ADR-0002 for the ingest-layer ruling
  on determinism classification.
