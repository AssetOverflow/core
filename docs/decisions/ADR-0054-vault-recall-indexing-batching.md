# ADR-0054 — Vault Recall: Matrix-Cache Indexing + Batched API; Holdout Split Wired

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay

---

## Context

Two doctrine-aligned items from CLAUDE.md were still open after
ADR-0053:

1. **CLAUDE.md item #4 — "Add exact vault recall indexing/batching
   without approximate search."**  ADR-0019 Stage 1 vectorised the
   single-query CGA scan inside `algebra.backend.vault_recall`, but
   the **deque → ndarray conversion** still happened on every recall,
   and there was no batched-query API.  Repeated recalls against a
   slowly-growing vault paid the conversion cost each call.
2. **Holdouts not in the official eval runner.**  The cognition lane
   has had a 19-case plaintext holdout file
   (`evals/cognition/holdouts/cases_plaintext.jsonl`) since the lane
   was set up, but `core eval cognition --split` accepted only `dev`
   and `public`.  Holdout numbers existed only via ad-hoc scripts
   spawned during ADR-0053.

Both items are minimal-doctrine work: no algebra change, no new
approximation, no new normalisation, no hot-path repair.  Bundled
together because both touch the validation/eval surface.

---

## Decision

### Part 1 — Vault recall indexing + batching

**`VaultStore` matrix cache (`vault/store.py`).**

A lazily-built `_matrix_cache: np.ndarray | None` is held on the
store.  It is `None` initially and after any mutation; the first
`recall` after a mutation rebuilds it via
`np.asarray(self._versors, dtype=np.float32)`.  Invalidation hooks:

- `store()`     — always invalidates (append shifts the deque view).
- `reproject()` — invalidates (every entry replaced).
- `_rebuild_index()` — invalidates (called on max-entries eviction).

The cache is read-only from the recall path; `vault_recall` receives
it via a new optional `prebuilt_matrix=` kwarg and skips the
deque → ndarray conversion when supplied.  No shared mutable state
is held across calls — the matrix is the same buffer between recalls
only while no mutation has happened.

**Batched recall (`algebra.backend.vault_recall_batch`).**

New function with signature
`vault_recall_batch(matrix, queries, top_k) -> list[list[(int, float)]]`.
Accepts `(N, D)` matrix and `(B, D)` (or `(D,)`) queries, returns
one ranked list per query.  Scoring uses the same diagonal CGA
metric and accumulates **in component-serial order**:

```python
scores = np.zeros((B, N), dtype=np.float32)
for i in range(D):
    scores += (_CGA_INNER_METRIC[i] * M[:, i])[None, :] * Q[:, i, None]
```

Folding component-by-component preserves bit-identity with the
single-query path's float32 addition order.  Tiebreak rule
(descending score, ascending index) is identical.

**`VaultStore.recall_batch`.**

Public sibling to `recall`.  Same per-query semantics — exact-self-
match promotion via the byte-key index, optional `min_status`
filter, score=+inf for exact hits — but the underlying scoring scan
is a single component-serial sweep over the cached matrix.

### Part 2 — Wire `--split holdout`

`evals/framework.py`:

- `LaneInfo.holdout_cases_path(version)` resolves the first existing
  of `holdouts/cases.jsonl`, `holdouts/cases_plaintext.jsonl`,
  `holdouts/<version>/cases.jsonl`.  Sealed (`*.age`) holdouts are
  **not** decrypted here — that path stays in
  `evals.holdout_runner.run_holdout`, which enforces aggregate-only
  output by trust-boundary contract.
- `run_lane(split="holdout")` reads that path and dispatches to the
  lane's `run_lane(cases, config=...)` like any other split.

`core/cli.py`:

- `--split` argparse `choices` extended to
  `{"dev", "public", "holdout"}`.
- Example added to `EPILOG`.

---

## Why this is doctrine-aligned

- **No approximate search.**  Both the matrix cache and
  `vault_recall_batch` are indexing/vectorisation changes only;
  scoring arithmetic is unchanged.
- **No hidden normalisation, no hot-path repair.**  The cache is
  invalidated, not "auto-rebuilt to fix drift."  `reproject()` was
  already the canonical drift-repair path; this ADR only invalidates
  the cache when it runs.
- **No shared mutable state across recalls.**  The cache buffer is
  read by `vault_recall` via a kwarg; nothing in the recall path
  mutates it.  Mutation paths (store / reproject / eviction) clear
  it explicitly.
- **`versor_condition < 1e-6` invariant untouched.**  No field is
  constructed, normalised, or transformed.
