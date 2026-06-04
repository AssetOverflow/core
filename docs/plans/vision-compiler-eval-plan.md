# Vision Compiler Eval Plan — `vision_core_v1`

**Companion to:** [ADR-0197](../decisions/ADR-0197-vision-compiler-delta-crdt.md),
[vision-compiler-spec.md](./vision-compiler-spec.md)
**Status:** Proposed (PR-1 docs)

This plan defines the seeding corpus, the acceptance gates that lift `vision_core_v1` from gate-closed to gate-engaged, the Delta-CRDT proof obligations, and the teacher-migration policy. It is the last PR-1 companion ADR-0197 names; it is what PR-2's "determinism + versor tests" gate is measured against.

---

## 1. Seeding corpus — visual atoms, not captions

Small, curated, checksum-locked. Four tiers:

- **Tier A — structural atoms:** flat field, oriented edge (each orientation bin), corner/junction, blob/region onset, open vs. closed contour, low- vs. high-spatial-frequency band.
- **Tier B — region & figure–ground:** salient figure on ground, background texture, occlusion boundary, symmetry, periodic repetition, scale-change across pyramid levels.
- **Tier C — color/material/lighting:** hue/saturation regimes, high vs. low luminance contrast, shadow/highlight, specular vs. matte, gradient ramp vs. hard step.
- **Tier D — alignment anchors:** caption hypothesis, detector box, segment mask, OCR text span, linked text surface (only when alignment is trustworthy).

Tier D is auxiliary; object/lexical semantics is a later enrichment step. Synthetic fixtures (oriented sinusoidal gratings, checkerboards, luminance gradients, single-dot impulses, step edges, solid color fields, controlled occlusions) drive first-pass determinism; checksum-locked real fixtures cover what synthesis does poorly (natural texture, soft occlusion, cluttered figure–ground).

## 2. Acceptance gates (gate-engaged criteria)

| Gate | Pass criterion | Obligation |
|---|---|---|
| Projection shape | exactly `(32,)` | V-1 |
| Projection dtype | exactly `float32` | V-1 |
| Compiler replay | bit-identical on same platform/build | V-1 |
| Cross-platform stability | equal after quantization, within declared numeric tolerance | V-1 |
| Canonical-ordering stability | re-tiling the same canonical image yields the same event order | V-4 |
| `versor_condition` | `< 1e-6` (never weakened) | V-5 |
| Canonical checksum stability | 100% on fixture corpus (colorspace + resize pinned) | V-1 |
| Gate closure | projection blocked when `gate_engaged = false` | — |
| Mount validation | bad checksum or bad unitarity blocks pack mount | — |
| Trace hygiene | no raw pixel bytes in any turn trace | V-6 |
| IR replay | `VisionIR -> versor` replays identically from stored IR | V-1 |

These mirror the existing modality-test posture (`sensorium/registry.py` mount/gate enforcement, `ModalityPack.__post_init__` invariants) — no new gating machinery.

## 3. Delta-CRDT proof obligations (ADR-0197 §4.2)

Each must be able to **fail loudly** under the violation it names (CLAUDE.md §Schema-Defined Proof Obligations — no decorative tests):

| ID | Obligation | Fails if… | ADR-0180 analog |
|---|---|---|---|
| **V-1** | Determinism: same canonical pixels + pack ⇒ byte-identical `(32,)` across calls/threads/processes | dict ordering, unpinned resize/colorspace, or float reduction order leaks in | T-4 |
| **V-2** | Set-equality of merges: a set of tile units folds to the same Vault state for any arena flush permutation | a delta's contribution is order-sensitive at the merge layer | T-1 |
| **V-3** | Content-addressed trace-hash: invariant under set-equal Vault states when keyed by `(canonical, ir, projection)` sha | the reduction consumes deltas in arrival order | T-2 |
| **V-4** | Serialization barrier **+ canonical spatial order**: in-chunk `compile_events` is order-sensitive (negative test), and the §6 spatial order is itself deterministic and re-tiling-stable | swapping two spatial-order events fails to change the versor, **or** re-tiling the same image reorders events | T-3 |
| **V-5** | `versor_condition < 1e-6` on every emitted unit | the threshold is weakened to pass | — |
| **V-6** | Trace hygiene: no pixels in any `TurnEvent`/Vault record | raw pixel data leaks into a delta's provenance | §1.5.5 |

V-4 carries one clause audio's A-4 did not: vision has no temporal axis, so the canonical *spatial* order (vision-compiler-spec §6) is the thing that makes the fold reproducible, and it must be tested as such.

### 3.1 The sequential==concurrent proof (PR-5 acceptance)

The load-bearing test for the CRDT mapping:

