# Vision Compiler Spec — `vision_core_v1`

**Companion to:** [ADR-0197](../decisions/ADR-0197-vision-compiler-delta-crdt.md)
**Status:** Proposed (PR-1 docs)
**Scope:** the deterministic substrate (PR-2/PR-3) and its Delta-CRDT delta interface (PR-5).

This spec fixes the typed IR, the operator/manifest format, the numeric determinism rules, and the `VisionCompilationUnit` → Delta-CRDT delta contract. It is implementation-facing; the *why* lives in ADR-0197, the *acceptance* lives in the eval plan. It also **resolves the two ADR-0197 red-line blockers** — §2.1 canonical spatial ordering and §2.6 blade semantics — see §6 and §7 below.

---

## 0. Resolutions of the ADR-0197 open questions

| ADR-0197 open Q | Resolution in this spec |
|---|---|
| **#1 unit granularity** | **One tile at one scale level = one chunk = one `VisionCompilationUnit`.** The whole-image versor is the *merged* contribution of its tile units, never a separate object. |
| **#2 position encoding** | **v1: position is carried in IR tile/scale coordinates and modulates rotor `theta`; layout is preserved by the canonical spatial order (§6).** CGA conformal *translators* (parabolic, `n_inf` generator) are deferred to v2. Rationale: keeps v1 elliptic-only and audio-parallel, and avoids unproven parabolic numerics on the hot path. |
| **#3 elliptic sufficiency** | **Elliptic bivector rotors only in v1** (square = −1), matching ADR-0181. Figure–ground is a grade-2 saliency rotor (`B_SALIENCE`), not a boost. |
| **#4 morton resolution-independence** | **Resolved by construction:** tiling happens *after* canonicalization to the pack's fixed grid (§3), so `morton_code` runs over fixed normalized tile indices and is identical regardless of source resolution. |

The CGA machinery in `algebra/cga.py` (`embed_point`, `cga_inner`) remains the **recall-side** distance metric for merged vision deltas in the Vault (ADR-0054) — exactly as for audio. This spec governs only how the **compile-side** versor is *built* (elliptic-rotor composition); it does not change how versors are *compared* at recall.

## 1. Two-clock architecture

A low-level **spatial clock** measures pixel facts; a higher-level **visual-grammar clock** emits typed events. The primary path is fully deterministic; learned systems are confined to auxiliary evidence lanes (PR-6).

```mermaid
flowchart LR
  A[Image bytes / single video frame] --> B[Canonicalizer<br/>fixed colorspace + gamma + grid + checksums]
  B --> C[Spatial grid<br/>tile lattice × scale pyramid]
  C --> D[Visual lexer<br/>orientation energy, spatial-freq bands,<br/>luma/chroma stats, corner/blob onset, region boundaries]
  D --> E[Typed VisionIR parser<br/>regions/segments, contour arcs,<br/>salient-object events, texture atoms, anchors]
  E --> F[Canonical spatial ordering<br/>scale → morton → precedence → stable_id]
  F --> G[Operator registry<br/>pack manifest + blade aliases + theta rules]
  G --> H[Rotor lowering]
  H --> I[Versor composition<br/>unitize_versor + versor_condition]
  I --> J["(32,) float32 — one VisionCompilationUnit"]
  E --> K[Vision evidence trace<br/>hashes, teacher provenance, pack IDs]
  J --> L[Thread-local arena<br/>ADR-0180 §2.1]
  L --> M[Semilattice merge<br/>keyed by content-addressed sha]
```

## 2. Typed VisionIR

The IR is built from **typed regions and events**, never from raw pixels or feature maps. Detector/caption hypotheses may exist only as auxiliary content anchors, never as the sole meaning of the image.

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import numpy as np


@dataclass(frozen=True, slots=True)
class VisionImage:
    pixels: np.ndarray         # canonical linear-light float32, shape (H, W, C)
    grid_h: int                # canonical tile rows
    grid_w: int                # canonical tile cols
    scale_levels: int
    source_sha256: str
    canonical_sha256: str


