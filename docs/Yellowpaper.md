# The CORE Yellowpaper
## **Formal Specification of the Cl(4,1) Versor Engine**

> *Companion to the Whitepaper. All conceptual foundations and design philosophy are in `docs/Whitepaper.md`. This document is the mathematical and implementation specification.*

---

### I. The Mathematical Foundation

#### 1. Why Cl(4,1)

The original CORE architecture used Cl(3,0) — the geometric algebra of 3D Euclidean space. Cl(3,0) has 8 basis elements (scalar, 3 vectors, 3 bivectors, 1 pseudoscalar) and maps onto 2×2 complex matrices via the Pauli isomorphism.

Cl(4,1) is the Conformal Geometric Algebra (CGA) of 3D Euclidean space. It has 32 basis elements and signature (4,1): four positive directions `e1, e2, e3, e4` and one negative direction `e5`. The CGA extension adds two null basis vectors:

```
o = (e5 - e4) / 2        # origin point
∞ = e5 + e4              # point at infinity
```

The key identity that motivates the upgrade:

**In Cl(4,1), a Euclidean point p = (x,y,z) embeds as a null vector:**
```
P = p + (1/2)|p|² ∞ + o
```
**and satisfies:**
```
P · P = 0
```

All conformal transformations (rotations, translations, dilations, inversions) are versors in Cl(4,1). In Cl(3,0), translations required special handling outside the algebra. In Cl(4,1), translations *are* versors — the algebra is fully closed over all conformal motions.

#### 2. Basis Structure

Cl(4,1) has 2^5 = 32 basis blades organized by grade:

| Grade | Count | Basis elements | Interpretation |
|---|---|---|---|
| 0 | 1 | 1 | Scalar |
| 1 | 5 | e1, e2, e3, e4, e5 | Vectors |
| 2 | 10 | e12, e13, e14, e15, e23, e24, e25, e34, e35, e45 | Bivectors |
| 3 | 10 | e123, e124, e125, e134, e135, e145, e234, e235, e245, e345 | Trivectors |
| 4 | 5 | e1234, e1235, e1245, e1345, e2345 | Quadvectors |
| 5 | 1 | e12345 | Pseudoscalar |

**Metric (signature (4,1)):**
```
e1² = e2² = e3² = e4² = +1
e5² = -1
ei · ej = 0  for i ≠ j
```

The geometric product multiplication table is a 32×32 signed permutation matrix, computed once at startup and stored in a `OnceLock<Table>` in `core-rs/src/cl41.rs`.

#### 3. Representation in Code

All multivectors are represented as `[f32; 32]` arrays. The index mapping is fixed:

```
index 0:  scalar (grade 0)
index 1-5:  grade-1 components (e1, e2, e3, e4, e5)
index 6-15: grade-2 components
index 16-25: grade-3 components
index 26-30: grade-4 components
index 31:  pseudoscalar (grade 5)
```

This layout is fixed at the Rust layer and mirrored in the Python algebra modules. All Python–Rust interchange uses this same 32-element f32 array.

---

### II. The Versor Engine — Core Invariant

#### The Versor Condition

A multivector V ∈ Cl(4,1) is a **versor** if and only if:

```
V · reverse(V) = ±1
```

Where `reverse(V)` reverses the order of every basis blade product:
- Grade 0: unchanged (sign +1)
- Grade 1: unchanged (sign +1)
- Grade 2: sign −1
- Grade 3: sign −1
- Grade 4: sign +1
- Grade 5: sign +1

#### The Sandwich Product

The unique allowed field transition is:

```
F_new = V · F · reverse(V)
```

This is the versor sandwich product. Its properties:
- If V is a versor and F is a versor, then F_new is a versor (algebraic closure)
- Preserves grade structure under any conformal transformation
- Reversal is free: `reverse(V)` is computed by sign-flipping grade-2 and grade-3 components in-place

#### Verification

```
versor_condition(F) = ||F · reverse(F) - 1||_F
```

This scalar is zero on the versor manifold. It is computed:
1. **Exactly once** at the injection gate on every input
2. **In tests only** — never in the propagation hot path

Tolerance: `versor_condition(F) < 1e-6` for acceptance.

---

### III. Conformal Geometric Algebra (CGA) Distance

#### The Null Cone