```text
ingest tiles [t1, t2, t3] sequentially          → vault_seq,  trace_hash_seq
ingest the same tiles across N arenas merged     → vault_conc, trace_hash_conc
assert set(vault_seq) == set(vault_conc)                       # V-2
assert trace_hash_seq == trace_hash_conc                       # V-3
assert re-ingesting any tile is a no-op on the vault           # idempotence (ADR-0197 §4.3)
```

This is the vision instance of ADR-0180 §4.3's `hash(Sequential_Ingest) == hash(Concurrent_CRDT_Ingest)` and must pass before PR-5 merges. Because tiles are spatially independent, this proof is the first *non-temporal* exerciser of the substrate's order-invariance (ADR-0197 §3.1).

### 3.2 Pytest skeleton

```python
def test_vision_projection_is_deterministic(vision_tile, vision_pack):          # V-1
    v1 = vision_pack.projection.project(vision_tile)
    v2 = vision_pack.projection.project(vision_tile)
    assert v1.shape == (32,)
    assert v1.dtype.name == "float32"
    assert np.array_equal(v1, v2)

def test_vision_pack_gate_blocks_projection(vision_pack_closed, vision_tile):   # gate closure
    with pytest.raises(Exception):
        _ = vision_pack_closed.projection.project(vision_tile)

def test_vision_ir_replay_matches_original(vision_tile, compiler):               # IR replay
    unit = compiler.compile_tile(vision_tile)
    replay = compiler.compile_ir(unit.vision_ir)
    assert np.array_equal(unit.versor, replay.versor)
    assert unit.ir_sha256 == replay.ir_sha256

def test_chunk_composition_is_order_sensitive(two_events, compiler):             # V-4 barrier
    a = compiler.compile_events([two_events[0], two_events[1]])
    b = compiler.compile_events([two_events[1], two_events[0]])
    assert not np.array_equal(a, b)

def test_canonical_spatial_order_is_retiling_stable(vision_fixture, compiler):   # V-4 spatial clause
    order_a = compiler.canonical_event_order(vision_fixture)
    order_b = compiler.canonical_event_order(compiler.recanonicalize(vision_fixture))
    assert [e.stable_event_id for e in order_a] == [e.stable_event_id for e in order_b]

def test_merge_is_permutation_invariant(units):                                 # V-2
    import itertools
    states = {fold_into_vault(p) for p in itertools.islice(_perms(units), 8)}
    assert len(states) == 1
```

## 4. Teacher / shadow lane policy (PR-6)

Teachers label or align; they **never** define the substrate and **never** fold embeddings into the main versor path. They are admitted only through typed, versioned, checksummed hints stored as `content_anchors` / `evidence_ids` in the IR.

| Source | Best role in CORE | Why not the substrate |
|---|---|---|
| **CLIP** | coarse scene/object labels, image-text alignment prototypes | embedding model; opaque latent violates the design goal |
| **DINOv2** | self-supervised region/correspondence hints | dense embedding; not a checksummable typed visual IR |
| **ViT (supervised)** | classification evidence, weak object labels | latent features, no content-addressed key |
| **SAM** | region/segment proposals as `region` anchors | non-deterministic across versions; gives no checksummable key |
| **Depth Anything / RAFT** | depth/flow evidence lanes (and the seam for future video) | estimators, not a CORE-native deterministic compiler |
| **Tesseract / OCR** | text-span anchors when glyphs are present | text extraction, wrong primary ontology for vision |

Migration policy, verbatim (identical to audio):

```text
Use teachers to label or align.
Never let teachers define the substrate.
Never fold teacher embeddings directly into the main versor path.
Only admit teacher outputs through typed, versioned, checksumed hints.
```

This is the line ADR-0197 §3.2 names as the primary risk: pretrained vision encoders are strong enough to tempt substrate use. They stay in this table, never on the versor path.

## 5. Phased sequence (priority order, no calendar)

1. **Doctrine** — ADR + spec + eval plan locked (PR-1, this).
2. **Deterministic substrate** — canonicalizer, checksums, resample, grid, lexer, parser, operators, compiler (PR-2).
3. **Governance** — pack artifacts, adapter, mount/gate/checksum tests (PR-3).
4. **Evaluation** — fixtures, expected IR, expected projection hashes, gate table (PR-4).
5. **Delta-CRDT wiring** — arena + merge key + sequential==concurrent proof (PR-5), gated on ADR-0180 §1.5.4 (T-1…T-4) green on `main`.
6. **Auxiliary lanes** — CLIP/DINOv2/SAM/depth/OCR teachers behind optional extras (PR-6).
7. **Streaming** — stateful incremental compiler preserving continuity across frames/seams (later; v1 is single-frame/whole-image, offline).