@dataclass(frozen=True, slots=True)
class TileCoord:
    scale_level: int           # 0 = finest
    tile_row: int
    tile_col: int

    @property
    def morton(self) -> int:   # Z-order interleave of (tile_row, tile_col)
        r, c, code, bit = self.tile_row, self.tile_col, 0, 0
        while (r >> bit) or (c >> bit):
            code |= ((r >> bit) & 1) << (2 * bit)
            code |= ((c >> bit) & 1) << (2 * bit + 1)
            bit += 1
        return code


@dataclass(frozen=True, slots=True)
class VisualToken:
    kind: Literal[
        "flat", "edge", "corner", "blob", "texture",
        "orient_bin", "freq_bin", "chroma_bin",
    ]
    coord: TileCoord
    value_q: tuple[int, ...]   # canonical quantized payload


@dataclass(frozen=True, slots=True)
class VisualEvent:
    event_type: str
    coord: TileCoord
    attrs: tuple[tuple[str, int | str], ...]   # quantized ints / short strings
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VisionIR:
    regions:         tuple[VisualEvent, ...]
    contour_arcs:    tuple[VisualEvent, ...]
    orient_events:   tuple[VisualEvent, ...]
    texture_atoms:   tuple[VisualEvent, ...]
    salient_events:  tuple[VisualEvent, ...]
    content_anchors: tuple[VisualEvent, ...]
    ir_sha256:       str
```

### 2.1 The compilation unit (the CRDT delta)

```python
@dataclass(frozen=True, slots=True)
class VisionCompilationUnit:
    canonical_sha256:     str
    ir_sha256:            str
    pack_id:              str
    pack_manifest_sha256: str
    projection_sha256:    str
    coord:                TileCoord     # tile/scale this unit covers
    versor:               np.ndarray    # (32,) float32
    versor_condition:     float

    @property
    def merge_key(self) -> tuple[str, str, str]:
        # ADR-0197 §2.2 — same triple as AudioCompilationUnit.
        return (self.canonical_sha256, self.ir_sha256, self.projection_sha256)
```

`VisionCompilationUnit` is the single object the vision adapter writes into its thread-local arena (ADR-0180 §2.1). It carries no pixels (ADR-0197 §3.1 / ADR-0180 §1.5.5). `coord` is retained so the merge can reconstruct spatial layout without a global lock (ADR-0197 §2.3).

## 3. Canonical signal formation

- Internal representation: **linear-light float**, fixed colorspace (sRGB primaries, gamma linearized to a pinned LUT), alpha dropped, fixed canonical resolution grid. Original-source bytes preserved separately for provenance.
- Resampling: **pinned separable kernel** (fixed Lanczos-3 coefficients), generated **once**, stored as a pack artifact (`resample_kernel_v1.npy`) and checksummed in the manifest. The runtime never relies on library defaults — this is the vision analog of audio's pinned FIR (ADR-0197 §3.2).
- Tiling happens **after** canonical resize, so the tile lattice and `morton` order are resolution-independent (resolves ADR-0197 #4).

## 4. Visual lexer

Operates on **measured facts**, not semantic guesses. Default tile 16×16 px at the finest scale; a fixed 3-level Gaussian/Laplacian pyramid. Each tile yields quantized descriptors: dominant gradient-orientation histogram bin, oriented-energy bin per spatial-frequency band (low/high), local luminance-contrast bin, quantized hue/saturation regime, corner/blob response bins, texture periodicity/entropy bin, flat-region flag.

## 5. Parser → typed events

Promotes lexer output into typed regions/events. Preserves the distinctions a downstream reader needs: a hard oriented edge vs. a soft luminance ramp, a closed contour vs. a dangling one, a salient figure vs. background texture. "Unstructured texture" is the fallback only when a more specific parse is impossible — the visual analog of audio's "chaotic noise" fallback.

## 6. Canonical spatial ordering (resolves ADR-0197 §2.1)

The in-chunk fold is a **serialization barrier** (ADR-0197 §2.1); it requires a deterministic total order over the chunk's `VisualEvent`s. The order is:

```text
key(event) = (coord.scale_level,
              coord.morton,
              event_precedence[category(event.event_type)],
              stable_event_id)
