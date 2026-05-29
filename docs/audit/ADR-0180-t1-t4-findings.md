# ADR-0180 §1.5.4 — T-1…T-4 Foundation: Findings

**Date:** 2026-05-29
**Branch:** `adr-0180-crdt-t1-t4-foundation`
**Tests:** `tests/test_adr_0180_crdt_foundation.py`
**Scope:** the Python-side pre-refactor obligations that must be green on `main`
before any `core-rs/src/vault.rs` change (CLAUDE.md work-sequencing item 5; ADR-0180 §1.5.4).
Also the foundation ADR-0181 PR-5 (audio Delta-CRDT wiring) rides on.

## Status

All four obligations are now covered and green (7 tests, all passing). Below
are the substantive findings discovered while grounding them against the
actual substrate, not the abstract baseline ADR-0180 §1.5 assumed.

## Finding 1 (load-bearing) — `compute_trace_hash` does not fold vault contents

ADR-0180 §1.5.3 point 2 worried that "the trace-hash reduction must consume
vault state in a content-addressed order … not in wall-clock arrival order"
and that §4.3 "cannot hold under [a time-driven flush] policy unless the
*hashing* step re-sorts."

**Actual code** (`core/cognition/trace.py:27`): `compute_trace_hash` folds
`vault_hits` — an **int count** — plus a serialized prefix of upstream turn
fields. It does **not** fold vault *contents* at all.

**Consequence:** the §1.5.3 "re-sort vault state in content-addressed order"
obligation is currently **vacuous at the trace-hash layer** — there is nothing
order-sensitive about vault contents in the payload to re-sort, because contents
are not in the payload. The CRDT merge may reorder the vault deque freely and
`compute_trace_hash` is unaffected, *provided* the recalled result *count*
(`vault_hits`) is order-invariant.

This shifts where the real obligation lives:

- It is **not** at `compute_trace_hash` today (T-2a confirms count-stability).
- It **is** at `recall()` — the count and content of recall results must be
  order-invariant under a reordered deque. T-2b (`recall_result_set_invariant
  _to_insertion_order`) pins this for distinct-score entries and is the
  genuinely-failable half of T-2.

The §1.5.3 re-sort obligation becomes live only if/when vault contents (not just
a count) enter the trace-hash payload. **Recommendation:** ADR-0180 §1.5.3
should be amended to say the content-addressed-sort requirement applies to the
*recall result set* and to any *future* contents-bearing hash, not to today's
count-based `compute_trace_hash`.

## Finding 2 (edge) — equal-score recall ties are index-sensitive

`vault_recall` breaks score ties by ascending index (`vault/store.py`). Index
is assigned by storage order, so two entries with *exactly equal* CGA inner
scores can surface in an order that depends on insertion order. For distinct
scores (the common case, and what T-2b asserts) recall is order-invariant.

**Consequence for the CRDT merge:** the merge must content-address tie-scored
entries (e.g. sort by versor bytes) before assigning deque indices, or the
sub-50ms reorder window (ADR-0180 §3.2) could change which of two equal-score
entries a recall returns. This is exactly the role ADR-0181 §2.2's
`(canonical, ir, projection)` merge key plays for audio — it gives a total,
content-addressed order independent of arrival. **Recommendation:** ADR-0180's
Merge Kernel spec (§2.2) should adopt a content-addressed tiebreak for the
general path, mirroring ADR-0181 §2.2.

## Finding 3 (confirmed) — append is genuinely semilattice-eligible

T-1 confirms `VaultStore.store` is set-equal under any write permutation
(append never dedups/drops/order-mutates), and re-ingest is set-stable at the
content-addressed layer. This validates ADR-0180 §1.5.2 row 5 ("vault/store
write … commutative, associative, idempotent — semilattice-eligible") against
the real implementation. Note the deque itself appends duplicates (length
grows on re-ingest); idempotence holds at the content-addressed layer the CRDT
merge dedups on, not at the raw deque.

## Finding 4 (confirmed) — `versor_apply` is non-commutative; barrier is justified

T-3 confirms the sandwich `V·F·rev(V)` does not commute. This is the load
under ADR-0181 §2.1: in-chunk audio composition is a serialization barrier
*because* this product is order-sensitive, and only the order-invariant
`AudioCompilationUnit` crosses into the sharded merge layer. If a refactor ever
makes `versor_apply` commutative, T-3 fails loudly before the substrate can
wrongly shard it.

## Net

- T-1, T-3, T-4 hold against the real code as ADR-0180 §1.5.4 assumed.
- T-2 holds, but the obligation moved: the order-invariance that matters today
  lives at `recall()` (result-set + count), not at `compute_trace_hash` (which
  is count-only). Two small amendments to ADR-0180 §1.5.3 and §2.2 are
  recommended above. Neither blocks the substrate; both sharpen it.
