# Zig Guidance — Delta-CRDT Substrate

**Status:** doctrine / prototype candidate  
**Component:** Delta-CRDT arena, delta, join, merge kernel, content-addressed ordering  
**Primary governing ADR:** ADR-0180

This is the strongest near-term Zig candidate in CORE.

The CRDT substrate is not semantic cognition. It is the mechanical substrate for concurrent modality write accumulation: thread-local arenas emit canonical deltas, and an explicitly mounted merge kernel folds those deltas into a global Vault-visible state without making final recall approximate or arrival-order dependent.

---

## Why this component is suitable for Zig

The CRDT substrate wants properties Zig is good at providing:

- explicit allocator ownership;
- small native surface area;
- deterministic byte-level ordering;
- stable C ABI;
- edge-native build story;
- predictable memory layout;
- no garbage collector;
- no hidden runtime;
- precise caller-owned buffer contracts.

This is not a broad language preference. It is a substrate fit.

---

## Existing contract to preserve

ADR-0180 states that the semilattice claim holds only at the `vault/store` layer, not at `versor_apply`, not at `field/propagate`, and not at trace reduction. The CRDT substrate must shard write accumulation only.

Required law:

```text
ProjectionHead.project       pure signal projection
versor_apply                 non-commutative, do not shard unless serialized
field propagation            not a CRDT merge
vault/store.write            semilattice-eligible write accumulation
recall result ordering       content-addressed, not arrival-addressed
```

The existing Rust substrate already implements the conceptual shape:

```text
ArenaEntry { versor: [f32; 32], provenance: Vec<u8> }
Delta      { entries: sorted/deduped ArenaEntry list }
LocalArena { thread-local write cache }
merge_kernel(deltas) -> canonical Delta
```

Zig may challenge this substrate only by preserving the same laws.

---

## What should be in Zig

A Zig CRDT lane should include:

```text
core-zig/src/crdt/entry.zig
core-zig/src/crdt/arena.zig
core-zig/src/crdt/delta.zig
core-zig/src/crdt/merge.zig
core-zig/src/crdt/hash.zig
core-zig/src/crdt/ffi.zig
include/core_crdt.h
```

### `ArenaEntry`

Should represent one content-addressed write:

```text
versor: [32]f32
provenance: []const u8
```

The content key is:

```text
raw IEEE-754 f32 bits of all 32 components
+ provenance bytes
```

The substrate must not compare floats numerically for canonical ordering. It must compare bytes/bits to avoid platform-dependent `NaN`, `-0.0`, and `+0.0` behavior.

### `LocalArena`

Should be thread-local and share-nothing.

Allowed:

```text
push local entries
snapshot to Delta
clear/drain if explicitly requested by owner
report pending count
```

Forbidden:

```text
write global Vault
spawn hidden merge thread
normalize entries
repair bad versors
infer epistemic status
call object-store/S3/cloud code
```

### `Delta`

A `Delta` must be canonical:

```text
entries sorted by content key
byte-identical duplicates removed
stable independent of insertion order
```

### `merge_kernel`

The merge kernel must be explicit, not hidden.

Required behavior:

```text
input: list of Deltas
output: one canonical Delta containing their union
law: permutation-invariant
law: duplicate-delta idempotent
law: content-addressed ordering only
```

---

## Minimum C ABI sketch

```c
typedef struct CoreCrdtArena CoreCrdtArena;
typedef struct CoreCrdtDelta CoreCrdtDelta;

typedef struct CoreCrdtError {
    int code;
    char message[256];
} CoreCrdtError;

CoreCrdtArena* core_crdt_arena_new(void);
void core_crdt_arena_free(CoreCrdtArena* arena);

int core_crdt_arena_push(
    CoreCrdtArena* arena,
    const float versor[32],
    const unsigned char* provenance,
    unsigned long provenance_len,
    CoreCrdtError* err
);

int core_crdt_arena_snapshot(
    const CoreCrdtArena* arena,
    CoreCrdtDelta** out_delta,
    CoreCrdtError* err
);

void core_crdt_delta_free(CoreCrdtDelta* delta);

int core_crdt_delta_join(
    const CoreCrdtDelta* a,
    const CoreCrdtDelta* b,
    CoreCrdtDelta** out_delta,
    CoreCrdtError* err
);

int core_crdt_merge_kernel(
    const CoreCrdtDelta* const* deltas,
    unsigned long delta_count,
    CoreCrdtDelta** out_delta,
    CoreCrdtError* err
);

int core_crdt_delta_hash(
    const CoreCrdtDelta* delta,
    unsigned char out_sha256[32],
    CoreCrdtError* err
);
```

This is illustrative, not final. The final ABI must be ratified before implementation is considered supported.

---

## What must stay out of Zig

The CRDT substrate must not own:

- epistemic status promotion;
- review decisions;
- teaching proposal admission;
- pack ratification;
- semantic normalization;
- recall scoring policy beyond canonical store order;
- object-store sync;
- hidden background execution;
- modality compilation semantics, except when called as a separate compiler component.

The CRDT substrate is storage-order law, not cognition.

---

## Required proof obligations

### C-1 — Commutativity

```text
join(a, b) == join(b, a)
```

### C-2 — Associativity

```text
join(join(a, b), c) == join(a, join(b, c))
```

### C-3 — Idempotence

```text
join(a, a) == a
```

### C-4 — Permutation invariance

```text
merge_kernel([d1, d2, d3]) == merge_kernel(any_permutation([d1, d2, d3]))
```

### C-5 — Duplicate re-ingest is no-op

```text
merge(existing, already_seen_delta) == existing
```

### C-6 — Recall order invariance

Equal-score recall must not depend on wall-clock arrival. The canonical merged order must be content-addressed so tie breaks are replay-stable.

### C-7 — No hidden global mutation

Tests must prove that pushing to an arena never mutates the global Vault. Only explicit merge publication may alter the global visible state.

---

## Migration sequence

1. Keep Rust implementation as incumbent.
2. Add Python tests that pin CRDT laws against the current behavior.
3. Add Zig prototype behind `CORE_CRDT_BACKEND=zig`.
4. Compare Zig against Rust/Python reference on canonical fixtures.
5. Add benchmark only after parity passes.
6. Promote only if Zig wins on ABI, deployment, memory, or performance.

---

## Promotion criteria

Zig should become the preferred CRDT substrate only if it demonstrates:

- equal or stronger deterministic law coverage;
- simpler C ABI for modality compilers and edge runtime;
- explicit allocation lifecycle that is easier to audit than the incumbent;
- no loss in exact recall behavior;
- observable merge state;
- clean failure when absent or stale.

Until then, Zig remains a prototype lane, not a replacement.