```

- `coord.morton` is the Z-order interleave in `TileCoord.morton` — a space-filling curve that keeps spatially-near events adjacent in the fold.
- `event_precedence` is a fixed list in the manifest (§6.1 `[ordering]`).
- `stable_event_id` is the content hash of the event's quantized attrs (final tiebreak; never wall-clock).

**This order is the thing V-4 asserts against** (ADR-0197 §4.2): re-tiling the same canonical image yields the same order, and swapping two events changes the versor.

## 7. Operator registry (pack-local blade aliases)

Because the `(32,)` boundary is fixed but no canonical *semantic* blade map is exposed, v1 uses **pack-local, versioned, checksummed blade aliases**, identical in discipline to ADR-0181 §6. v1 uses **elliptic bivector operators only** (square = −1), so every rotor is `R = cos(θ/2) + B·sin(θ/2)`. Parabolic (CGA translator) and hyperbolic operators are deferred to v2.

Position does **not** get its own geometric generator in v1 (resolves ADR-0197 #2): tile/scale coordinates modulate `theta` and order the fold; they are not embedded as a CGA point on the compile path.

| Visual atom family | Measured source | Alias | Default blade index | Theta rule |
|---|---|---|---|---|
| Oriented edge energy | gradient-orientation histogram | `B_ORIENT` | 6 | `q(base + g1·orient_q + g2·scale_level)` |
| Low spatial-frequency band | low bandpass energy | `B_FREQ_LOW` | 7 | `q(base + g3·energy_q)` |
| High spatial-frequency band | high bandpass energy | `B_FREQ_HIGH` | 8 | `q(base + g4·energy_q)` |
| Corner / junction | corner response bin | `B_CORNER` | 9 | `q(base + g5·corner_q)` |
| Blob / region onset | blob detector bin | `B_BLOB` | 10 | `q(base + g6·blob_q)` |
| Contour closure | boundary continuity | `B_CONTOUR` | 11 | `q(base + g7·closure_q)` |
| Luminance contrast | local contrast bin | `B_CONTRAST` | 12 | `q(base + g8·contrast_q)` |
| Chroma / color regime | quantized hue/sat bin | `B_CHROMA` | 13 | `q(base + g9·hue_q + g10·sat_q)` |
| Texture regularity | periodicity / entropy bin | `B_TEXTURE` | 14 | `q(base + g11·texture_q)` |
| Saliency / figure–ground | center-surround salience | `B_SALIENCE` | 15 | `q(base + g12·salience_q)` |

Indices are **reasonable defaults, not metaphysical claims** about Cl(4,1) (verbatim the ADR-0181 §6 stance). The contract is that the mapping is explicit, versioned, checksummed, and frozen in the manifest. `B_SALIENCE` is the figure–ground atom that ADR-0197 §2.6 declined to model with a boost.

### 7.1 Minimal manifest (`packs/vision/vision_core_v1/manifest.toml`)

```toml
pack_id = "vision_core_v1"
modality = "vision"
cl41_dim = 32
compiler_version = "0.1.0"
basis_version = "vision-basis-v1"

[canonical]
colorspace = "srgb_linear"
gamma_lut = "gamma_lut_v1.npy"
tile_px = 16
scale_levels = 3
output_dtype = "float32"
internal_dtype = "float64"

[resampling]
algorithm = "separable_lanczos3"
kernel_path = "resample_kernel_v1.npy"
kernel_sha256 = "sha256:REPLACE_ME"

[gating]
gate_engaged = false
checksum_verified = false
versor_condition_max = 1.0e-6

[ordering]
event_precedence = ["region", "contour", "orient", "texture", "salient", "content_anchor"]
```

### 7.2 Operator row (`operators.jsonl`)

```json
{
  "operator_id": "vision.orient.edge_energy.v1",
  "event_type": "orient.edge_energy",
  "blade_alias": "B_ORIENT",
  "blade_index": 6,
  "rotor_kind": "elliptic",
  "base_theta_q": 48,
  "gain_rules": {"orient_q": 3, "scale_level": 2, "confidence_q": 1},
  "theta_clip_q": 384,
  "version": "1"
}
```

## 8. Numeric determinism

Rule (verbatim from ADR-0181 §7): **quantize before semantics, normalize after composition.** Quantization regime (frozen in manifest): orientation in 16 ordinal bins, oriented energy in log bins, contrast in dB-like bins, hue/sat in fixed ordinal bins, all confidences in uint8. After quantization, compute in float64, compose sparse rotors in canonical spatial order, call algebra-owned `unitize_versor`, cast to float32 **only** at the output boundary.

```python
import math
import numpy as np

