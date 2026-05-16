# ADR-0020 — Phase 5 / Rust Parity Sequencing

**Status:** Accepted (2026-05-16)
**Date:** 2026-05-16
**Authors:** Joshua Shay
**Depends on:** ADR-0016 (Capability Roadmap), ADR-0019 (Exact
Vault Recall Acceleration), `docs/PROGRESS.md` Phase 4 exit
memo.

## Context

Phase 4 exited 2026-05-16 with three lanes shipped
(sample_efficiency, long_context_cost, multi_agent_composition)
and ADR-0019 Stage 1 vectorising vault recall.  Two non-trivial
axes are now unblocked:

- **Phase 5 — Curriculum Era.**  Open-ended domain acquisition
  (English fluency v5 OOD, Hebrew, Koine Greek, elementary
  mathematics, foundational physics/biology, classical
  literature).  Stresses the runtime *as it stands today* on
  semantic breadth and pack scale.
- **Rust backend parity port.**  CLAUDE.md sequencing rule 5:
  *"Add Rust backend parity only after Python semantics are
  locked by tests."*  Phase 4 just locked vault recall semantics
  with bit-identity tests; the prior Phase 1–3 work locked
  algebra closure, intent classification, articulation, teaching,
  and trace hashing.  The blocker is dissolved.

The question is **what order to take these on**.  Three
positions are credible:

### Option A — Phase 5 first, Rust parity later

Open Phase 5 now.  Drive curriculum work on the Python runtime.
Defer Rust until Phase 5 surfaces a concrete bottleneck that
indexing/vectorisation cannot dissolve.

- **Pro:** Maximum focus on capability expansion.  Phase 5 is
  where CORE proves its end-goal claim (listen → comprehend →
  recall → think → articulate → learn → replay) on real domains.
  Every additional language / domain pack is a load-bearing
  capability bet.
- **Pro:** Python is currently fast enough.  Stage 1 vault
  recall is ~20 ms at N=10⁵.  No measured Python bottleneck
  blocks Phase 5 work today.
- **Con:** Phase 5 will balloon the test surface.  Re-running
  Phase 1–4 lanes on every release (per the roadmap) will get
  slow.  CI feedback latency directly governs willingness to
  refactor — a slow loop encourages unsafe shortcuts that
  CLAUDE.md explicitly warns against.
- **Con:** Each new pack ships with Python-only semantics.
  When Rust parity lands later, every pack's behaviour will
  need re-verification against the Rust path — more locked
  surface to re-lock.

### Option B — Rust parity first, then Phase 5

Port the Python backend surfaces to Rust before opening Phase 5.
Lock parity with bit-identity tests at every ported surface.

- **Pro:** Phase 5 then starts on a faster substrate.  Every
  curriculum eval re-run is cheaper.  Faster feedback supports
  the eval-driven discipline the project rests on.
- **Pro:** Locks parity at the smallest possible surface area.
  Today the locked Python surface is finite and bounded; after
  Phase 5 it will have grown by every pack, every curriculum,
  every new operator.  Porting later means porting more.
- **Con:** Rust port is itself a non-trivial project.  Done
  poorly it introduces a parallel backend whose drift from
  Python is a constant source of incident.  CLAUDE.md already
  treats Rust as opt-in for a reason — `CORE_BACKEND=rust`
  must remain explicit and the Python path must remain the
  deterministic default.
- **Con:** Delays the capability story.  No new curricula
  ship until parity is done.

### Option C — Parallel: Phase 5 curriculum + Rust parity in independent tracks

Open Phase 5 on the Python runtime.  In parallel, port one
backend surface at a time to Rust, gated by bit-identity tests,
without making Rust the default.  Phase 5 curricula run on
Python until Rust parity is proven per-surface.

- **Pro:** Both axes progress.  Phase 5 capability bets land
  on schedule.  Rust parity grows incrementally, surface by
  surface.
- **Pro:** Bit-identity gating means a Rust regression cannot
  silently corrupt Python-validated runtime behaviour.  The
  Rust path is purely an acceleration; the Python path remains
  the source of truth.
- **Con:** Two contexts to hold.  Demands discipline about
  which surface is being touched at any given time.
- **Con:** Mid-Phase-5 backend swap (per-surface enablement of
  Rust path) is a real operational complexity that needs
  careful tooling to keep replay determinism intact.

## Recommendation

**Option C — parallel, with explicit ordering.**

Concretely:

1. **Open Phase 5.1 (English fluency v5 OOD) immediately.**
   This is the natural successor to Phase 3 v2 grammatical-
   coverage and to ADR-0018's articulation operators.  It does
   not depend on Rust.
2. **In parallel, open a Rust-parity track.**  First port:
   `vault_recall` — the surface ADR-0019 Stage 1 just locked
   with bit-identity tests.  Port is gated on byte-equal scores
   and identical top-k ordering against the Python path on a
   wide fixture vault.  No Rust enablement on `main` until the
   bit-identity test passes under `CORE_BACKEND=rust`.
3. **Second port:** `geometric_product` and `versor_apply`.
   These are the hottest algebra paths; bit-identity is testable
   against the existing Python closure.  Locked by Phase 1–3
   algebra suite.
4. **Third port:** `cga_inner` (drop-in replacement now that
   the diagonal-metric kernel is the source of truth).
5. **Defer:** propagation, teaching, trace hashing — these are
   Python-shaped semantics with relatively low computational
   weight; port only if Phase 5 evidence demands it.

Phase 5 may also unlock the deferred scope decisions in
PROGRESS.md ("Code generation" before Phase 5, "Embodiment"
during Phase 5).  Those are separate ADRs; this one only
governs sequencing.

## Decision

**Option C — parallel, with explicit ordering.**  Confirmed
2026-05-16.

## Consequences

- `docs/PROGRESS.md` opens Phase 5 with "Status: IN PROGRESS"
  on the same date this ADR is accepted.
- A new ADR (numbered after this one) opens to document the
  Rust parity contract per-surface (test discipline, parity
  gate, default-off enablement, replay determinism preservation).
- The Rust track produces no new runtime behaviour — only
  faster execution of behaviour that the Python path already
  validates.  Any divergence is a test failure, not a feature
  request.

## What this ADR does NOT decide

- Which Phase 5 curriculum to open *second* (Hebrew vs.
  mathematics vs. physics).  Separate scope call once 5.1 ships.
- The Rust crate layout / dependency choice.  That belongs in
  the per-surface Rust parity ADR, not here.
- Whether to invest in a third backend (e.g., GPU / JAX).  Out
  of scope until both Python and Rust paths are mature.