- **Holdouts run via the same harness as dev/public.**  No parallel
  scoring path was added; the trust boundary on sealed holdouts is
  preserved by routing plaintext through the standard runner and
  leaving the encrypted path to `holdout_runner`.

---

## Characterisation

### Vault recall — bit-identity gate

`tests/test_vault_recall_indexing_batch.py` adds 21 tests.  The
batched path is verified bit-identical to per-query
`vault_recall` across three seeds × 7 queries × N=137 — every
index sequence and every float32 score matches exactly.

The pre-existing `tests/test_vault_recall_vectorised.py` (ADR-0019
Stage 1 gate) continues to pass — the single-query path is
unchanged when no `prebuilt_matrix` is passed.

### Eval lanes — first official holdout run

```
core eval cognition --split holdout
  cases                : 19
  intent_accuracy      : 100.0%
  surface_groundedness :  94.7%
  term_capture_rate    :  70.8%
  versor_closure_rate  : 100.0%

core eval cognition --split dev
  cases                : 13
  intent_accuracy      : 100.0%
  surface_groundedness : 100.0%
  term_capture_rate    :  78.6%
  versor_closure_rate  : 100.0%

core eval cognition --split public
  cases                : 13
  intent_accuracy      : 100.0%
  surface_groundedness : 100.0%
  term_capture_rate    :  91.7%
  versor_closure_rate  : 100.0%
```

The single surface_groundedness miss on holdouts is the predicted
`correction_truth_040` case — see ADR-0053 scope-limits.  Term
capture on holdouts is the next-cheapest pull (echo the corrected-
subject lemma in the CORRECTION acknowledgement), candidate for a
follow-up ADR.

### Lanes (all green)

```
core test --suite smoke         67 passed
core test --suite cognition    121 passed
core test --suite runtime       19 passed
core test --suite teaching      17 passed
core test --suite packs          6 passed
core test --suite algebra      132 passed
```

---

## Consequences

### What changes

- `algebra/backend.py` gains `vault_recall_batch` and an optional
  `prebuilt_matrix=` kwarg on `vault_recall`.
- `vault/store.py` gains a lazy matrix cache, cache-invalidation
  hooks on mutation paths, and a `recall_batch` method.
- `evals/framework.py` gains `LaneInfo.holdout_cases_path` and a
  `"holdout"` branch in `run_lane`.
- `core/cli.py` `--split` now accepts `"holdout"`.

### What does not change

- Single-query `vault_recall` semantics — same scores, same order,
  same Rust dispatch.
- ADR-0019 Stage 1 bit-identity contract — still gated.
- `versor_condition < 1e-6` invariant unaffected.
- Encrypted holdout decryption — still owned by
  `evals.holdout_runner.run_holdout`; aggregate-only output
  contract preserved.
- All five core lanes remain green.
- Cognition eval numbers on dev/public unchanged from ADR-0053.

### Scope limits

- **No Rust binding for `vault_recall_batch` yet.**  Python is the
  canonical path; a Rust batched binding can be added under a
  separate ADR with a parity gate analogous to ADR-0019.
- **Holdout case_details are written when run via `--split
  holdout`** because the standard `LaneResult.case_details` carries
  the lane runner's output.  The trust-boundary doctrine in
  `evals/holdout_runner.py` applies to **sealed** (encrypted)
  holdouts — the cognition holdout file is plaintext-in-tree by
  intent (development), so writing details is consistent.  Once a
  sealed cognition holdout exists, callers must use
  `holdout_runner.run_holdout` (aggregate-only) instead of
  `framework.run_lane`.

---

## Cross-References

- [ADR-0019](./ADR-0019-vault-recall-vectorisation.md) — Stage 1
  vectorised single-query path this ADR builds on (if a file by
  that name does not exist, the contract lives in
  `tests/test_vault_recall_vectorised.py`).
- [ADR-0053](./ADR-0053-cognition-lane-closure.md) — last cognition
  lane work; its scope-limits section predicted the holdout
  number.

---

## Verification

```
tests/test_vault_recall_indexing_batch.py — 21 tests, all green
tests/test_eval_holdout_split.py          — 10 tests, all green
tests/test_vault_recall_vectorised.py     —  4 tests still green
tests/test_vault_recall_rust_parity.py    —  pre-existing parity gate still green
```

The non-negotiable field invariant (`versor_condition(F) < 1e-6`)
is preserved: this ADR adds an indexing cache, a batched scan
function, and a CLI flag — no algebra change, no field
construction, no normalisation.
