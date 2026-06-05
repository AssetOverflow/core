# L10 Continuity Spike — Design

**Date:** 2026-06-05 · **Status:** SPIKE DESIGN (a falsifiable experiment spec; not yet built) · **Parent:** [L10 Runtime Scoping Brief](./L10-runtime-scoping-2026-06-05.md) (critical-path step 3) · **Gated by:** Decision 0 (RULED — closure holds by construction) + step 1 (byte-stability tests, committed `3911db66`) + step 2 (schema-migration discipline — see Dependencies).

> The master plan calls the L10 long-horizon spike "the single point of failure." Decision 0 already answered its *original* core question — **closure holds by construction** (100k-step measurement, `versor_condition` ~6e-13, flat). So this spike's job has **shifted**: from *"does the field stay a valid versor?"* (answered) to *"does the field stay a meaningful, bounded, recoverable, deterministic life over a long horizon?"* — the **sufficient** legs Decision 0 explicitly deferred here.

---

## What the spike proves (and what it can't)

It is the empirical gate between the two L10 targets:
- **T-resume** (provable same-life *resume*): determinism + recovery. Predicates P1–P4.
- **T-experience** (a continuous *experiencing* field-life): the field's *content* stays meaningful over indefinite uptime. Predicate **P5** — the one that decides whether continuous-field-life is real or whether we fall back to the honest recognizer-only-continuity servant.

