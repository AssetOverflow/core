# Backlog: everyday-atoms grounding pack (idea, not yet scoped)

**Source:** closed PR #449 (`atomic_definitions_everyday_v1`), opened off-brief by
the remote connector during the 2026-05-29 ADR-0179 work. Closed as not-mergeable
(inert, structurally duplicated, unvalidated, disconnected from the active arc),
but the *idea* is worth keeping.

## The idea

A compact, curated pack of everyday-object atoms — the concrete nouns GSM8K word
problems actually lean on (apples, baskets, boxes, strawberries, coins, …). This
is on-thesis: it gives the engine "more pieces to the puzzle" so it can comprehend
the entities a problem talks about, rather than only counting their numbers. It is
*finding/comprehending better*, not *storing another found answer*.

## Why #449 as shipped delivered no benefit

- **Inert** — nothing in `chat/`, `generate/`, `language_packs/`, or `core/`
  referenced it; `default = false`, `status = "draft"`. No runtime effect.
- **Duplicated + mislocated** — shipped the same 9 files twice
  (`packs/everyday/` *and* `packs/everyday/atomic_definitions_everyday_v1/`),
  neither matching the flat `packs/<pack_id>/` convention (cf. `packs/en/`).
- **Unvalidated** — never run through the pack gate (`core pack validate`); all
  gates `false`; manifest checksums unverified (must hash the bytes on disk).
- **Disconnected** — the math derivation/reader lane does not consume semantic
  packs, so even if loaded it would do nothing for GSM8K today.

## What would make it beneficial (the real scope when it's time)

1. **One flat, conventional location**: `packs/atomic_definitions_everyday_v1/`.
2. **Passes the pack gate**: probes green, checksums hashing the written bytes,
   `validate_pack_dir`/`lift_from_pack` delegation reviewed at the dynamic-validator
   trust boundary.
3. **A consuming grounding path**: an ADR that wires everyday-atom grounding into a
   comprehension/reader lane that actually reads it (otherwise it's a parked
   artifact). Likely adjacent to the ADR-0178 comprehension-guided composer, not to
   ADR-0179 extraction.
4. **Curated, not bulk** — keep it compact (CLAUDE.md: no corpus bulk-ingest into
   runtime); grow it deterministically with pack tests.

Until 1–3 exist, this is an idea, not a pack.
