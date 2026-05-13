# Language Pack Contract

A CORE language pack is a deterministic, versioned manifold bundle that binds
a human language to the shared CORE semantic field.

## Goals

A valid pack must be able to:

- Normalize incoming surface text into canonical language units.
- Lift canonical units into CORE-native `CandidateGeometricPressure`.
- Read back field state into grammatical surface language.
- Validate its own internal consistency through the gate sequence.
- Participate in cross-language alignment probes via published anchor records.

## Required Public Interface

Each pack's `validators.py` must expose:

```python
def validate() -> ValidationReport: ...
```

Each pack's `lift_rules.py` must expose:

```python
def lift(analysis: LinguisticAnalysis) -> CandidatePressureBatch: ...
```

Each pack's `readback_rules.py` must expose:

```python
def readback(field_state, intent: dict | None = None) -> SurfaceRealization: ...
```

These are not optional. A pack that cannot implement one of these boundaries
must raise `NotImplementedError` at that boundary explicitly. Nothing is
silently skipped.

## Required Data Surfaces

| File                  | Purpose                                           |
|-----------------------|---------------------------------------------------|
| `pack.toml`           | Pack identity, version, activation flags          |
| `orthography.yaml`    | Script, normalization, spacing, punctuation rules |
| `lemmas.jsonl`        | Lemma inventory (lemma-first)                     |
| `morphology.jsonl`    | Surface forms per lemma with feature bundles      |
| `frames.jsonl`        | Predicate frame templates                         |
| `senses.jsonl`        | Sense records mapping lemmas to field targets     |
| `lift_rules.py`       | Deterministic lift into field primitives          |
| `readback_rules.py`   | Deterministic articulation from field state       |
| `validators.py`       | Gate-sequence validation logic                    |
| `probes/`             | Deterministic probe sets for each gate            |
| `corpora/manifest.yaml` | Curated, licensed corpus source manifest        |

## Design Rules

### 1. Lemma-first
Tokens are surface realizations. Lemmas are the stable lexical unit.
The field-state layer operates on lemmas, not tokens.

### 2. Deterministic normalization
Normalization must be deterministic and script-aware. Unicode NFC is the
minimum baseline. Script-specific rules are defined in `orthography.yaml`.

### 3. Native morphology
Morphology is a first-class pack surface, not optional metadata.
Hebrew stems and Koine Greek aspects are semantically load-bearing and
must be represented in `morphology.jsonl` with explicit feature bundles.

### 4. Shared field target
Semantic lift must target shared CORE field primitives.
No pack-private semantic space is permitted. What cannot be expressed
in shared primitives must be proposed as a new shared primitive,
not hidden inside a pack.

### 5. Readback is owned locally
Each pack owns its articulation rules. Readback is not a global
postprocessor. Ambiguity management at the surface level is resolved
by the pack, not by the field layer.

### 6. Alignment is explicit
Packs must publish anchor records verifiable against the trilingual
anchor template in `packs/common/anchors/`. Coherence across languages
is a testable probe, not an emergent assumption.

## Validation Gate Sequence

| Gate | Checks |
|------|--------|
| 1. Schema | All data files validate against their JSON schemas |
| 2. Lexical | Lemma inventory is non-empty and internally consistent |
| 3. Morphology | All surface forms trace to a known lemma record |
| 4. Lift | Lift rules produce valid pressure for all seed inputs |
| 5. Readback | Readback produces grammatical surface for all seed states |
| 6. Determinism | All D0/D1 paths produce identical output on repeated runs |
| 7. Alignment | Anchor records pass trilingual coherence check |
| 8. Coverage | Probe set covers minimum lexical and morphological surface |

A pack is not active until all eight gates pass.