It is **not** a proof of correctness of any single turn (that's the cognition lane), nor a wall-clock endurance certificate (see Compression). It is a **falsifiable soak**: every predicate must be able to **fail loudly**, and the spike itself must be **mutation-verified to bite** before any PASS is trusted (CLAUDE.md schema-as-proof discipline).

---

## The five predicates (pass/fail, each must fail loudly)

| # | Predicate | Assertion | Fails loudly when | Mutation-verify (the spike bites) |
|---|---|---|---|---|
| **P1** | Closure regression guard | `versor_condition(F) < 1e-6` every turn over N turns | a future change breaks construction-correctness or sneaks in a repair | break a rotor construction → P1 trips |
| **P2** | Reboot-transparent determinism | `trace_hash` sequence of [boot → run K → **reboot(reload)** → run M] is byte-identical to [boot → run K+M] (no reboot) | any state/byte leaks across reboot, or replay is nondeterministic | drop a field from the checkpoint → P2 trips (this is step-1's byte-stability, escalated to the turn loop) |
| **P3** | Bounded resources | over N turns: process RSS sub-linear to a declared ceiling; live `VaultStore` growth bounded/as-designed; no fd/handle leak | a ceiling is breached (unbounded recall scan, cache, memory) | inject an unbounded cache → P3 trips |
| **P4** | Kill-9 convergence | a hard kill at an arbitrary point (incl. **mid-checkpoint-write**) always next-boots onto a **valid prior checkpoint** (ADR-0156 atomicity) and resumes deterministically (P2 from the recovered point) | corruption / partial state / non-resumable boot | corrupt the atomic-replace (write-in-place) → P4 trips |
| **P5** | Semantic-quality over horizon | the field's **content** stays meaningful as the session grows (3 sub-assertions below) | the field rots, collapses, or wanders | force anchor collapse / inject recall decay → P5 trips |

**P5 sub-assertions (the T-experience gate):**
- **P5a — recall stays sharp.** On a held-out probe set, recall precision@k does **not** degrade as the session grows (no "memory rot" as the vault fills). Uses exact CGA recall (no approximation).
- **P5b — no anchor collapse.** `cga_inner(F, session_anchor)` does **not** monotonically → 1. The (now-sanctioned) semantic anchoring must *anchor*, not *dominate*: the field must still move with content, not collapse onto the attractor over many turns. *(This is the direct long-horizon test of the `_session_anchor_pull` ruling — α=0.05 must be gentle enough.)*
- **P5c — no incoherent wander.** Surface groundedness / key-term stability stays above a pinned threshold; the field doesn't drift into noise.

> **Why P5 is the crux:** P1 proves *valid-versor-forever*; P5 proves *meaningful-content-forever*. Decision 0 cleared the doctrinal blocker for continuous-field-life; **P5 is the empirical one.** A PASS on P1–P4 with a FAIL on P5 means we have provable *resume* but not continuous *experience* — the honest fallback (recognizer-only continuity, ephemeral field) the telos rejects but the evidence might force.

---

## What it runs

1. **Deterministic scripted corpus.** A seeded, replayable input sequence driving the *real* turn loop (`SessionContext.respond` → `finalize_turn`, the actual cognition pipeline), over N turns. N scales by lane: `smoke` ≈ 1k, `full` ≈ 50k+. No randomness except seeded fuzz (Decision: reuse `calibration/replay.py` determinism harness; corpus is a committed fixture).
2. **Reboot legs.** At intervals: checkpoint (existing per-turn path) → construct a fresh runtime from the checkpoint → continue. P2 asserts transparency.
3. **Kill-9 legs.** (a) *Seeded* kill points at chosen turn/checkpoint boundaries; (b) a lighter *random real-time* kill fuzz (see Compression). Each followed by a recovery boot + P2/P4 assertions.
4. **Instrumentation.** Per-turn `versor_condition`, `trace_hash`, RSS, vault size, recall-probe precision, `cga_inner(F, anchor)`, key-term stability → a structured JSONL report; per-predicate PASS/FAIL; **no silent skips** (a skipped leg is recorded as `not_covered`).

Reuses: `core/cognition/trace.py` (trace hash), `calibration/replay.py` (replay), `engine_state/` (checkpoint), and the step-1 byte-stability tests as the unit-level floor under P2.

---

## Compression vs. wall-clock (honest coverage limits)

- **Primary lane = compressed N-turn soak.** Turn-count — not wall-clock — is the real variable for determinism (P2), resources (P3), and semantics (P5). "24h" is a proxy for "many turns + bounded resources"; a compressed soak is the falsifiable core.
- **Secondary lane = real-time fuzz.** Some failure modes are genuinely time/entropy-shaped and a turn-count soak cannot enumerate them: **true power-loss-at-an-arbitrary-instruction** (vs. scripted kill points), fd/timer leaks, idle-tick behavior. A lighter real-time random-kill + long-idle probe covers these.
- **Stated limit (no-silent-caps):** even the real-time fuzz is **sampling**, not exhaustive — it cannot enumerate every mid-instruction crash boundary. The report logs the coverage bound explicitly; a PASS means "no failure found in the sampled boundaries," not "proven crash-safe at every instruction." (ADR-0156 atomic-replace is the *construction* argument that backs the sampled evidence.)

---

## Operator-reality lens ([[user-circumstances]])

The operator is unhoused with intermittent power → **ungraceful kill-mid-turn is the common lifecycle event, not the edge.** This **elevates P4 (kill-9 convergence) to the primary design driver** — above graceful-shutdown machinery. The spike must treat "power dies at an arbitrary instruction" as the default transition and prove convergence to a valid checkpoint, not assume clean exits.

---

## Entry gates

- **Decision 0 ruled** ✓ — closure cleared; the spike targets P2/P3/P4/P5, not "does closure survive."
- **Step 1 byte-stability tests** committed (`3911db66`) ✓ — P2 escalates them to the turn loop.
- **Step 2 (schema-migration discipline) DECIDED** — *prerequisite.* P2's byte-identity assertions assume a **fixed schema within a run**; a mid-horizon `DerivedRecognizer`/`DiscoveryCandidate` field-add would make P2 falsely fail. The spike must pin `schema_version`, and the migration story (versioned upgrade vs clear-slate) must exist before P2 is load-bearing. **Do not build the spike before step 2 is decided.**
- A committed deterministic input corpus.

## Exit gates / outcomes

- **PASS (P1–P5 over the horizon + kill-9 legs)** → licenses: flipping the default-OFF flags ON under traffic (ADR-0148/0149/0154); the **Shape B+** warm-process / field-residency decision; lineage-chain identity work.
- **FAIL P1/P2/P3/P4** → fix the *construction* (no watchdog/repair allowed — CLAUDE.md) or REFUSE the regime; do not paper over.
- **FAIL P5** → continuous-field-life (**T-experience**) is not yet achievable → honest fallback to **T-resume only** (recognizer-only continuity, ephemeral field — the sanctioned servant outcome) until the **learned-field / contemplation** track solves content-stability. This is a *fail-forward*: it's a real, negative, useful result.

---

## Where it lives

- New eval lane `evals/l10_continuity/` + a runner; CLI `core eval l10-continuity` (or a pytest marker). **Not** in the default smoke suite (it's a soak) — on-demand + CI nightly.
- Structured JSONL report (per-predicate metrics + PASS/FAIL + coverage bounds). The lane is **frozen-gated** like the other serving lanes (pinned SHA / CLAIMS-style) once it passes, so a regression is caught.

## Build order (when authorized)

1. Decide step 2 (schema-migration discipline) — unblocks P2.
2. Build the deterministic corpus + the soak runner (P1, P2, P3 first — cheapest, reuse replay harness).
3. Add the reboot + kill-9 legs (P4) — including the real-time fuzz with logged coverage bound.
4. Add P5 (recall-probe + anchor-collapse + coherence metrics) — the T-experience gate.
5. Mutation-verify every predicate bites; then freeze-gate the lane.