def quantize_theta(theta: float, step: float = 1.0 / 1024.0) -> float:
    return round(theta / step) * step

def build_elliptic_rotor(blade_index: int, theta: float) -> np.ndarray:
    out = np.zeros(32, dtype=np.float64)
    half = quantize_theta(theta) / 2.0
    out[0] = math.cos(half)
    out[blade_index] = math.sin(half)
    return out

def compile_events(events, registry, geometric_product, unitize_versor, versor_condition):
    # SERIALIZATION BARRIER (ADR-0197 §2.1): in-chunk composition is order-sensitive,
    # single-threaded, in CANONICAL SPATIAL ORDER (§6). The substrate never parallelizes this.
    v = np.zeros(32, dtype=np.float64)
    v[0] = 1.0
    for ev in events:                          # MUST already be in §6 canonical spatial order
        spec = registry[ev.event_type]
        theta = spec.theta_from_event(ev)      # deterministic, quantized inputs only
        r = build_elliptic_rotor(spec.blade_index, theta)
        v = geometric_product(v, r)
        v = unitize_versor(v)
    if versor_condition(v) >= 1e-6:
        raise ValueError("vision compilation failed versor check")
    return v.astype(np.float32)
```

`geometric_product`, `unitize_versor`, `versor_condition` are imported from `algebra/`; the vision compiler adds **no** new normalization function. `embed_point`/`cga_inner` are used only on the Vault recall side, never here.

## 9. Repo-facing adapter (`sensorium/adapters/vision.py`)

```python
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True, slots=True)
class VisionProjectionHead:
    compiler: "VisionCompiler"
    modality = ...                # Modality.VISION

    @property
    def embedding_dim(self) -> int:
        return 32

    def project(self, image: "VisionImage") -> np.ndarray:
        # One image projects to its merged tile-unit versor (granularity resolution #1):
        out = self.compiler.compile_image(image).versor
        if out.shape != (32,):
            raise ValueError(f"expected (32,), got {out.shape}")
        if out.dtype != np.float32:
            raise TypeError(f"expected float32, got {out.dtype}")
        return out

    def project_batch(self, images: list["VisionImage"]) -> np.ndarray:
        return np.stack([self.project(im) for im in images], axis=0)

    def verify_unitarity(self, image: "VisionImage") -> bool:
        return self.compiler.compile_image(image).versor_condition < 1e-6
```

The adapter is thin and pack-governed; it satisfies the `ProjectionHead` protocol in `sensorium/protocol.py` and is mounted as `ModalityPack(modality_type=Modality.VISION, gate_engaged=False)` until the eval gates pass.

## 10. Delta-CRDT delta interface (PR-5)

The vision adapter **never** writes the global `epistemic_state` (ADR-0180 §2.1). Instead:

1. `compile_tile()` produces one `VisionCompilationUnit` per tile/scale (the §8 serialization barrier runs here).
2. Each unit is written lock-free into the adapter's **thread-local arena**. Independent regions/scales/frames each have their own arena (ADR-0197 §2.3).
3. The **Merge Kernel** (ADR-0180 §2.2, explicitly mounted, not a daemon) folds pending units into the Vault ordered by `unit.merge_key`. Duplicate keys deduplicate (idempotence).
4. The kernel surfaces its pending-delta count in `TurnEvent` for replay evidence (ADR-0180 §1.5.5).

The per-tile Vault contribution is `(versor, provenance)` where provenance = `{merge_key, pack_id, pack_manifest_sha256, coord}` — content-addressed, no pixels.

## 11. File plan (PR-2 … PR-6)

```text
sensorium/vision/{__init__,types,canonical,checksum,resample,grid,lexer,parser,operators,compiler,trace,fixtures,teachers}.py
sensorium/adapters/vision.py
packs/vision/vision_core_v1/{manifest.toml,basis_map.json,operators.jsonl,atoms.jsonl,prototypes.jsonl,resample_kernel_v1.npy,gamma_lut_v1.npy,checksums.json}
tests/test_vision_{image,resample,grid,lexer,parser,ordering,pack_manifest,sensorium_mount,trace,crdt_delta}.py
evals/vision_sensorium/{fixtures/*.png,manifest.json,expected_ir.jsonl,expected_projection_hashes.json}
```