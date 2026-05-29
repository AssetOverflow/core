# Audio Compiler Eval Plan — `audio_core_v1`

**Companion to:** [ADR-0181](../decisions/ADR-0181-audio-compiler-delta-crdt.md),
[audio-compiler-spec.md](./audio-compiler-spec.md)
**Status:** Proposed (PR-1 docs)

This plan defines the seeding corpus, the acceptance gates that lift `audio_core_v1` from
gate-closed to gate-engaged, the Delta-CRDT proof obligations, and the teacher-migration policy.

---

## 1. Seeding corpus — auditory atoms, not transcripts

Small, curated, checksum-locked. Four tiers:

- **Tier A — speech & turn atoms:** silence, short/long pause, voiced/unvoiced speech, onset,
  offset, interruption, overlap, rising/falling contour, emphatic energy.
- **Tier B — prosody & affect:** calm, urgent, uncertain, whispered, shouted, sorrowful, joyful,
  irritated, sarcastic-like contours where reliably labelable.
- **Tier C — non-speech events:** laughter, sigh, cry, alarm, knock, impact, keyboard, water,
  traffic, animal call, music bed, broadband noise.
- **Tier D — alignment anchors:** spoken phrase, timestamp span, transcript hypothesis,
  speaker/channel metadata, linked text surface (only when alignment is trustworthy).

Tier D is auxiliary; lexical semantics is a later enrichment step. Synthetic fixtures (sine
bursts, chirps, impulses, periodic voiced surrogates, silence, controlled overlaps) drive
first-pass determinism; checksum-locked real fixtures cover what synthesis does poorly
(laughter, sigh, whisper, interruption, yes/no rising-pitch questions).

## 2. Acceptance gates (gate-engaged criteria)

| Gate | Pass criterion |
|---|---|
| Projection shape | exactly `(32,)` |
| Projection dtype | exactly `float32` |
| Compiler replay | bit-identical on same platform/build |
| Cross-platform stability | equal after quantization, within declared numeric tolerance |
| `versor_condition` | `< 1e-6` (never weakened) |
| Canonical checksum stability | 100% on fixture corpus |
| Gate closure | projection blocked when `gate_engaged = false` |
| Mount validation | bad checksum or bad unitarity blocks pack mount |
| Trace hygiene | no raw waveform bytes in any turn trace |
| IR replay | `AudioIR -> versor` replays identically from stored IR |

These mirror the existing modality-test posture (`sensorium/registry.py` mount/gate enforcement,
`ModalityPack.__post_init__` invariants).

## 3. Delta-CRDT proof obligations (ADR-0181 §4.2)

Each must be able to **fail loudly** under the violation it names (CLAUDE.md §Schema-Defined
Proof Obligations — no decorative tests):

| ID | Obligation | Fails if… | ADR-0180 analog |
|---|---|---|---|
| **A-1** | Determinism: same bytes + pack ⇒ byte-identical `(32,)` across calls/threads/processes | dict ordering, unpinned FIR, or float reduction order leaks in | T-4 |
| **A-2** | Set-equality of merges: a set of units folds to the same Vault state for any arena flush permutation | a delta's contribution is order-sensitive at the merge layer | T-1 |
| **A-3** | Content-addressed trace-hash: invariant under set-equal Vault states when keyed by `(canonical, ir, projection)` sha | the reduction consumes deltas in arrival order | T-2 |
| **A-4** | Serialization barrier: in-chunk `compile_events` is order-sensitive (negative test) | swapping two canonical-order events fails to change the versor | T-3 |
| **A-5** | `versor_condition < 1e-6` on every emitted unit | the threshold is weakened to pass | — |
| **A-6** | Trace hygiene: no PCM in any `TurnEvent`/Vault record | raw waveform leaks into a delta's provenance | §1.5.5 |

### 3.1 The sequential==concurrent proof (PR-5 acceptance)

The load-bearing test for the CRDT mapping:

