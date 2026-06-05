# Shape B+ Persistence — Scope

**Date:** 2026-06-05 · **Status:** SCOPE (await go-ahead before code) · **Parent:** [[milestone-l10-continuity-spike]] (the acceptance oracle) · **Telos:** [project-core-is-one-continuous-life] — this is the **T-resume** half (make a reboot transparent), not the always-on process.

## Goal (one sentence)

Make the lived session state — field, vault, anchor, graph, referents, dialogue blade — **durable across reboot, bit-exactly**, so that resuming from a checkpoint continues the *same* life instead of starting a fresh one sharing only recognizers/candidates.

## The acceptance oracle is already built

The L10 continuity spike (`evals/l10_continuity/`, #567) gives us a precise,
falsifiable target — we do **not** invent acceptance criteria:

- **The flip:** today `evaluate_p2b_reboot_transparency(...).post_reboot_transparent == False`
  and `test_p2b_documents_current_resume_gap` pins that. Shape B+ makes it **True**.
  The build is done when that test flips and we invert its assertion to assert
  transparency (P2b becomes a green guard: a reboot is byte-identical to no-reboot).
- **The guards that must stay green prove the round-trip is honest:**
  - **P1 closure** — `versor_condition < 1e-6` must survive serialize→deserialize
    (the #1 risk: float round-trip must be bit-exact or closure breaks).
  - **P2a determinism** — restored state must yield identical `trace_hash`.
  - **P4 crash recovery** — recovery from a session-state checkpoint stays
    deterministic + atomic (ADR-0156).
  - **P5b/P5c** — anchor/coherence behavior unchanged across reboot.
- **The TDD loop writes itself:** restore SessionContext fields until P2b is
  transparent. If a field is load-bearing and we miss it, P2b stays False and
  tells us exactly that. The spike *drives* the scope.

## Lived state to persist (verified inventory)

`ChatRuntime._context` is a `SessionContext` assigned once and never restored
(`chat/runtime.py:608`). Everything it holds is **pure data** (no locks / files
/ RNG / threads — verified), so the whole object is serializable:

| Component | Fields | Serialization note |
|---|---|---|
| `state: FieldState` | `F` (32-vec), `node`, `step`, `holonomy` (opt array), `energy` (EnergyProfile), `valence` (ValenceBundle) | arrays **bit-exact**; energy/valence are frozen dataclasses of primitives |
| `vault: VaultStore` | `_versors` (deque of arrays), `_metadata` (deque of dicts), `_store_count`, `_reproject_interval`, `_max_entries` | the **bulk**; `_exact_index` + `_matrix_cache` are DERIVED → rebuild on load, do not persist |
| `_anchor_field` | 32-vec array | bit-exact; load-bearing for `_session_anchor_pull` |
| `graph: SessionGraph` | `_nodes: list[TurnNode]` (turn_idx, input/output versors, tokens, role, slots, edges) | per-node arrays bit-exact |
| `referents: ReferentRegistry` | `_slots`, `_history` (ReferentEntry: surface/versor/turn/slot), `_last_resolved_*` | per-entry versor bit-exact |
| `running_dialogue_blade` | array \| None | bit-exact |
| scalars/caches | `turn`, `_last_input_tokens`, `_last_resolved_input_tokens`, `_last_input_versor`, `_last_response_tokens`, `_dialogue_history_compat` | restore for safety; P2b reveals which are load-bearing |

## Architecture

- **Per-component `to_dict`/`from_dict`** mirroring the existing Shape-B
  convention (`DerivedRecognizer.to_json`, `DiscoveryCandidate.as_dict/from_dict`):
  `FieldState`, `VaultStore`, `SessionGraph`, `ReferentRegistry` (+ the small
  nested types). Compose into `SessionContext.snapshot() -> dict` /
  `SessionContext.restore(dict)`.
- **Exact array codec** — arrays serialize as `{dtype, shape, b64(raw bytes)}`
  (NOT decimal JSON — decimal truncates and breaks both closure and determinism;
  this is the Cl(4,1) float-truncation pitfall). Preserve `float32` vs `float64`
  exactly.
- **Storage** — extend `engine_state/` with a `session_state.json` written via
  the existing `_atomic_write_text` (ADR-0156), and bump `_SCHEMA_VERSION` 1→2.
  The #563 migration discipline already makes this backward-compatible: a v1
  checkpoint (no `session_state`) loads gracefully into a fresh session — i.e.
  exactly today's behavior — so old checkpoints don't break.
- **Wiring** — `ChatRuntime.checkpoint_engine_state()` saves the snapshot;
  `_load_engine_state()` restores it into `self._context`.

## Phases (entry → exit gates)

| Phase | Build | Exit gate (CLI/test) |
|---|---|---|
| **A. Exact array codec + FieldState** | `b64(dtype,shape,bytes)` codec; `FieldState.to_dict/from_dict` | bit-exact round-trip test + **closure preserved** (`versor_condition` identical post-restore) |
| **B. VaultStore (de)serialize** | snapshot versors+metadata+store_count; rebuild index/cache on load; **NO reproject/normalize on load** | round-trip test: `recall(q)` returns **identical** results post-restore (exact CGA recall preserved); bright-line review that load calls no normalization |
| **C. Graph + referents + anchor + blade → SessionContext.snapshot/restore** | compose all per-component codecs | `SessionContext` snapshot→restore round-trip is object-equal |
| **D. Wire into engine_state (schema v2) + ChatRuntime** | save in checkpoint, restore in load; v1 back-compat | a v1 checkpoint still loads (fresh session); a v2 checkpoint restores the context |
| **E. Flip the oracle** | invert `test_p2b_documents_current_resume_gap` to assert transparency | **P2b transparent** + P1/P2a/P4/P5 still green + the spike `deterministic_digest` stable; `python -m evals.l10_continuity` all gates pass incl. reboot transparency |

## Risks (surfaced up front)

1. **Bit-exact float round-trip (closure + determinism).** The whole flip
   depends on it. De-risk in Phase A with a base64 raw-bytes codec; never decimal.
2. **`vault/store.py` is a CLAUDE.md forbidden normalization site.** Adding
   pure (de)serialization is allowed, but the **load path must not reproject,
   re-normalize, or repair** — it restores raw persisted versors and rebuilds
   only the derived index/cache. Needs an explicit bright-line review and ideally
   an architectural-invariant assertion that `from_dict` invokes no normalizer.
3. **Reproject interaction.** `reproject()` rewrites all versors every N stores,
   so the vault content changes at reproject boundaries. A full snapshot captures
   post-reproject state correctly; an append-only log would diverge. Start with
   **full snapshot** (correct); optimize to incremental only if Phase E / P3 shows
   the I/O cost matters.
4. **Persistence cost vs P3.** Full-snapshot each turn is O(n) I/O → O(n²) over a
   session. Measure with the spike's P3 + a longer soak; if it breaches, move to
   snapshot-at-reproject + append-between. Correctness first.
5. **`trace_hash` depends on `vault_hits` + recall surface.** This is *why* the
   flip works (restored vault → identical recall → identical hash) and *why* the
   round-trip must be exact. Phase B's exact-recall test de-risks it.
6. **Teaching-safety boundary.** This persists **session memory** (immediate per
   CLAUDE.md), NOT reviewed/ratified memory — it is continuity, not a learning
   path. Do not let it become a parallel correction/teaching channel.

## Scope boundary (what this is NOT)

- **NOT** the always-on process / idle-tick runtime (the *other* L10 half) — this
  is resume-transparency only.
- **NOT** cross-reboot **identity-lineage** work (EngineIdentity / lineage chain)
  — that builds *on top of* a transparent resume.
- **NOT** persisting reviewed/ratified memory (already the teaching path).

## Proposed PR shape

One stacked sequence, each PR green on its own exit gate: **A** (codec+FieldState)
→ **B** (vault) → **C** (context compose) → **D** (engine_state wiring) → **E**
(flip the oracle). A–C are additive + unit-tested in isolation (fast); D wires;
E is the soak-lane flip. E is the load-bearing PR — it's the one that proves
resume-as-same-life.
