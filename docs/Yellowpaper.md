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
1. Obtain a 3D semantic coordinate p_w (from a frozen static embedding or from the manifold’s coordinate frame)
2. Embed: `v_w = p_w_x·e1 + p_w_y·e2 + p_w_z·e3 + (1/2)|p_w|²·e4 + e5`
3. Verify: `v_w · v_w = 0` (null condition)

**Token projection:** At each generation step:
```
next_token = argmin_w { d_CGA(F_current, v_w) }
               = argmax_w { F_current · v_w }
```

This is a nearest-null-vector scan. For vocabularies up to ~50,000 tokens it is computed in a single vectorized MLX pass.

---

### VI. The Sensorium — Modality Protocol Specification

The `sensorium/` layer converts any surface signal into a `(32,)` Cl(4,1) multivector before it reaches `ingest/gate.py`. Every `ProjectionHead` is the Logos-recovery boundary for its modality.

#### `Modality` Enum

```python
class Modality(enum.Enum):
    TEXT   = "text"
    VISION = "vision"
    AUDIO  = "audio"
    MOTOR  = "motor"
```

New modalities must be added here AND register a projection head in `sensorium/registry.py` before any pack can mount.

#### `ProjectionHead[S, F]` Protocol

```python
class ProjectionHead(Protocol[S, F]):
    modality: Modality
    embedding_dim: int  # must be 32 for Cl(4,1)

    def project(self, signal: S) -> mx.array:         # shape (32,)
    def project_batch(self, signals: list[S]) -> mx.array:  # shape (N, 32)
    def verify_unitarity(self, sample: S) -> bool
        # True iff V · reverse(V) = ±1 within 1e-6
```

Note: `core-ai` used shape `(2, 2)` complex (Cl(3,0) Pauli isomorphism). `core` uses shape `(32,)` f32 (Cl(4,1) canonical layout).

#### `ModalityPack[S]` Dataclass

```python
@dataclass(frozen=True, slots=True)
class ModalityPack(Generic[S]):
    pack_id: str                          # "en", "he", "grc", "imagenet-1k", ...
    modality_type: Modality
    projection: ProjectionHead[S] | None  # None for articulation-only modalities
    decoder: SurfaceDecoder[S] | None     # None for perception-only modalities
    vocabulary: ModalityVocabulary[S]     # bidirectional surface ↔ rotor map
    grammar_scaffold: Any                 # versor attractors from vocab/
    checksum_verified: bool
    gate_engaged: bool = True
```

Frozen + slotted: zero per-instance dict overhead, hashable. Type-parameterised: `ModalityPack[str]` and `ModalityPack[np.ndarray]` are not interchangeable at the type level.

#### Mount-Time Failure Modes

| Error | Meaning |
|---|---|
| `MANIFEST_INVALID` | Pack manifest fails integrity check |
| `UNITARITY_VIOLATION` | Projection head produces non-unitary rotor |
| `PROJECTION_NOT_CONVERGED` | Projection head did not converge during validation |
| `GRADE_DECLARATION_MISMATCH` | Declared grades do not match produced grades |
| `MODALITY_NOT_REGISTERED` | Modality not in `sensorium/registry.py` |
| `GATE_NOT_ENGAGED` | Surprise-gate not active (non-text modality during seeding) |

#### Active Modalities

| Pack ID | Modality | Surface type `S` | Status |
|---|---|---|---|
| `en` | TEXT | `str` | Active |
| `he` | TEXT | `str` | Active (Hebrew depth corpus) |
| `grc` | TEXT | `str` | Active (Koine Greek depth corpus) |
| vision adapters | VISION | `np.ndarray` | Planned |
| audio adapters | AUDIO | `np.ndarray` | Planned |
| motor adapters | MOTOR | `np.ndarray` | Planned |

See ADR-0013 for the full protocol specification.

---

### VII. The `core_ingest` Governance Layer — Pre-Gate Specification

The `core_ingest/` layer wraps upstream of `ingest/gate.py`. The gate is not modified.

#### `DeterminismClass`

