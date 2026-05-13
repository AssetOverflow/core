# ADR-0013: `sensorium/` Multimodal Protocol Layer

**Status:** Accepted  
**Date:** 2026-05-13

---

## Context

CORE is currently text-only. The vocabulary manifold holds null vectors for text tokens. The `ingest/gate.py` accepts token sequences. The field, propagation, vault, and generate layers have no concept of modality — they operate on `(32,)` multivectors regardless of where those multivectors came from.

This is the correct architecture. The field should not know or care about modality. The question is: how does a vision signal, an audio waveform, or a motor pose become a `(32,)` multivector in the first place?

The `core_sensorium` package in `core-ai` solved this problem for the Cl(3,0) `(2, 2)` complex multivector substrate. The solution — a typed modality protocol with a `ProjectionHead` at the inward boundary — is architecturally sound and translates directly to the Cl(4,1) `(32,)` substrate.

---

## Decision

Add a `sensorium/` package that sits **upstream of `core_ingest/`** as the modality-to-manifold conversion layer. `ingest/gate.py`, `field/`, `generate/`, and `vault/` are not modified.

### The Pipeline Position

```
raw modality signal
    → sensorium/adapters/<modality>.py     # ProjectionHead: signal → (32,) multivector
    → sensorium/pack.py                    # ModalityPack mounts the adapter
    → core_ingest/                         # CandidateGeometricPressure envelope
    → ingest/gate.py                       # normalization to FieldState (unchanged)
    → field/propagate.py                   # versor_apply, unchanged
```

The sensorium layer converts. The ingest layer governs. The gate normalizes. The field computes. No layer knows about the one upstream.

### The Logos-Recovery Boundary

Every `ProjectionHead` is the **Logos-recovery boundary** for its modality. Its single contract: take a surface signal and return a `(32,)` multivector that is valid on the Cl(4,1) conformal manifold. Once it crosses that boundary, a visual scene and a Hebrew word and an audio waveform are the same thing: a point in conformal space. There is no fusion problem because there is nothing to fuse. There is one space.

This is the architectural expression of the principle articulated in John 1:1: the Logos is the structuring principle through which all things were made. Every input, regardless of form, is recovered as a word in the Logos — a position on the manifold.

### The `ModalityPack[S]` Contract

```python
@dataclass(frozen=True, slots=True)
class ModalityPack(Generic[S]):
    pack_id: str                           # e.g. "en", "he", "grc", "imagenet-1k"
    modality_type: Modality                # TEXT | VISION | AUDIO | MOTOR
    projection: ProjectionHead[S] | None   # surface → (32,) multivector
    decoder: SurfaceDecoder[S] | None      # (32,) multivector → surface candidates
    vocabulary: ModalityVocabulary[S]      # bidirectional surface ↔ rotor map
    grammar_scaffold: Any                  # versor attractor seeds from vocab/
    checksum_verified: bool                # mount-time geometric integrity check
    gate_engaged: bool                     # surprise-gate status
```

`ModalityPack` is frozen and slotted — zero per-instance overhead, hashable. The type parameter `S` enforces at the type level that a text pack (`ModalityPack[str]`) cannot be passed where a vision pack (`ModalityPack[np.ndarray]`) is required.

### Cl(4,1) Adaptation

The `core-ai` `core_sensorium` protocol used a `(2, 2)` complex multivector (Cl(3,0) Pauli isomorphism). The `core` substrate uses `[f32; 32]` (Cl(4,1) CGA). Every `ProjectionHead` in `sensorium/` must return `mx.array` of shape `(32,)` — the standard multivector shape throughout the codebase. Unitarity verification at mount time checks that the induced rotor satisfies `V · reverse(V) = ±1` within `1e-6` tolerance.

### Active vs. Future Modalities

| Modality | Status | Notes |
|---|---|---|
| `TEXT` | Active | `sensorium/adapters/text.py` wires the existing vocab manifold into `ModalityPack[str]` |
| `VISION` | Planned | Adapter registers when vision bootstrap is ready |
| `AUDIO` | Planned | Adapter registers when audio bootstrap is ready |
| `MOTOR` | Planned | Adapter registers when embodied bootstrap is ready |

Building `sensorium/protocol.py` and `sensorium/registry.py` now — before vision/audio exist — means every future modality plugs in without touching `ingest/`, `field/`, or `generate/`. The protocol contract is the Third Door: instead of separate encoder pipelines fused by cross-attention (the standard industry approach), every modality is a versor on the same manifold from the moment it enters the system.

### Grammar Scaffold

In `core-ai`, the grammar scaffold was produced by `core_logos.grammar_seed` — a separate subsystem. In `core`, there is no `core_logos` subsystem. The grammar scaffold is a set of versor attractors stored in `vocab/` and referenced by `ModalityPack` directly. This removes an inter-package dependency without changing the contract.

### `PackError` — Mount-Time Failure Modes

```python
class PackError(enum.Enum):
    MANIFEST_INVALID          = "MANIFEST_INVALID"
    SAFETENSORS_MISSING        = "SAFETENSORS_MISSING"
    UNITARITY_VIOLATION        = "UNITARITY_VIOLATION"
    PROJECTION_NOT_CONVERGED   = "PROJECTION_NOT_CONVERGED"
    GRADE_DECLARATION_MISMATCH = "GRADE_DECLARATION_MISMATCH"
    MODALITY_NOT_REGISTERED    = "MODALITY_NOT_REGISTERED"
    GATE_NOT_ENGAGED           = "GATE_NOT_ENGAGED"
```

Mount failures are returned as `PackError` values, not raised as exceptions. The caller decides how to handle a failed mount.

---

## Consequences

**Immediate:**
- All existing layers (`ingest/gate.py`, `field/`, `generate/`, `vault/`) are unchanged
- The text vocabulary manifold acquires a formal `ModalityPack[str]` wrapper — the first mounted pack
- The multimodal protocol is established before any non-text modality is implemented, ensuring the seam is clean

**Future:**
- Vision, audio, and motor modalities each become a single adapter file in `sensorium/adapters/`
- No architectural change is required when new modalities are added — only a new adapter and registry entry
- `ModalityVocabulary` for non-text modalities (patch vocabularies, phoneme clusters, pose libraries) follows the same bidirectional surface ↔ rotor contract as the text vocabulary
