# Zig Native Substrate — Status & Handoff

**Last updated:** 2026-05-31
**Maintainer note:** update this page whenever a gate advances or a slice ships.

This is the single portable *"where we are / what's next"* page for the Zig
native-substrate work. The doctrine and the definition of each step live in the
sibling docs; **this page records execution state, the immediate next action,
and environment gotchas** so any operator — or a fresh terminal, or another
agent — can resume cold.

> Cold-start read order: this page → [`README.md`](README.md) (decision
> package) → [`adoption-gates.md`](adoption-gates.md) (G0–G8) → the per-component
> slice docs.

---

## TL;DR

- CORE is **not** converting to Zig. Zig is a **Ring-1 native-substrate
  candidate**, adopted component-by-component through gates **G0–G8**. Python
  stays the semantic source of truth; Rust stays the incumbent algebra backend.
- **Ratified:** ADR-0196 (doctrine). **Locked:** the Delta-CRDT reference
  contract (ADR-0180 → Accepted, **gate G1**).
- **No Zig code is authorized.** The next Zig step (ZC-1) requires a **new ADR
  clearing gate G2**.
- This is **opportunistic Ring-1 work. Ring-2 GSM8K comprehension remains the
  live priority** — do not let substrate work displace it.

---

## What shipped

| PR | Scope | State |
|---|---|---|
| [#509](https://github.com/AssetOverflow/core/pull/509) | ADR-0196 doctrine ratification (`docs/zig/**` + README section) | open |
| [#511](https://github.com/AssetOverflow/core/pull/511) | ADR-0180 → Accepted; Delta-CRDT G1 contract lock (slice ZC-0); this STATUS page | open |

Merge **#509 first** (narrative coherence + so the sibling links in this page
resolve on `main`). The two PRs are otherwise independent (no file conflict).

---

## Gate status per component

Gate ladder: `G0 doctrine → G1 reference-locked → G2 prototype-selector →
G3 parity → G4 determinism → G5 mechanical-advantage → G6 ops → G7 supported →
G8 default-by-ADR`.

### Delta-CRDT substrate (ADR-0180) — highest priority

| Slice | What | Gate | Status |
|---|---|---|---|
| ZC-0 | Contract pinning: Python reference + golden fixtures + Rust↔Python byte parity | **G1** | ✅ done (#511) |
| ZC-1 | Inert Zig skeleton `core-zig/` (builds + local tests, no runtime wiring) | G2 | ⬜ **needs a new ADR to clear G2 first** |
| ZC-2 | C ABI self-test (create/free/push/snapshot/join/merge/hash, no Python) | — | ⬜ |
| ZC-3 | Python binding behind `CORE_CRDT_BACKEND=zig` (no auto-selection) | — | ⬜ |
| ZC-4 | Parity fixtures: Zig == reference (**reuses the corpus locked in ZC-0**) | G3 | ⬜ |
| ZC-5 | Benchmark + memory profile (must win a *named* mechanical criterion) | G5 | ⬜ |
| ZC-6 | Runtime integration proposal | G6→G7 | ⬜ **new ADR** |
| — | Default backend | G8 | ⬜ **separate ADR** |

Step detail: [`crdt-substrate/implementation-slices.md`](crdt-substrate/implementation-slices.md).

### Other components (each starts fresh at its own G0/G1)

| Component | Doc | Current gate | Blocker / note |
|---|---|---|---|
| Audio compiler (ADR-0181) | [`audio-compiler/`](audio-compiler/README.md) | **G0/G1 (blocked)** | Python audio spec not locked — ADR-0183 lexeme fork is a stub. Lock it (audio's own "ZC-0") before any Zig. |
| Runtime FFI contract | [`runtime-ffi/`](runtime-ffi/README.md) | G0 | Doctrine says land the C-ABI/versioning/ownership contract *before* serious Zig in any component. |
| Batch-recall challenge (`vault_recall_batch`) | [`algebra-kernels/`](algebra-kernels/README.md) | G0 | Optional Rust/Zig contest; only after parity tests. `vault_recall_batch` is Python-canonical today (`algebra/backend.py`). |
| Edge-native ingestion runner | [`core-native-system/`](core-native-system/README.md) | G0 | Future; after the above contracts stabilize. |

---

## Immediate next action

**Nothing is authorized to start** — this is the deliberate stopping point.

When the CRDT Zig lane is greenlit, the first step is **an ADR to clear gate G2**
(cite ADR-0196's gate ladder and ADR-0180's locked contract), *then* ZC-1
(inert `core-zig/` skeleton). The ZC-4 parity fixtures already exist:

- Python golden corpus: `tests/fixtures/crdt/merge_fixtures.json`
- Rust expected hex: `core-rs/tests/fixtures/crdt_parity_expected.rs`
- Single source of truth (regenerator): `tests/fixtures/crdt/_generate.py`

A Zig prototype is graded against `canonical_bytes` / `delta_hash` from the
locked reference (below).

---

## The locked reference contract (gate G1)

- **Python canonical reference:** `vault/crdt.py` — `ArenaEntry`, `Delta`,
  `LocalArena`, `merge_kernel`, `canonical_bytes`, `delta_hash`. Pure content
  law (content-addressed by IEEE-754 bits then provenance; no normalization, no
  versor closure, no global Vault writes).
- **Rust incumbent parity:** `Delta::canonical_bytes` in `core-rs/src/vault.rs`,
  pinned byte-identical by `core-rs/tests/test_crdt_hash_parity.rs`.
- **Canonical byte layout** (the cross-language contract; `delta_hash` = its SHA-256):

  ```text
  u64   entry_count
  per entry (content order):
    32 x f32   versor components (IEEE-754, little-endian, 4 bytes each)
    u64        provenance_length
    bytes      provenance
  ```

- **Obligation → test map:** ADR-0180 §5.2.

---

## Environment gotchas (these cost time on 2026-05-31)

1. **Build `core-rs` against Python ≤3.12.** PyO3 0.21 supports max 3.12, but
   fresh `uv` worktree venvs resolve to 3.13 and the homebrew system python is
   3.14 (`cargo` then errors: *"configured Python interpreter version (3.14) is
   newer than PyO3's maximum supported version (3.12)"*). Use:

   ```bash
   PYO3_PYTHON=/opt/homebrew/bin/python3.12 cargo test --test test_crdt_hash_parity --test test_arena -q
   ```

2. **`public_demo` lane SHA miss is environmental, not a regression.**
   `scripts/verify_lane_shas.py` reports `lanes: 7/8` with `✗ public_demo` →
   `DemoContractError: showcase exceeded ADR-0099 runtime budget (~46–48s >
   30000 ms)`. This is a **wall-clock** overrun in `core/demos/showcase.py`,
   **reproduced identically on clean `main`**. For substrate-only PRs (no
   lane-affecting serving code), confirm the 7 content lanes match and the only
   miss is `public_demo`'s timeout. Do **not** re-pin or chase it.

---

## How to verify current state

```bash
# Python contract (default backend)
uv run python -m pytest tests/test_crdt_semilattice_contract.py \
  tests/test_crdt_content_ordering.py \
  tests/test_crdt_no_global_write_from_arena.py -q          # expect 21 passed

# Rust ↔ Python byte parity (needs Py3.12)
cd core-rs && PYO3_PYTHON=/opt/homebrew/bin/python3.12 \
  cargo test --test test_crdt_hash_parity --test test_arena -q   # expect 16 passed

# Regenerate the golden fixtures (Python is the single source of truth)
uv run python tests/fixtures/crdt/_generate.py
```

---

## Authoritative docs

- **Doctrine & ratification:** ADR-0196 (`docs/decisions/`), [`README.md`](README.md)
- **Gates:** [`adoption-gates.md`](adoption-gates.md)
- **CRDT slices:** [`crdt-substrate/`](crdt-substrate/README.md) + [`implementation-slices.md`](crdt-substrate/implementation-slices.md)
- **Component contract status / what locked G1:** ADR-0180 §5