| Class | Meaning | Auto-Accept Eligible? |
|---|---|---|
| D0 | Fully deterministic, pinned inputs and code | ✅ |
| D1 | Deterministic with pinned external artifact | ✅ |
| D2 | Nondeterministic but replay-captured | ❌ |
| D3 | External unpinned model or API | ❌ |
| D4 | Human / operator proposal | ❌ |

A D2–D4 frontend is structurally forbidden from claiming `AUTO_ACCEPT_ELIGIBLE`. Enforced in `CandidateGeometricPressure.__post_init__`.

#### `CandidateGeometricPressure` Content-Addressing

```
pressure_id  = SHA-256(full canonical packet)    # structural deduplication
semantic_key = SHA-256(kind + modality + lemma + subject + verb + object + payload)
                                                  # convergent-evidence detection
```

Two packets with the same `semantic_key` assert the same claim from different provenance sources. Convergence is tracked by the `IngestCompiler` and surfaced as a confidence signal to downstream consumers.

#### Three-Gate Validation Flow

```
CandidateGeometricPressure batch
    → ProvenanceGate    # SourceSpan integrity, SHA-256 of source material
    → SemanticGate      # span completeness, balanced delimiters, non-empty
    → GovernanceGate    # ReviewLevel, DeterminismClass, ReviewDecision overrides
    → ValidationReport  # per-packet disposition
    → LearningArtifact  # accepted packets → train/ export path
```

#### `StructuralSegmenter` — Why, Not What

LLM extraction was rejected: a language model upstream of the gate is a D3 nondeterministic oracle whose semantic projections would be silently embedded in the field state. The `StructuralSegmenter` carves at *form* boundaries only — the meaning of a span stays inside the field where it belongs. Biblical texts (Hebrew, Koine Greek) are D0 by construction: canonical verse boundaries are fixed. See ADR-0012.

---

### VIII. Persona as CGA Motor

A CGA **motor** is a versor that encodes a screw motion: a combined rotation and translation in conformal space.

```
M = T · R
```

Where T is a translator versor and R is a rotor. Every motor satisfies the versor condition by construction.

Persona application:
```
F_biased = M · F · reverse(M)
```

This rotates and translates the field state within the conformal manifold, biasing generation toward the persona’s characteristic region of the vocabulary manifold. It is a single versor product — algebraically closed, no weight overlay, no post-hoc bias vector.

**Motor composition:**
```
M_combined = M_2 · M_1
```

Personas compose. Two persona motors can be combined into a single motor before application. The composition is also a versor.

---

### IX. The Three-Language Contract

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

### IX-B. Forward Semantic Control — Formal Admissibility Specification

This section provides the precise mathematical specification of the
Forward Semantic Control mechanism (ADRs 0022, 0023, 0024, 0025,
0026). The Whitepaper describes the architectural commitment; this
section is the formal contract.

#### 1. AdmissibilityRegion

An `AdmissibilityRegion` is the triple

```text
R = (I, B, Φ)

where
    I ∈ ℕᵏ        : the admissible token index set (k ≥ 1)
    B ∈ Cl(4,1)   : the relation blade (a multivector, not necessarily simple)
    Φ ∈ Cl(4,1)*  : an optional frame versor (None ⇒ no rotor constraint)
```

Module: `generate/admissibility.py::AdmissibilityRegion`. The region
is constructed once per turn from the proposition graph and is
held immutable for the duration of the generation walk. No
in-walk mutation of `R` is permitted.

#### 2. Destination-side admissibility (ADR-0024)

For a candidate token `t` with versor `V_t ∈ Cl(4,1)`, define the
*destination score*

```text
σ_dest(t, R) = cga_inner(V_t, B)
```

In **threshold mode** (the back-compat default), `t` is *admitted*
iff

```text
admit_threshold(t, R, τ)  ⇔  σ_dest(t, R) > τ
```

where `τ ∈ ℝ` is the `admissibility_threshold` configured per turn.
In **margin mode** (ADR-0026), the admissibility test is on a *pair*
of ranked candidates rather than a single candidate. See §4.

Module: `generate/admissibility.py::check_transition`.

#### 3. Rotor-side admissibility (ADR-0025)

When `R.Φ ≠ None`, the rotor that would advance the field state must
also be admissible. For a rotor `V` and current field state `F`,
define the *post-rotor field*