A vector X ∈ Cl(4,1) is **null** if:
```
X · X = 0
```

All embedded Euclidean points live on the null cone. The conformal embedding of point p = (x,y,z):

```
P = xe1 + ye2 + ze3 + (1/2)|p|² e4 + e5
```

(Using the compact basis e4=∞, e5=o convention.) This satisfies P·P = 0 by construction.

#### The Distance Identity

For null vectors X, Y representing Euclidean points:

```
X · Y = -(1/2) d(X, Y)²
```

Where d(X,Y) is Euclidean distance and `·` denotes the grade-0 scalar part of the geometric product.

This identity makes the CGA inner product the **exact** conformal distance. It is the foundation of vault recall.

#### Vault Recall

Given a query versor Q and a vault of stored versors {V_i}:

```
best_match = argmax_i { Q · V_i }
```

This is implemented as a parallel scan in `core-rs/src/vault.rs` via Rayon. The scan is:
- Exact (not approximate)
- Allocation-free per worker thread
- GIL-releasing (Rayon runs outside Python)
- O(N) where N = vault size

No ANN index is used. No approximate neighbor structure is maintained. No index rebuild is required on vault growth.

#### Null Cone Drift

Over long sessions, stored versors can drift off the null cone due to floating-point accumulation. The `null_project()` function in `core-rs/src/cga.rs` resets them:

```
X ← X / sqrt(|X · reverse(X)|)
```

This is called as `VaultStore.reproject()` every N turns. It is not drift correction in the sense of the deleted monitor stack — it is a periodic renormalization required by finite-precision arithmetic on any manifold, and it costs a single division per stored versor.

---

### IV. Holonomy Encoding

Holonomy is the accumulated geometric transformation from traversing a closed path in the vocabulary manifold. It is used to encode prompt context as a single versor that captures the path-dependent structure of the input.

**Forward walk** over word versors w_0, ..., w_n:
```
F = normalize(w_0 · w_1 · ... · w_n)
```

**Reverse walk** with damping (1-α):
```
R = normalize((1-α) · reverse(w_n) · ... · reverse(w_0))
```

**Holonomy:**
```
H = normalize(F · R)
```

Where α ∈ [0,1] is the blend factor (default 0.5). The holonomy versor encodes not just which words appeared, but the order in which they appeared and the curvature of the path they traced.

Implementation: `core-rs/src/holonomy.rs` — the entire computation is a single allocation-free Rust function. At 100-token inputs, this replaces 200+ Python dispatch calls with a single call crossing the PyO3 boundary.

**Boundedness invariant:**
```
||H||_F ∈ [0.5, 2.0]  for any prompt length
```

Verified in `tests/test_holonomy.py` via property-based testing with Hypothesis.

---

### V. The Vocabulary Manifold

The vocabulary manifold is a finite set of null vectors {v_w} ⊂ Cl(4,1), one per token w in the vocabulary.

