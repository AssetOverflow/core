# Language Pack Contract

A CORE language pack is a deterministic, versioned manifold bundle that binds a
human language to the shared CORE semantic field.

## Goals

A valid pack must be able to:
- normalize incoming surface text into canonical language units
- lift canonical units into CORE-native pressure
- read back field state into grammatical surface language
- validate its own internal consistency
- participate in cross-language alignment probes

## Required Interfaces

Each pack must expose the following methods:

```python
def validate() -> ValidationReport
def normalize(text: str) -> NormalizedText
def analyze(text: str) -> LinguisticAnalysis
def lift(analysis: LinguisticAnalysis) -> CandidatePressureBatch
def readback(field_state, intent=None) -> SurfaceRealization
def anchors() -> list[AnchorRecord]
def probe() -> ProbeReport
```

## Required Data Surfaces

```text
packs/<lang>/
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
```

## Design Rules

### 1. Lemma-first
Tokens are surface realizations. Lemmas are the stable lexical unit. All lexical
identity, morphological variation, and semantic targeting is anchored to lemmas.

### 2. Deterministic normalization
Normalization must be deterministic and script-aware. Unicode normalization form,
punctuation strategy, and spacing rules are declared in `orthography.yaml` and
must produce identical output for identical input every time.

### 3. Native morphology
Morphology is part of meaning-bearing structure, not optional metadata. Hebrew
and Koine Greek morphology carries semantic load (stem, aspect, voice, agreement)
that must be represented in the morphology layer and available to the lift rules.

### 4. Shared field target
Semantic lift must target shared CORE field primitives. No pack may define
private or opaque semantic space that bypasses the shared field. A pack that
cannot express its semantics in shared field primitives is not a valid CORE pack.

### 5. Readback is owned locally
Each pack owns its articulation rules, grammatical agreement, and ambiguity
management. Readback does not reach into another pack's rules.

### 6. Alignment is explicit
Packs must publish anchor records in `anchors()` for cross-language coherence
checks. Anchors are formally scoped semantic equivalences with stated constraints
and tolerances — not approximate glosses.

## Validation Gates

A pack is not considered active because files exist. A pack becomes active only
when it passes all eight gates in order:

| Gate | Checks |
|------|--------|
| 1. Schema | All `.jsonl` records validate against their JSON Schema |
| 2. Lexical | All `lemma_id`s are unique; all `field_hooks` reference known primitives |
| 3. Morphology | All morphology records reference existing `lemma_id`s |
| 4. Lift | `lift()` produces valid `CandidatePressureBatch` for every probe input |
| 5. Readback | `readback()` produces grammatical surface output for every probe intent |
| 6. Determinism | `normalize()` and `lift()` produce identical output on repeated runs |
| 7. Alignment | `anchors()` returns at least the required trilingual anchor set |
| 8. Coverage | Required probe set passes without failures |

A gate failure blocks all subsequent gates. The pack is not partially active.