```text
F' = versor_apply(V, F) = V · F · reverse(V)
```

and the *rotor score*

```text
σ_rotor(V, F, Φ) = cga_inner(F', Φ)
```

The rotor is *admitted* iff

```text
admit_rotor(V, F, Φ)  ⇔  σ_rotor(V, F, Φ) > 0
```

When `R.Φ = None` (or `||Φ|| < 10⁻⁸`), `admit_rotor` returns `True`
unconditionally with `σ_rotor = +∞` as the sentinel.

Module: `generate/rotor_admissibility.py::check_rotor_admissibility`.

**Architectural placement (load-bearing).** This check lives in
`generate/rotor_admissibility.py`, a sibling-but-separate module to
`generate/admissibility.py`. It is **not** placed in
`algebra/versor.py` (would couple algebra to pack-derived
admissibility state and structurally invite grade-projection
"repair" of inadmissible rotors) and **not** in
`field/propagate.py` (forbidden normalization/repair site per
`CLAUDE.md`).

#### 4. Ranked-with-margin gate (ADR-0026)

Given a candidate set `C ⊆ I` and the region `R`, compute the
ranked list

```text
ranked(C, R) = sort_descending_by_score_then_index([
    (t, σ_dest(t, R)) for t in C
])
```

with stable tie-break by index (strict `<` on integer index, never
floating-point comparison on score). Let `(t₁, σ₁), (t₂, σ₂), …` be
the ordered list. The margin verdict is

```text
admit_margin(C, R, δ)  ⇔
    |C| = 1 ∧ σ₁ > 0
  ∨ |C| ≥ 2 ∧ σ₁ > 0 ∧ (σ₁ − σ₂) ≥ δ
```

where `δ ∈ ℝ₊` is the `admissibility_margin`. Default `δ = 0.4`.

The walk admits the top-ranked candidate `t₁` iff
`admit_margin(C, R, δ)` holds; otherwise the inner-loop raises
`InnerLoopExhaustion` with the full ranked list as evidence.

Modules:
`generate/admissibility.py::rank_candidates_by_blade`,
`generate/admissibility.py::check_margin` (returns typed
`MarginVerdict`).

**Why δ on the difference, not τ on the absolute score.** Under
the Cl(4,1) Lorentzian signature, self-`cga_inner` is signed: 23 of
85 tokens in `en_core_cognition_v1` have `σ_dest(t, V_t) < 0`. No
scalar `τ` separates admissible from inadmissible across the
corpus (`separation_quality < 0.8` at every probed `τ`,
characterized in `evals/forward_semantic_control/results/phase4_characterization_combined.json`).
A margin gate is scale-invariant under per-blade norm variation;
it survives where the static threshold fails.

#### 5. Honest refusal (ADR-0024 Phase 2)

When inner-loop admissibility leaves no admissible destination, or
when rotor-side admissibility refuses every candidate, the walk
raises `InnerLoopExhaustion`, a typed subclass of `ValueError`
carrying:

```text
InnerLoopExhaustion(
    reason            : RefusalReason,
    region_label      : str,
    step_index        : int,        # -1 = pre-walk empty intersection
                                    #  ≥0 = in-walk per-step exhaustion
    rejected_attempts : tuple[(int, str, float), ...],
)
```

`RefusalReason` is an enum with stable string values:

| Value | Meaning |
|---|---|
| `"inner_loop_exhaustion"` | Destination-side: no candidate passed `admit_threshold` / `admit_margin`. |
| `"rotor_rejection"` | Rotor-side: candidate passed destination admit, but `admit_rotor` returned `False`. |

The reason value is folded into `compute_trace_hash` payload only
when non-empty, preserving byte-identical hashes for non-refused
turns (back-compat invariant) while making refusals themselves
replay-deterministic.

Module: `generate/exhaustion.py`. Trace fold:
`core/cognition/trace.py::compute_trace_hash`.

#### 6. Composition order at the generation seam

The full per-step admissibility predicate is the conjunction:

```text
admit_step(t, R, F, τ, δ) =
    t ∈ I                                             (region intersection, ADR-0023)
  ∧ admit_destination(t, R, τ, δ)                     (destination, ADR-0024 / 0026)
  ∧ admit_rotor(rotor_for(t), F, R.Φ)                 (rotor, ADR-0025)
```

