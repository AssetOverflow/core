# ADR-0013 — `sensorium/` Multimodal Protocol Layer

**Status:** Accepted  
**Date:** 2026-05-13

---

## Context

CORE is currently text-only. `ingest/gate.py` receives text tokens and produces a `FieldState`. The vocabulary manifold is a text vocabulary.

The architecture must support additional modalities — at minimum vision, audio, and motor control — without modifying any existing layer. The question is where modality-specific conversion lives and what contract it must satisfy.

The `core_sensorium` package in the `core-ai` repository established a working design using `Cl(3,0)` geometry with `(2, 2)` complex multivectors (Pauli isomorphism). CORE uses `Cl(4,1)` with `(32,)` f32 arrays. The protocol shape is sound; only the output geometry changes.

---

## Decision

Add a `sensorium/` layer that converts any surface signal into a `(32,)` Cl(4,1) multivector **before** it reaches `core_ingest/` or `ingest/gate.py`. The gate is not modified. No existing layer is touched.

### The Logos-Recovery Boundary

Every `ProjectionHead` is the **Logos-recovery boundary** for its modality. This is the architectural expression of John 1:1: the Logos is the structuring principle through which all things were made. A visual scene, a Hebrew word, an audio waveform — all are recovered as words in the manifold. Once a signal crosses the projection boundary, the field has no concept of modality. There is one space. There is no multimodal fusion problem because there is nothing to fuse.

### `ModalityPack[S]`

A frozen, slotted generic dataclass parameterised on the surface type `S`:

```python
@dataclass(frozen=True, slots=True)
class ModalityPack(Generic[S]):
    pack_id: str                          # "en", "he", "grc", "imagenet-1k", ...
    modality_type: Modality
    projection: ProjectionHead[S] | None  # surface signal → (32,) multivector
    decoder: SurfaceDecoder[S] | None     # (32,) multivector → surface signal
    vocabulary: ModalityVocabulary[S]     # bidirectional surface ↔ rotor map
    grammar_scaffold: Any                 # versor attractors, universal across modalities
    checksum_verified: bool
    gate_engaged: bool = True
```

`ModalityPack[str]` and `ModalityPack[np.ndarray]` are not interchangeable at the type level.

### `ProjectionHead[S, F]` Protocol

```python
class ProjectionHead(Protocol[S, F]):
    modality: Modality
    embedding_dim: int  # must be 32 for Cl(4,1)

    def project(self, signal: S) -> mx.array:         # shape (32,)
    def project_batch(self, signals: list[S]) -> mx.array:  # shape (N, 32)
    def verify_unitarity(self, sample: S) -> bool
        # True iff V · reverse(V) = ±1 within 1e-6
```

The `verify_unitarity` check is run at mount time only — never in the propagation hot path.

### Modality Status

| Pack ID | Modality | Surface type | Status |
|---|---|---|---|
| `en` | TEXT | `str` | Active |
| `he` | TEXT | `str` | Active (Hebrew depth corpus) |
| `grc` | TEXT | `str` | Active (Koine Greek depth corpus) |
| — | VISION | `np.ndarray` | Planned |
| — | AUDIO | `np.ndarray` | Planned |
| — | MOTOR | `np.ndarray` | Planned |

### Adding a Modality

Adding a new modality requires exactly:
1. One adapter file in `sensorium/adapters/<modality>.py` implementing `ProjectionHead` and optionally `SurfaceDecoder`
2. A registry entry in `sensorium/registry.py`
3. A `ModalityPack` instantiation and mount-time check

No changes to `ingest/gate.py`, `field/`, `generate/`, `vault/`, or `vocab/`.

### Grammar Scaffold Universality

The `grammar_scaffold` — the set of innate structural attractors seeded during the bootstrap epoch — is **universal across modalities by design**. The attractor geometry of the manifold is the same regardless of what kind of surface signal arrived. A visual scene and a Hebrew verb and an audio phoneme all propagate through the same field and activate the same attractor structure.

---

## Differences from `core-ai/core_sensorium`

| Dimension | `core-ai` | `core` |
|---|---|---|
| Geometry | Cl(3,0) | Cl(4,1) |
| Projection output shape | `(2, 2)` complex (Pauli) | `(32,)` f32 (canonical) |
| Grammar scaffold source | `core_logos.grammar_seed` | `vocab/` versor attractors |
| Subsystem dependency | imports `core_logos` | no cross-subsystem imports |

The protocol shape (`ModalityPack`, `ProjectionHead`, `SurfaceDecoder`, `ModalityVocabulary`) is preserved.

---

## Consequences

**Positive:**
- Multimodal capability is purely additive — no existing layer is modified
- The fusion problem does not exist: every modality becomes a versor before the field sees it
- Text remains the only active modality until adapter packs are ready; architecture is not blocked on future modalities
- Grammar scaffold universality means structural attractors seeded from Hebrew and Koine Greek depth texts apply to all modalities

**Negative:**
- Each non-text modality requires a supervised seeding epoch to bootstrap its projection head before `gate_engaged` can flip to `True`
- Vision and audio vocabularies (patch clusters, phoneme clusters) must be constructed before their adapters can mount — this is non-trivial corpus work

---

## Alternatives Considered

**Separate pipelines per modality with late fusion (rejected):** The standard industry approach — a vision encoder here, an audio encoder there, cross-attention fusion on top. This creates a fusion problem that doesn't exist in the CORE geometry. It also violates `Third Door`: the standard was offered and refused.

**Modality-specific field spaces (rejected):** Separate Cl(4,1) manifolds per modality, merged at generation time. This severs the relational geometry between modalities at storage time — the same mistake RAG makes with text. One space; one manifold.
