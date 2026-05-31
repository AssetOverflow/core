# Zig Guidance — Algebra and Recall Kernels

**Status:** doctrine / challenge candidate  
**Component:** Cl(4,1), exact recall, batch recall, graph diffusion

Rust is the incumbent native backend for algebra and exact recall. Zig may challenge specific kernels only through parity and benchmark evidence.

---

## Current incumbent

The current `core-rs` backend already covers:

- Cl(4,1) geometric product;
- versor apply / closure path;
- CGA inner product;
- exact vault recall;
- exponential-map unitization;
- graph diffusion.

It is built as a PyO3/NumPy extension, uses Rayon for parallel recall, and has parity tests across multiple algebra surfaces.

Therefore, Zig should not start by replacing these surfaces. It should start by challenging uncovered or ABI-sensitive surfaces.

---

## Best Zig algebra candidate: `vault_recall_batch`

`vault_recall_batch` is currently Python-canonical and has no Rust binding. It is a good challenge kernel because:

- the semantics are already precise;
- scoring is exact CGA diagonal-metric accumulation;
- top-k ordering is deterministic;
- batch input/output maps naturally to caller-owned buffers;
- C ABI may be cleaner than a PyO3-only path;
- performance can be measured without touching semantic runtime.

### Candidate ABI

```c
int core_recall_batch_f32(
    const float* matrix,          /* N x 32, row-major */
    unsigned long n,
    const float* queries,         /* B x 32, row-major */
    unsigned long b,
    unsigned long top_k,
    unsigned int* out_indices,    /* B x top_k */
    float* out_scores,            /* B x top_k */
    CoreNativeError* err
);
```

The caller owns output buffers. Zig writes into them. No allocation is required in the hot path except optional scratch passed explicitly by later ABI versions.

---

## Required recall invariants

Any Zig recall kernel must preserve:

```text
exact CGA metric
component-serial accumulation if bit-identity requires it
descending score order
ascending index tie-break unless the store layer supplies a content-addressed order
top_k truncation semantics
empty input behavior
shape errors as typed failures
no approximate search
```

Forbidden:

```text
cosine fallback
ANN/HNSW/FAISS-like index
learned projection
score normalization
hidden reordering
GPU nondeterminism without proof
```

---

## Geometric product / versor apply

These are not first Zig targets.

They may become candidates only if:

- the Rust path becomes difficult to build/deploy;
- C ABI is needed by non-Python hosts;
- Zig produces equal behavior with simpler lifecycle;
- performance exceeds Rust on representative workloads;
- parity tests prove closure behavior exactly.

The closure invariant remains:

```text
versor_condition(F) < 1e-6
```

No native path may hide violations by repair outside the approved closure boundary.

---

## Graph diffusion

Graph diffusion is a possible Zig candidate after CRDT and audio work.

It is suitable because:

- input/output buffers are regular arrays;
- edge lists are compact;
- memory ownership can be explicit;
- a C ABI could support edge-native runtimes.

It is not urgent because the Rust implementation already removed major marshalling overhead through zero-copy NumPy views.

---

## Unitize / expmap

Unitization can be native, but it is dangerous to duplicate casually. Any Zig implementation must be tested against the existing algebra contract and audio compiler closure gates.

Required:

- same boost/rotation plane semantics;
- same f32/f64 strategy as the reference surface;
- same behavior on near-zero input;
- same post-condition threshold;
- no hidden fallback rotor unless the reference does the same.

---

## Promotion sequence for any Zig algebra kernel

1. Identify exact reference surface.
2. Add parity tests independent of Zig.
3. Add Zig implementation behind explicit selector.
4. Run parity fixtures.
5. Add benchmark fixtures.
6. Compare Rust, Python, and Zig.
7. Promote only if Zig wins a named mechanical criterion.

---

## Decision posture

For algebra kernels, Zig is a challenger, not the incumbent.

The correct first Zig algebra target is not the full Cl(4,1) backend. It is `vault_recall_batch` or another uncovered, buffer-regular, ABI-friendly kernel.