where `admit_destination` is `admit_threshold` in threshold mode and
`admit_margin` in margin mode. The conjunction is evaluated
left-to-right and short-circuits at the first failing clause; the
clause that failed is encoded in the `RefusalReason` carried by any
subsequent `InnerLoopExhaustion`.

Module: `generate/stream.py::generate` (the seam itself).

#### 7. Replay determinism contract

For any fixed `(state, vocab, persona, region, mode, τ, δ)`, the
output `GenerationResult` is bit-identical across reruns, including
the `admissibility_trace` and (when refused) the `RefusalReason`,
`region_label`, `step_index`, and `rejected_attempts` carried by
`InnerLoopExhaustion`.

This contract is exercised by:

| Lane | Replay tests | File |
|---|---|---|
| Inner-loop admit | 5-rerun byte identity | `tests/test_inner_loop_admissibility.py` |
| Margin gate | 3-rerun replay | `tests/test_margin_admissibility.py` |
| Rotor admissibility | 5-rerun admit + 5-rerun refuse | `tests/test_rotor_admissibility.py` |
| Phase 5 stratified | 3-rerun across 20 cases | `tests/test_phase5_corpus.py::TestReplayDeterminism` |
| Phase 6 demo C1 | 5-rerun on 8 cases, baseline + CORE | `tests/test_phase6_demo.py::TestC1ReplayDeterminism` |

#### 8. Verification invariants added by the chain

| Invariant | Expression | Tolerance | Test file |
|---|---|---|---|
| Refusal is typed | `isinstance(exc, ValueError) ∧ isinstance(exc, InnerLoopExhaustion)` | exact | `test_refusal_contract.py` |
| Reason is enumerated | `exc.reason ∈ RefusalReason` | exact | `test_refusal_contract.py` |
| Margin tie-break is stable | `rank_candidates_by_blade` returns deterministic ordering under exact tie | exact | `test_margin_admissibility.py` |
| Rotor closure preserved | `versor_condition(versor_apply(V, F)) < 1e-6` on admitted rotors | < 1e-6 | `test_rotor_admissibility.py` |
| Mechanism isolated (margin) | per-family `pass_rate_margin = 1.0` across 5 families | exact | `test_phase5_corpus.py` |
| Three-condition demo passes | `c1_pass ∧ c2_pass ∧ c3_pass` | exact | `test_phase6_demo.py` |

These are structural contracts, not regression tests. A failing
invariant means the chain is broken, not the corpus.

---

### X. Verification Invariants (The Implementation Gate)

These are testable predicates. Every invariant has a corresponding test in `tests/`.

| Invariant | Expression | Tolerance | Test file |
|---|---|---|---|
| Versor closure | `\|\|F·reverse(F) - 1\|\|_F` | < 1e-6 | `test_versor_closure.py` |
| Null cone | `\|\|X·X\|\|` for all vault entries | < 1e-6 | `test_null_cone.py` |
| Holonomy boundedness | `\|\|H\|\|_F` | [0.5, 2.0] | `test_holonomy.py` |
| Motor condition | `\|\|M·reverse(M) - 1\|\|_F` | < 1e-6 | (in `test_versor_closure.py`) |
| CGA distance symmetry | `cga_inner(X,Y) == cga_inner(Y,X)` | exact | `test_cga.py` |
| Vault recall self | `recall(V_i, top_k=1)[0] == i` | exact | `test_vault_recall.py` |
| Projection unitarity | `\|\|V·reverse(V) - 1\|\|_F` (sensorium mount) | < 1e-6 | `test_sensorium_mount.py` |
| Ingest D-class gate | D2–D4 ↛ AUTO_ACCEPT_ELIGIBLE (construction) | exact | `test_core_ingest.py` |

These are structural contracts, not regression tests. A failing invariant means the algebra is broken, not the behavior.

---

### XI. The Rust Acceleration Contract

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

### XII. Ratification Contract (ADR-0091 + ADR-0106 + ADR-0109)

The runtime contracts in §I–§XI describe the engine's algebraic
behavior. The ratification contract describes the discipline under
which the *capability ledger* is allowed to make claims about a
domain.