**Construction:** Each word w is embedded as a null vector via the CGA point embedding:
1. Obtain a 3D semantic coordinate p_w (from a frozen static embedding or from the manifold's coordinate frame)
2. Embed: `v_w = p_w_x·e1 + p_w_y·e2 + p_w_z·e3 + (1/2)|p_w|²·e4 + e5`
3. Verify: `v_w · v_w = 0` (null condition)

**Token projection:** At each generation step:
```
next_token = argmin_w { d_CGA(F_current, v_w) }
               = argmax_w { F_current · v_w }
```

This is a nearest-null-vector scan. For vocabularies up to ~50,000 tokens it is computed in a single vectorized MLX pass.

---

### VI. Persona as CGA Motor

A CGA **motor** is a versor that encodes a screw motion: a combined rotation and translation in conformal space.

```
M = T · R
```

Where T is a translator versor and R is a rotor. Every motor satisfies the versor condition by construction.

Persona application:
```
F_biased = M · F · reverse(M)
```

This rotates and translates the field state within the conformal manifold, biasing generation toward the persona's characteristic region of the vocabulary manifold. It is a single versor product — algebraically closed, no weight overlay, no post-hoc bias vector.

**Motor composition:**
```
M_combined = M_2 · M_1
```

Personas compose. Two persona motors can be combined into a single motor before application. The composition is also a versor.

---

### VII. The Three-Language Contract

| Layer | Language | Entry point | Invariant |
|---|---|---|---|
| Orchestration | Python | `session/context.py` | Reads and writes `FieldState`. Never calls algebra directly — always via `algebra/backend.py`. |
| Backend dispatch | Python | `algebra/backend.py` | Single switch: core_rs if available, pure Python fallback. |
| Algebra kernel | Rust (PyO3) | `core-rs/src/lib.rs` | `[f32; 32]` in, `[f32; 32]` out. No heap allocation in hot path. All errors are `thiserror` named variants. |
| Tensor ops | MLX | `field/propagate.py` | Used for batched matmul and field tensor operations. Stays in UMA. |

**Zero-copy contract:**
- Python passes numpy arrays to Rust via PyO3 buffer protocol
- Rust reads into `[f32; 32]` stack arrays — one copy from Python heap to Rust stack
- Rust returns new `[f32; 32]` as numpy array — one copy from Rust stack to Python heap
- No intermediate heap allocation in the Rust kernel

**GIL contract:**
- `vault_recall` (Rayon parallel scan) releases the GIL before entering Rayon and reacquires after
- All other Rust functions hold the GIL for the duration of the call (fast enough that release is not worth the overhead)

---

### VIII. Verification Invariants (The Implementation Gate)

These are testable predicates. Every invariant has a corresponding test in `tests/`.

| Invariant | Expression | Tolerance | Test file |
|---|---|---|---|
| Versor closure | `\|\|F·reverse(F) - 1\|\|_F` | < 1e-6 | `test_versor_closure.py` |
| Null cone | `\|\|X·X\|\|` for all vault entries | < 1e-6 | `test_null_cone.py` |
| Holonomy boundedness | `\|\|H\|\|_F` | [0.5, 2.0] | `test_holonomy.py` |
| Motor condition | `\|\|M·reverse(M) - 1\|\|_F` | < 1e-6 | (in `test_versor_closure.py`) |
| CGA distance symmetry | `cga_inner(X,Y) == cga_inner(Y,X)` | exact | `test_cga.py` |
| Vault recall self | `recall(V_i, top_k=1)[0] == i` | exact | `test_vault_recall.py` |

These are structural contracts, not regression tests. A failing invariant means the algebra is broken, not the behavior.

---

### IX. The Rust Acceleration Contract

**Performance-critical operations in Rust:**

| Operation | Complexity | Why Rust |
|---|---|---|
| `geometric_product` | O(32²) = 1024 MADs | Called 2-3× per versor_apply; autovectorized at opt-level=3 |
| `versor_apply` | 3× geometric_product | No allocation; entire sandwich product in one stack frame |
| `cga_inner` | O(32) | Called every token decode and every vault recall |
| `vault_recall` | O(N × 32) | Rayon parallel scan across N stored versors |
| `holonomy_encode` | O(2L × 32²) | 2L products for L-token prompt; replaces 2L Python dispatch calls |
| `propagate_batch` | O(B × 32²) | B parallel versor_apply for beam search |

**Build:**
```bash
cd core-rs
maturin develop --release
cargo test
```

---

### X. What Was Deleted and Why

The formal record is in `docs/DELETION_LOG.md`. The summary:

| Deleted subsystem | Algebraic reason |
|---|---|
| `spectral_normalize()` (5/6 call sites) | Compensated for rotor drift in an unclosed operation. Versor sandwich product does not drift. |
| `grade_guard.py` | Grade purity is a consequence of versor products, not a condition to be checked. |
| `_maybe_correct_field()` | Drift correction requires an unclosed operation upstream. The operation was closed instead. |
| `RotorDriftTelemetry` | Measures a symptom. The symptom was eliminated. |
| `HippocampusIndex` (ANN) | CGA inner product is exact. Approximate indexing introduced error into an analytically exact operation. |
| `_compute_g3_energy()` | Pseudoscalar accumulation is impossible when all transitions are versor products. |
| `_stabilize_post_turn_g3()` | Followed from the above. |

---

*CORE Yellowpaper — Versor Engine Edition. For the architectural vision, origin story, seven axioms, and three pillars, see `docs/Whitepaper.md`. For agent instructions and invariant enforcement, see `CLAUDE.md`.*