```text
ingest fixtures [c1, c2, c3] sequentially      → vault_seq,  trace_hash_seq
ingest the same fixtures across N arenas merged → vault_conc, trace_hash_conc
assert set(vault_seq) == set(vault_conc)                       # A-2
assert trace_hash_seq == trace_hash_conc                       # A-3
assert re-ingesting any fixture is a no-op on the vault        # idempotence (ADR-0181 §4.3)
```

This is the audio instance of ADR-0180 §4.3's `hash(Sequential_Ingest) ==
hash(Concurrent_CRDT_Ingest)` and must pass before PR-5 merges.

### 3.2 Pytest skeleton

```python
def test_audio_projection_is_deterministic(audio_fixture, audio_pack):       # A-1
    v1 = audio_pack.projection.project(audio_fixture)
    v2 = audio_pack.projection.project(audio_fixture)
    assert v1.shape == (32,)
    assert v1.dtype.name == "float32"
    assert np.array_equal(v1, v2)

def test_audio_pack_gate_blocks_projection(audio_pack_closed, audio_fixture):  # gate closure
    with pytest.raises(Exception):
        _ = audio_pack_closed.projection.project(audio_fixture)

def test_audio_ir_replay_matches_original(audio_fixture, compiler):            # IR replay
    unit = compiler.compile(audio_fixture)
    replay = compiler.compile_ir(unit.audio_ir)
    assert np.array_equal(unit.versor, replay.versor)
    assert unit.ir_sha256 == replay.ir_sha256

def test_chunk_composition_is_order_sensitive(two_events, compiler):           # A-4 barrier
    a = compiler.compile_events([two_events[0], two_events[1]])
    b = compiler.compile_events([two_events[1], two_events[0]])
    assert not np.array_equal(a, b)

def test_merge_is_permutation_invariant(units):                                # A-2
    import itertools, random
    states = {fold_into_vault(p) for p in itertools.islice(_perms(units), 8)}
    assert len(states) == 1
```

## 4. Teacher / shadow lane policy (PR-6)

Teachers label or align; they **never** define the substrate and **never** fold embeddings into
the main versor path. They are admitted only through typed, versioned, checksummed hints stored
as `content_anchors` / `evidence_ids` in the IR.

| Source | Best role in CORE | Why not the substrate |
|---|---|---|
| **Whisper** | offline transcript evidence, weak lexical labels, language ID | chunked, text-intermediate; loses native auditory structure |
| **NeMo Parakeet** | timestamp/alignment teacher, live evidence lane | ASR, not a CORE-native auditory compiler |
| **NeMo Canary** | streaming multilingual transcript/translation evidence | useful evidence, wrong primary ontology |
| **CLAP** | coarse sound-event labels, audio-text alignment prototypes | embedding model; opaque latent violates the design goal |
| **EnCodec** | reconstruction shadow lane, transport, future speech-to-speech output | codec tokens ≠ lawful typed auditory operators |
| **Moshi** | latency / full-duplex reference target | codec-token speech modeling, not deterministic IR→versor |
| **openSMILE / eGeMAPS** | reference feature catalog / offline oracle | OSS build is **non-commercial**; reference only, never a runtime dep unless licensing cleared |

Migration policy, verbatim:

```text
Use teachers to label or align.
Never let teachers define the substrate.
Never fold teacher embeddings directly into the main versor path.
Only admit teacher outputs through typed, versioned, checksumed hints.
```

## 5. Phased sequence (priority order, no calendar)

1. **Doctrine** — ADR + spec + eval plan locked (PR-1, this).
2. **Deterministic substrate** — canonicalizer, checksums, resample, lexer, parser, operators,
   compiler (PR-2).
3. **Governance** — pack artifacts, adapter, mount/gate/checksum tests (PR-3).
4. **Evaluation** — fixtures, expected IR, expected projection hashes, gate table (PR-4).
5. **Delta-CRDT wiring** — arena + merge key + sequential==concurrent proof (PR-5), gated on
   ADR-0180 §1.5.4 (T-1…T-4) green on `main`.
6. **Auxiliary lanes** — Whisper/NeMo/CLAP/EnCodec teachers behind optional extras (PR-6).
7. **Streaming** — stateful incremental compiler preserving continuity across chunk seams
   (later; v1 is offline/whole-buffer).