#### Domain Pack Contract v1 (ADR-0091)

A pack manifest at `language_packs/data/<pack_id>/manifest.json`
satisfies the contract iff all nine predicates hold:

1. **lemma_coverage** — declared lemmas resolve in `lexicon.jsonl`.
2. **gloss_coverage_above_floor** — mount-eligible if gloss coverage
   crosses the per-pack floor.
3. **operator_chain_count** — declared operator families each carry
   at least `_CHAINS_PER_OPERATOR_DOMAIN` chains.
4. **intent_shape_coverage** — at least three intent shapes present.
5. **holdout_present** — `evals/<lane>/holdouts/` exists with sealed
   or dev-mode-plaintext cases.
6. **eval_lanes_uniform** — all packs in a multi-pack domain declare
   identical lane sets.
7. **fabrication_control_passing** — phantom / cross-pack / sibling
   refusal classes all clean.
8. **reviewer_resolution** — provenance reviewer id resolves in
   `docs/reviewers.yaml`.
9. **deterministic_replay** — the canonical eval reports reproduce
   under `core test --suite cognition`.

A pack passing all nine earns `status = reasoning-capable` in the
generated ledger row.

#### Expert-Demo Promotion (ADR-0106 + ADR-0109)

The promotion to `status = audit-passed` is contract-gated. The
promotion predicate (`core/capability/expert_demo.py::evaluate_expert_demo`)
requires:

```text
reasoning_capable(D)
∧ ∃ claim ∈ ReviewerRegistry.audit_passed_claims
  : claim.domain_id == D
∧ ReviewerRegistry.can_review(claim.signed_by, D, scope="eval")
∧ claim.evidence_lanes ⊆ ratified_lanes(D)
∧ ∀ lane ∈ claim.evidence_lanes, split ∈ {public, holdout} :
    shape_checker(lane)(result(lane, v1, split))
∧ derive_evidence_digest(D, claim.evidence_revision,
                         claim.evidence_lanes, lane_results)
  == claim.claim_digest
```

The digest function:

```text
derive_evidence_digest(D, rev, lanes, results) =
  SHA-256(JSON.canonicalize({
    domain_id:        D,
    evidence_revision: rev,
    evidence_lanes:   sort(lanes),
    lane_metrics:     {lane: {public: results[lane].public,
                              holdout: results[lane].holdout}
                       for lane in sort(lanes)}
  }))
```

Canonicalization rules: sorted keys, compact separators,
`ensure_ascii=False`. The same lane results must reproduce the same
digest byte-for-byte; this is what makes the gate replay-deterministic.

#### Lane-Shape Registry (ADR-0109)

Threshold dispatch is per-lane-shape, not lane-uniform:

| Shape | Required keys | Pass condition |
|---|---|---|
| `cognition_shape` | `surface_groundedness`, `term_capture_rate`, `intent_accuracy`, `versor_closure_rate` | `≥ 0.95 ∧ ≥ 0.85 ∧ ≥ 0.95 ∧ == 1.0` |
| `accuracy_shape` | `accuracy` *or* `(passed, total)` | `accuracy ≥ 0.95` (computed as `passed/total` if `accuracy` absent) |
| `inference_shape` | `all_pass_rate`, `replay_determinism`, `overall_pass` | `≥ 0.95 ∧ == 1.0 ∧ True` |
| `refusal_shape` | `by_class[*].n`, `.refused`, `.fabricated` | `∀ bucket: refused == n ∧ fabricated == 0` |
| `symbolic_logic_shape` | `accuracy` | `≥ 0.95` |

Lane id → shape resolution is by registry lookup, not metric
introspection. Unknown lanes fail closed.

#### Fail-Closed Discipline

- Unloadable reviewer registry → zero claims → no domain promotes.
- Unregistered lane id → promotion fails with named reason.
- Claim digest drift → promotion refused; ledger row demotes to
  `reasoning-capable`.
- Signer outside `eval` scope → promotion refused.

This is the algebraic specification of the contract layer the
Whitepaper §XIII narrates. The substrate makes both refusal and
promotion first-class; the ratification contract makes the
distinction visible to external readers.

---

### XIII. What Was Deleted and Why

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
