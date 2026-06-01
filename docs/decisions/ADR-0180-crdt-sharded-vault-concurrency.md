# ADR-0180: Delta-CRDT Sharded Substrate for Multimodal Concurrency

**Status:** Accepted (2026-05-31) — Delta-CRDT reference contract locked at gate G1 (ADR-0196). See §5.
**Date:** 2026-05-29 (Proposed) · 2026-05-31 (Accepted)
**Authors:** Joshua M. Shay, Core R&D Engine
**Domains:** `core-rs/src/vault.rs`, `vault/crdt.py`, `sensorium/`, `field/`

## 1. Context & Problem Statement

With the introduction of continuous, high-density sensory modalities
(specifically Native Geometric Vision and Kinematics, forthcoming ADRs), the
ingestion rate of the system shifts from discrete textual tokens to sustained
60+ FPS high-dimensional streams.

The supreme architectural invariant of `core` is **Modality Blindness**: all
senses must project into a singular, unified Conformal Geometric Algebra
Cl(4,1) manifold to achieve Holonomy Resonance (cross-modal unification
without late-fusion neural networks).

However, enforcing this single geometric truth creates a brutal mechanical
bottleneck: **Global Lock Contention**. If the Vision, Audio, and Text adapters
attempt to concurrently mutate a globally shared `Vault` (the epistemic state)
guarded by a standard Mutex or RwLock, the resulting thread contention will
completely choke the M-Series Unified Memory Architecture (UMA) and Ryzen
threading topologies. We risk sacrificing mechanical sympathy for mathematical
elegance.

## 1.5 What's Being Sharded: The Existing Python Ingest Path

Before specifying the CRDT substrate, this section names the single-threaded
Python pipeline that §2 makes concurrent, so the proof obligation in §4.3 can
be grounded against actual code rather than an abstract baseline. Per
CLAUDE.md work-sequencing item 5 ("Rust backend parity only after Python
semantics are locked by tests"), the contracts in §1.5.2 must be covered by
Python tests on `main` before any change to `core-rs/src/vault.rs` lands.

### 1.5.1 Current Ingest Pipeline (single modality, single thread)

```text
surface signal S
  → sensorium/protocol.py :: ProjectionHead.project(S)       # Logos recovery boundary
  → ingest/gate.py                                            # raw-input normalization (allowed)
  → field/state.py :: F                                       # current field state
  → field/operators.py :: versor_apply(V, F) = V * F * rev(V) # algebra-owned transition
  → field/propagate.py                                        # diffusion step
  → vault/decompose.py + vault/store.py                       # exact CGA recall write
  → core/cognition/trace.py :: compute_trace_hash(...)        # deterministic replay anchor
```

The `ProjectionHead` protocol (`sensorium/protocol.py:CL41_DIM = 32`) is
already the modality boundary this ADR claims to defend. The Modality enum
already covers `TEXT | VISION | AUDIO | MOTOR`. §2's "Modality Blindness"
should be re-stated in terms of the existing **Logos-recovery boundary** —
that is the load-bearing CORE concept; "Modality Blindness" is a synonym
worth either dropping or anchoring to `ProjectionHead` in §1.

### 1.5.2 Ordering Properties Under the Current Path

| Step | Operation | Commutative | Associative | Idempotent | Notes |
|---|---|---|---|---|---|
| `ProjectionHead.project` | S → (32,) | n/a | n/a | yes | pure function on S |
| `ingest/gate.py` | normalize → F₀ | no | no | no | site of CGA construction; ordering-dependent |
| `versor_apply` | V · F · rev(V) | **no** | yes | no | non-commutative sandwich |
| `field/propagate` | F → F′ | depends on operator | depends | no | linear-blend diffusion (Threshold 1) |
| `vault/store.write` | append (F, provenance) | **yes** | yes | yes | exact CGA recall; semilattice-eligible |
| `compute_trace_hash` | reduce → bytes | no | no | yes | order-sensitive by construction |

The semilattice claim in §2.2 holds **only** at the `vault/store` layer —
not at `versor_apply` and not at `compute_trace_hash`. The CRDT substrate
must therefore shard *write-accumulation*, not the full ingest path. Any
operation upstream of `vault/store` that the substrate parallelizes must
either (a) be proven order-invariant on its inputs, or (b) carry an explicit
serialization barrier.

### 1.5.3 Trace-Hash Inputs That Must Survive Sharding

`compute_trace_hash` (per `core/cognition/trace.py:27`) currently hashes a
payload that includes `admissibility_trace_hash` among other fields. For the
proof obligation `hash(Sequential_Ingest) == hash(Concurrent_CRDT_Ingest)` to
be checkable:

1. The set of `(F, provenance)` tuples written to the Vault must be identical
   between the sequential and concurrent runs — *as a set*, not as a sequence.
2. The trace-hash reduction must consume vault state in a content-addressed
   order (e.g. sorted by a deterministic key on the multivector + provenance),
   not in wall-clock arrival order. The merge kernel in §2.2 currently
   describes time-driven flushes ("every 16ms"); §4.3 cannot hold under that
   policy unless the *hashing* step re-sorts.
3. `admissibility_trace_hash` and any other upstream-of-Vault hash inputs
   must be computed on the serialized portion of the path (§1.5.2 row 2-4),
   not on the sharded portion.

> **Amendment (2026-05-29, post T-1…T-4).** Finding 1 of
> [docs/audit/ADR-0180-t1-t4-findings.md](../audit/ADR-0180-t1-t4-findings.md)
> establishes that `compute_trace_hash` (`core/cognition/trace.py:35`) folds
> `vault_hits` — an **int count** — and *not* vault contents. The
> content-addressed re-sort obligation in point 2 is therefore **vacuous at the
> `compute_trace_hash` layer today**: there are no vault contents in the payload
> to reorder. The obligation it names is real, but it lives at **`recall()`** —
> the recall *result set* and its count must be order-invariant under a
> reordered deque (pinned by T-2b,
> `recall_result_set_invariant_to_insertion_order`). Point 2 above is amended to
> apply to the **recall result set and to any future contents-bearing hash**,
> not to today's count-only `compute_trace_hash`. The re-sort requirement on the
> hashing step becomes live again only if/when vault contents (beyond a count)
> enter the trace-hash payload.

### 1.5.4 Pre-Refactor Test Obligations (Python-side, on `main`)

Before any code in `core-rs/src/vault.rs` changes, the following must exist
as Python tests and be green on `main`:

- **T-1**  Set-equality of vault writes under shuffled single-thread ingest:
  for any ingest sequence `[s₁, …, sₙ]` and any permutation `π`, the
  resulting `vault.store` contents are equal as sets.
- **T-2**  `compute_trace_hash` invariance under set-equal vault states with
  identical upstream serialized prefixes. If this fails today, §4.3 cannot
  hold and the reduction step needs a content-addressed sort first.
- **T-3**  `versor_apply` non-commutativity is asserted (negative test): if a
  future refactor accidentally makes it commutative, it will be caught here
  rather than masked by the CRDT substrate.
- **T-4**  `ProjectionHead.project` purity: same `S` → byte-identical `(32,)`
  output across repeated calls, across threads, across processes.

T-1 and T-2 are the load-bearing ones. T-3 and T-4 are guards against silent
drift.

### 1.5.5 What Stays Out of Scope of This ADR

- **Approximate recall.** CLAUDE.md §Core Primitives is non-negotiable: exact
  CGA recall, no HNSW/ANN/cosine. The CRDT merge produces *eventually-exact*
  recall, never approximate. The sub-50ms window in §3.2 is a **latency**
  window for write-visibility, not a **fidelity** window — once merged, recall
  is exact byte-for-byte.
- **Hidden background execution.** The "Merge Kernel" in §2.2 must be an
  explicitly-mounted runtime component with a named owner and observable
  state, not a daemon thread. CLAUDE.md §Security forbids hidden background
  execution; the kernel must surface its pending-delta count in
  telemetry/`TurnEvent` for replay evidence.
- **MLX/UMA hardware optimization.** §2.3's zero-copy MLX handshake is a
  follow-up ADR; it is mentioned here as horizon-setting only. The CRDT
  substrate itself must work on a pure-CPU Rust path first.

### 1.5.6 Cross-References

- ADR-0054 (Vault Recall Indexing + Batching) — the matrix-cache contract the
  sharded path must preserve at the read side.
- `docs/runtime_contracts.md` — the response/telemetry/memory/identity
  contracts that §3.1's "zero modification of `anti_unifier` and `carrier`"
  claim is being measured against.
- CLAUDE.md §Normalization Rules — `ingest/gate.py` remains the **only**
  allowed pre-Vault normalization site; the CRDT substrate must not introduce
  per-shard normalizers.

## 2. Decision: Logical Unity, Physical Sharding

We will resolve this tension by decoupling the logical manifold from the
physical memory layout. The manifold remains singular and mathematically
continuous, but the underlying Rust substrate will heavily shard the ingestion
pathways.

We adopt an architecture based on **Delta-State CRDTs (Conflict-Free Replicated
Data Types)** acting over lock-free, thread-local arenas, resolved via
asynchronous Semilattice Joins.

### 2.1 Thread-Local Sensory Arenas

* **Deprecation of Direct Global Writes:** Adapters (`sensorium/adapters/*`)
  are strictly forbidden from writing directly to the global `epistemic_state`.
* **Local Delta Caches:** Each active modality adapter is assigned a
  thread-local memory arena in `core-rs`. As dense geometric primitives
  (spheres, lines, motors) are generated by the `ProjectionHead`, they are
  written lock-free into this local cache.

### 2.2 The Semilattice Join (CRDT Merge)

* The geometric `Field` operates as an additive accumulation of knowledge. It
  mathematically satisfies the properties of a **Join Semilattice**
  (commutativity, associativity, and idempotence of state integration).
* At predefined intervals (e.g., every 16ms to match 60fps, or at semantic
  chunk boundaries), the local thread generates a `Delta` — a snapshot of the
  newly ingested multivectors.
* A background, lock-free **Merge Kernel** sweeps these Deltas and folds them
  into the global `Vault` using atomic compare-and-swap (CAS) operations or
  unified memory tensor reductions via MLX.
* **Content-addressed tiebreak (amendment 2026-05-29, post T-1…T-4).** Finding 2
  of [docs/audit/ADR-0180-t1-t4-findings.md](../audit/ADR-0180-t1-t4-findings.md)
  shows `vault_recall` breaks equal-score ties by ascending deque index
  (`vault/store.py`), and index is assigned by storage order. Two entries with
  *exactly equal* CGA inner scores can therefore surface in an order that depends
  on arrival — which the sub-50ms reorder window (§3.2) can perturb. The Merge
  Kernel must assign deque order to tie-scored entries by a **content-addressed
  key on the multivector + provenance bytes**, not by arrival order, so that
  equal-score recall is total and arrival-independent. This is the general-path
  analog of the `(canonical_sha256, ir_sha256, projection_sha256)` merge key
  ADR-0181 §2.2 already uses for audio; the kernel adopts the same discipline for
  every modality.

### 2.3 Nanospin Orchestration & Zero-Copy Symbiosis

* **Python/Rust Boundary:** Python will write raw sensory arrays into
  lock-free Ring Buffers (e.g., `crossbeam` channels).
* **Rust Worker Pool:** A pool of pinned Rust worker threads will continuously
  poll these buffers using **nanospin** loops to avoid OS context-switching
  latency.
* **MLX UMA Handshake:** For cross-modal resonance (calculating
  `cga_inner(text_F, vision_F)` across millions of points), Rust will pass raw
  memory pointers (`&[f32]`) directly to the MLX Neural Engine. MLX will
  perform the massively parallel tensor reduction without ever copying the data
  across a PCIe bus.

## 3. Consequences

### 3.1 Positive Impacts (The Exploits)

* **Zero Ingestion Contention:** The vision pipeline can run at the maximum
  framerate allowable by the neural backbone without ever being blocked by
  textual or auditory processing.
* **Hardware Saturation:** Safely maximizes utilization of Apple Silicon
  unified memory and multi-core Ryzen architectures.
* **Mathematical Purity Maintained:** The `anti_unifier` and `carrier` logic
  requires zero modification. They simply operate on a slightly delayed,
  eventually-consistent global state.

### 3.2 Negative Impacts (The Risks)

* **Eventual Consistency Latency:** There will be a sub-50ms window where a
  visual primitive exists in the local Delta Cache but has not yet merged into
  the global Vault. During this micro-window, cross-modal resonance with a
  simultaneous text token cannot occur.
* **Memory Overhead:** Maintaining the local arenas and managing the Delta
  garbage collection increases baseline memory footprint.

## 4. Execution Plan & Proof Obligations

1. **`core-rs` Mutation:** Refactor `core-rs/src/vault.rs` to implement the
   `LocalArena` struct and the `SemilatticeDelta` trait.
2. **MLX Integration:** Define the zero-copy C-FFI boundary between the Rust
   arenas and the MLX distance-calculation tensors.
3. **Trace Invariance Proof:** Extend `evals/` to prove that
   `hash(Sequential_Ingest) == hash(Concurrent_CRDT_Ingest)`. The order of
   asynchronous merging must not alter the final unified geometric topography.

## 5. Status: Accepted — G1 reference-contract lock (2026-05-31)

This ADR is accepted at **gate G1** of the native-substrate adoption ladder
(ADR-0196 / `docs/zig/adoption-gates.md`): the Delta-CRDT substrate now has a
**locked, executable reference contract**. This corresponds to slice **ZC-0**
("contract pinning") in `docs/zig/crdt-substrate/implementation-slices.md`,
whose exit gate is *"Python/Rust reference behavior is locked."*

### 5.1 The locked contract

- **Canonical reference:** `vault/crdt.py` — `ArenaEntry`, `Delta`,
  `LocalArena`, `merge_kernel`, `canonical_bytes`, `delta_hash`. Pure
  content law: no normalization, no versor closure/repair, no field mutation,
  no global Vault writes (CLAUDE.md §Normalization Rules / §Core Primitives).
- **Content order** is by the IEEE-754 bit pattern of the 32 versor components,
  then the provenance bytes — never arrival order (§2.2 amendment). `+0.0`,
  `-0.0`, and distinct NaN payloads are distinct content (bit-addressed).
- **Canonical serialization** (`canonical_bytes`) is the cross-language
  contract; `delta_hash` is its SHA-256. Layout (all little-endian):

  ```text
  u64   entry_count
  per entry (canonical order):
    32 x f32   versor components (IEEE-754, little-endian, 4 bytes each)
    u64        provenance_length
    bytes      provenance
  ```

### 5.2 Proof obligations (all failable; CLAUDE.md §Schema-Defined Proof Obligations)

| Obligation | Test |
|---|---|
| C-1 commutativity, C-2 associativity, C-3 idempotence | `tests/test_crdt_semilattice_contract.py` |
| C-4 permutation-invariant merge, C-5 duplicate-delta no-op, kernel == join-fold | `tests/test_crdt_semilattice_contract.py` |
| Content ordering, distinct-provenance retention, signed-zero / NaN bit-addressing | `tests/test_crdt_content_ordering.py` |
| C-7 arena push never mutates the global Vault; snapshot/merge purity | `tests/test_crdt_no_global_write_from_arena.py` |
| Golden corpus: canonical bytes + merge hash regression-lock | `tests/test_crdt_semilattice_contract.py` + `tests/fixtures/crdt/merge_fixtures.json` |
| **Rust ↔ Python byte-parity** | `core-rs/tests/test_crdt_hash_parity.rs` (+ `Delta::canonical_bytes` in `core-rs/src/vault.rs`) |

The golden corpus is regenerated deterministically from the Python reference by
`tests/fixtures/crdt/_generate.py` (single source of truth; it also emits the
Rust-side expected hex). Mutation-tested: removing dedup breaks C-3/C-5;
ordering by arrival breaks C-1.

### 5.3 §4 execution-plan status

1. **`core-rs` LocalArena / SemilatticeDelta** — **done** (`core-rs/src/vault.rs`,
   `core-rs/tests/test_arena.rs`), now extended with `canonical_bytes` and
   pinned to the Python reference by `test_crdt_hash_parity.rs`.
2. **MLX zero-copy integration** — **deferred / out of scope** per §1.5.5
   (hardware optimization; not required for the substrate contract).
3. **Trace-invariance proof** — the *substrate-level* property is locked: the
   merge kernel is permutation-invariant and `delta_hash` is replay-stable
   (C-4). The full end-to-end `hash(Sequential_Ingest) ==
   hash(Concurrent_CRDT_Ingest)` eval over a live concurrent modality pipeline
   remains future work, to land when modality ingestion is wired — it rides on
   the contract locked here.

### 5.4 Boundary — what this ADR does NOT authorize

This ADR locks the **reference contract only**. It does **not** authorize any
Zig implementation. The Zig CRDT prototype (slices **ZC-1 and beyond**) remains
at **gate G2** under ADR-0196 and requires a separate ADR before any Zig code,
backend selector, or runtime wiring. The Rust substrate likewise stays a
pure-CPU, Python-unbound substrate (§1.5.5) until a downstream ADR binds or
promotes it.
