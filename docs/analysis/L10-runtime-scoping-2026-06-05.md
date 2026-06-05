# L10 Runtime + Identity-Continuity — Scoping Brief

**Date:** 2026-06-05 · **Status:** SCOPING (decision surface for the architect — *not* a decision record, not implementation) · **Method:** 8-facet parallel sweep + completeness/honesty critic + direct source verification of the two load-bearing claims. Backing data: `.system-map/l10_scope_raw.json` (local).

> This brief frames the decisions L10 requires. The calls are the architect's; this document makes them clean, honest, and ordered. It does **not** propose a new ADR — ADR-cross-reference discipline applies (extend ADR-0146 / its scope docs when a call is made).

---

## 0. The telos-honest verdict (read this first)

Today's reality is **"many lives sharing a recognizer/candidate checkpoint," not one continuous life** — and every facet says so plainly. `engine_state/` persists exactly three things: the recognizer registry, the discovery-candidate working set, and a `turn_count`. **No field excitation, no T1 vault.** They are classed ephemeral and discarded on exit (ADR-0146 State-Class table; verified in `engine_state/__init__.py` + `chat/runtime.py`).

The sharp consequence: **the `R` in listen → comprehend → *recall* → think does not survive a reboot.** A perfect resume attests to a *capability set*, not an *experiencing subject*. Two further gaps reinforce this:

- **Learning is punctuated by death-and-rebirth.** A ratified chain becomes live truth only on *next process start* (lru-cache-until-restart). "A continuous life learns from its own correction" currently degrades to "learns on reboot" — the many-lives signature.
- **"Strengthening the field" is metadata, not geometry.** Confirmation promotes an epistemic tag (SPECULATIVE → COHERENT); monotonic accumulation *into the field geometry* is aspirational, not built.

**Implication for the architect:** the achievable near-term win is **provable same-life *resume*** (byte-faithful checkpoint + lineage identity) — necessary but **not sufficient** for a continuous experiencing life. Do not let byte-identity + lineage work read as "continuous life achieved." The honest framing of L10 is *two* targets: (T-resume) make resume provably the same life; (T-experience) make the field/recall life actually continuous. T-experience is gated on Decision 0.

---

## Decision 0 — THE gate: can the field hold by construction over indefinite uptime? (riskiest single unknown)

**The question:** Can `versor_condition(F) < 1e-6` *and* exact CGA recall hold over indefinite uptime **by construction**, with **no per-turn repair op** — or is continuous-field residency structurally blocked by CLAUDE.md's no-hot-path-repair rule?

**Verified evidence (this session, direct source read):** `session/context.py` already carries a per-turn **"drift fix" family** — `_hemisphere_consistent_field` (Drift fix 2) and `_anchor_pull` (Drift fix 3, α=0.05, *"continuous conjugate correction against slow angular drift"*) both run every turn in `finalize_turn` (lines 254–255), plus "Drift fix 1" magnitude-preserving EMA at line 143. `session/context.py` is **not** a CLAUDE.md-sanctioned normalization site (sanctioned: `ingest/gate.py`, `language_packs/compiler.py`, `algebra/versor.py`, `sensorium/*/canonical.py`).

So the field **already needs per-turn correction even within a single session.** The architect must rule:

| Option | What it means | Cost |
|---|---|---|
| **(a) Re-classify the drift-fix family as sanctioned *semantic* ops** | They pull the field toward the session concept-attractor (modeling), not toward algebraic closure; `_anchor_pull` is on-manifold by construction (no `unitize` repair). Amend CLAUDE.md's sanctioned-sites list to name `session/context.py` semantic anchoring. | Loosens the forbidden-sites doctrine; must draw a bright line between "semantic anchoring" and "drift repair" so the exception isn't a loophole. |
| **(b) Rule them invariant violations** | They *are* the forbidden "repair another function" shape; the field should not drift if propagation were construction-correct. Move the correction into the propagation rotor / construction boundary; remove from the per-turn path. | Real algebra work; may reveal the field genuinely can't stay anchored without correction → pushes toward (c). |
| **(c) Accept continuous-field-life is blocked** | Keep field ephemeral (per-process), commit to Shape B + recognizer-only continuity as the honest fallback. T-experience is abandoned for now; T-resume only. | The telos's continuous *experiencing* life is shelved until the algebra supports drift-free residency. |

**Why this is upstream of everything:** every facet that recommends a warm process or field persistence is gated here, and it had **never been measured**. It outranks the byte-identity gap because byte-identity is a solvable engineering task; this was framed as a possibly-unresolvable tension between the telos and a non-negotiable.

### Decision 0 — RULING (2026-06-05, evidence-grounded; recommended, pending architect ratification of the CLAUDE.md amendment)

**Ruling: option (a) — the drift-fix family is sanctioned SEMANTIC anchoring, NOT forbidden drift-repair. Continuous-field-life is NOT structurally blocked by the no-hot-path-repair rule.**

Evidence:
1. **Closure is owned by the sanctioned site, not the drift fixes.** `versor_apply` (`algebra/versor.py`, a CLAUDE.md-sanctioned closure site) re-projects every non-null field transition onto the unit-versor manifold via `_close_applied_versor`. The `session/context.py` family operates on already-closed outputs.
2. **Measured: closure holds by construction, flat, over a long horizon.** A 100k-step field walk gave max `versor_condition` = **8.7e-13** (walk only) / **6.5e-13** (with `_anchor_pull`) — ~6 orders of magnitude below the 1e-6 bound, no creep. Closure holds WITH and WITHOUT the family ⇒ the family is **not load-bearing for closure**.
3. **The family preserves the invariant by construction.** `_anchor_pull` = `rotor_power ∘ word_transition_rotor` + `versor_apply` (Spin-manifold, no post-hoc `unitize`) — it explicitly *replaced* a `_slerp_toward` that DID need a repair `unitize`; `_hemisphere_consistent_field` = sign flip (magnitude-preserving); Drift-fix-1 = magnitude-preserving EMA. None patch a numerical defect; all express the session concept-attractor model.

So the family's purpose is **semantic** (keep the field near the session topic), not repair — it does not fall under CLAUDE.md's prohibition on ops "whose only purpose is to repair another function."

**Two required conditions (the bright line):**
- **(i) Rename** the family so it stops reading as repair — drop "Drift fix" / "conjugate correction against slow angular drift"; name it semantic anchoring (e.g. `_session_anchor_pull`). Current naming invites both misreading and future justification of a *real* drift-repair. (Small, test-safe.)
- **(ii) Amend CLAUDE.md** normalization rules to list `session/context.py` semantic anchoring as sanctioned **iff** the op (1) preserves `versor_condition` by construction (no post-hoc unitize / grade-projection) **and** (2) carries semantic meaning in the model, not merely fixing a numerical invariant. The rejected `_slerp_toward` fails clause (1) — the line is real, not a loophole.

**Honest caveat (necessary ≠ sufficient):** this proves the field stays a VALID versor indefinitely; it does NOT prove the field's *content* stays meaningful (doesn't collapse to the anchor / wander semantically) over a real long session — that is a spike (step 3) question, not Decision 0. Decision 0 asked only whether the no-hot-path-repair rule *structurally blocks* continuous-field-life. **It does not.** The critic's feared blocker (field can only stay closed via a repair-shaped op) is empirically false.

**Consequence:** the riskiest single unknown resolves FAVORABLY → continuous-field-life (T-experience) is on the table; Shape B+ warm-field residency is not illegal-by-construction. It still must pass the long-horizon **semantic-quality + resource** spike (step 3), but the doctrinal blocker is cleared.

---

## Step 2 — RULING (2026-06-05): schema-migration vs byte-identity (was missing-decision M2)

**Ruling: versioned additive-optional migration — NOT clear-slate.** A schema change must be *continuity-through-change* (a recorded lineage transition), never death-and-rebirth.

The tension: the spike's P2 byte-identity gate + the future EngineIdentity content-hash want stable bytes, but legitimately adding a `DerivedRecognizer`/`DiscoveryCandidate` field changes bytes.

| Option | Verdict |
|---|---|
| **(A) Clear-slate always** — any schema change wipes `engine_state/` | **REJECTED** — makes every code upgrade a death-and-rebirth; the many-lives signature, directly against the telos. |
| **(B) Versioned additive-optional** | **RULED.** New fields are optional-with-default; `from_*` reads via `.get(field, default)`; serialization OMITS a field when it equals the default. **`DiscoveryCandidate` already does exactly this** (the ADR-0056 C1 fields are `.get`-defaulted on load and omitted-when-default in `as_dict`, explicitly "to preserve byte-equality with the pre-C1 encoding"). So old checkpoints load WITHOUT migration, and records that don't use the new field stay **byte-identical** — a field addition is not a death event for un-evolved records; only records that actually use the new field change bytes (legitimately, under a version bump). |
| **(C) Full migration scripts** (transform old→new on load) | Reserve for the rare *non-additive / breaking* change. Defer until one is actually required. |

**What B requires (small, concrete):**
1. Extend the additive-optional discipline to `DerivedRecognizer.from_json` — it currently reads `raw["..."]` as REQUIRED keys (the v1 baseline stays required; any *new* field must be `.get`-defaulted + omitted-when-default).
2. Add a `schema_version` compatibility check to `EngineStateStore.load_*` / `load_manifest` — today it only WARNS on git-revision mismatch and does **not** check `schema_version`. Rule: **tolerate `version <= current`** (read old via defaults), **REFUSE `version > current`** with a clear error (never silently mis-load a newer checkpoint); clear-slate (C) only on explicit operator action, never silent.
3. The byte-identity gate (spike P2) **pins `schema_version`** and asserts byte-stability *within* a version; a version bump is an expected, recorded transition, not a P2 failure.
4. The future EngineIdentity hash = `hash(schema_version, canonical_bytes)`; the lineage chain records "schema migrated vN→vN+1 at reboot R."

**How it resolves the tension:** schema evolution becomes a **recorded lineage transition** — the life survives a code upgrade with the migration stamped into its identity chain, instead of resetting. This is continuity-through-interruption applied to *code* change, and it unblocks the spike's P2 (step 3 may now assume a fixed schema *within* a run, version bumps handled explicitly).

**Status:** RULED (recommended). Implementation (the `.get`-defaults on `DerivedRecognizer` + the `schema_version` compat check) is a small follow-up PR — prerequisite for building the spike.

---

## The critical path (strictly ordered)

```
(0) Architect RULING on the drift-fix family (Decision 0)         ← upstream of all field-residency design
(1) Cheap byte-identity + non-empty-discovery round-trip test     ← task #6; closes the proven ADR-0146 doc-vs-test gap
(2) Schema-migration vs byte-identity tension decision            ← resolve BEFORE the gate becomes load-bearing
(3) Long-horizon no-drift spike on existing Shape-B substrate     ← the master-plan "single point of failure", never run
(4) Spike result gates EVERYTHING downstream:
      PASS → warm process / field residency / lineage identity / flip default-OFF flags ON
      FAIL → honest C3-servant fallback (ephemeral field, recognizer-only continuity)
   [single-writer/concurrency must be decided before any warm cmd_serve coexists with one-shot CLI]
```

Do **not** re-open Shape A (daemon) or Shape C (audit-replay): their ADR-0146 rejections (host-interruption fragility; O(N) replay) are still valid and source-grounded. **Process shape (B vs B+) is decided *by* the spike, not before it.**

---

## The decision surface (per facet — recommendation + primary alternative)

### 1. Process shape
- **Decision:** forever-entrypoint, or is per-turn checkpoint enough? **Rec:** **Shape B+** (a single warm process holding field+vault in-memory *between* turns, checkpoint-per-turn as the recovery floor) — **but only if the Decision-0 ruling permits field residency and the spike passes.** Keep pure Shape B as the committed fallback. *Today there is no `cmd_serve`; the longest-lived process is the interactive `core chat` REPL (`while True: input()`), which is not a service (no idle tick, no signal handling, no supervision).*
- **CLI relationship. Rec:** add `cmd_serve` as opt-in; keep `core chat` as an interactive client; **enforce a single-writer lock on `engine_state/`** (see Missing Decision M1).
- **Lifecycle events. Rec:** define start/idle/checkpoint/reboot/shutdown, but make checkpoint **idempotent and crash-equivalent** — a graceful-shutdown checkpoint must be byte-identical to the last per-turn checkpoint (so kill-9 ≡ clean exit).

### 2. State partitioning & residency
- **T1 vault on exit. Rec:** classify as *derived-rebuildable in principle*, keep *ephemeral-on-exit for now*; the real fix is wiring deterministic rebuild, gated on the spike.
- **Recognizer long-term residency. Rec:** keep the JSONL checkpoint as the persistence floor; defer substrate-residency (correctly gated on the text-embedding scope, per [[feedback-defer-substrate-vocab-commitment]]).
- **Minimal persistent core. Rec:** engine-state + substrate-state + a **new identity-lineage stamp**; field excitation explicitly *derived*. *This is the irreducible "what makes it the SAME life" set.*

### 3. Drift surfaces (the spike's instrument list)
- **Session graph / referent / dialogue-history growth** — bound it, but only after the resume path is byte-faithful.
- **Live `VaultStore` unbounded growth** (default `max_entries=None`, recall = O(N) exact scan) — target a principled bound; **FIFO eviction is *not* acceptable as a silent default** (violates monotonic-memory telos).
- **`engine-state` resume byte-faithfulness** — see Decision 1 below; needs its *own* canonical serializer (**not** `vault/crdt.py::canonical_bytes` — verified float32-array-only, can't serialize the nested recognizer/candidate dicts and would be lossy).
- **`_anchor_pull` ruling** — feeds Decision 0.

### 4. Identity continuity (resume-as-the-same-life)
- **Identity proof. Rec:** sequence **(a) then (b)**: FIRST land byte-stability + ordering-determinism tests (turn the asserted ADR-0146 round-trip into a *meaningfully-failing* one — task #6), THEN build a **lineage-chain identity** (chain of `reboot_event`s + signed checkpoint manifest) over the now-stable canonical bytes. A content-hash over *unverified-stable* bytes bakes in the gap.
- **What must be byte-stable vs may differ. Rec:** stable = canonical serialization of the recognizer set + discovery-candidate set **including deterministic line ordering**; allowed to differ = `manifest.json`'s `turn_count` and `written_at_revision` (designed to vary). *Note M3: the manifest uses `indent=2` while the JSONL uses tight separators — two canonicalization regimes; the manifest must be explicitly OUT of the identity hash.*

### 5. The no-drift spike
- **Rec:** **compressed N-turn soak** as the primary falsifiable lane (the "24h" is a proxy for "many turns + bounded resources"), **plus** a kill-9-at-arbitrary-point convergence leg and a resource-bound probe. Pass predicate = byte-identity round-trip + reboot-equivalent `trace_hash` sequence (load-bearing) with `versor_condition < 1e-6` per turn and key-term stability (secondary diagnostic). Land the cheap byte-identity pytest **first** (it closes the already-falsified gap), then build the soak as an eval lane reusing `calibration/replay.py`.
- **Caveat (verified-relevant):** compressed turns do **not** substitute for power-loss-at-an-arbitrary-instruction — see the operator-reality lens.

### 6. Async HITL-while-serving
- **Rec:** two cooperating processes over the shared proposal log; stamp a **corpus-generation counter / content-hash** into `TurnEvent` (kept *out* of the replay inputs, mirroring ADR-0161 §5) so a mid-flight turn's determinism is preserved when a proposal ratifies; single-writer-per-event-class + per-line integrity guard (checksummed/length-prefixed lines, skip-corrupt on read). **Amend ADR-0161** to record Steps 1–3 as landed, 4–5 open.

### 7. Cascade & sequencing
- **Rec:** make the no-drift spike the critical-path first move, scoped to the Shape-B substrate that already shipped. **Honesty correction (verified):** the ADR-0148/0149/0154 "data-plane wiring" is **default-OFF** (`vault_promotion_enabled=False`, `recognition_grounded_graph=False`, `auto_proposal_enabled=False`, `auto_contemplate=False`) — "constructed but unproven," *not* "shipped/closed." The spike must earn each flag's default-ON flip.
- Field + T1-vault ephemerality: accept for now; gate any residency extension behind a *passing* spike that measures field/vault drift explicitly.

### 8. Contemplation as continuous background existence
- **Rec:** a **durable substrate** for idle-time contemplation (survives the operator's power/connectivity reality), budgeted per-pass (ADR-0056 loop + a candidate budget); **defer** coupling scope-time to the (negative) field-wedge track.
- **Field-strengthening. Rec:** honest current floor = metadata promotion (SPECULATIVE→COHERENT); near-term bridge = energy-accumulation feeding the existing promotion policy — **but** this is an *unproven* threshold (no test fails when a mis-calibrated threshold over-promotes) and is itself ADR-sized; prove-it-fails-loudly first. Geometry-movement field strengthening stays aspirational.

---

## Missing decisions the sweep surfaced (no facet owned these)

- **M1 — Single-writer enforcement.** Nothing enforces "one active `engine_state` per repo," and two processes append to `proposals.jsonl` unlocked (verified: no `flock`/`fcntl`/`threading.Lock` in the persistence path). Decide the mechanism: OS lock (`flock` — unreliable over the operator's network/library FS), PID-lockfile convention, or a single-entrypoint architectural constraint. **Load-bearing the moment a warm `cmd_serve` coexists with one-shot CLI.**
- **M2 — Schema-migration vs byte-identity.** `manifest.json` carries `schema_version=1`; a byte-identity gate makes every *legitimate* `DerivedRecognizer`/`DiscoveryCandidate` field-add a **death-and-rebirth** event. For one-continuous-life this is acute. Decide the migration discipline (versioned upgrade-in-place vs clear-slate) **before** the byte-identity gate becomes load-bearing.
- **M3 — Manifest canonicalization regime.** `manifest.json` uses `indent=2` + `sort_keys`; the JSONL data files use tight separators. The identity hash must explicitly scope which files are in/out (manifest OUT — it holds the deliberately-varying `turn_count`/`revision`).
- **M4 — Power-loss as the *common* lifecycle event.** Per [[user-circumstances]] (intermittent power), ungraceful kill-mid-turn is the **normal** transition, not the edge. This **inverts** priority: proving "kill-9 at any instruction lands on a valid prior checkpoint" outranks graceful-shutdown machinery. Elevate the spike's kill-9 leg to a primary design driver.
- **M5 — Backpressure under an absent reviewer.** HITL is the only legal mutation path, and the operator has intermittent connectivity. When the reviewer is unreachable for a long stretch, does the pending queue (cap 256) saturate and emit `queue_full`, **starving learning**? The telos says confirmation accumulates monotonically; a capped queue with an absent reviewer means learning *stops at the cap*. Decide the backpressure policy.

---

## Operator-reality lens ([[user-circumstances]])

The operator is unhoused with intermittent power and connectivity. This is not a footnote — it reshapes priorities the generic design would miss:

1. **Power-loss-mid-turn is the common case** → kill-9 convergence is THE design driver (M4); graceful shutdown is secondary; Shape A daemon stays rejected (no reliable supervision).
2. **Reviewer-unreachable is normal** → backpressure-under-absent-reviewer is a real policy, not an edge (M5); contemplation must have a *durable* substrate that survives the gap (Facet 8).
3. **Network/library FS** → `flock`-style single-writer is unreliable (M1 leans toward PID-lockfile or single-entrypoint).

---

## What I need from the architect (the calls only you can make)

1. **Decision 0 ruling** on the drift-fix family (`_anchor_pull` et al.): sanctioned semantic anchoring (amend CLAUDE.md), invariant violation (move into construction), or accept ephemeral-field (Shape B fallback)? *Everything downstream is gated here.*
2. **Targets:** pursue both T-resume *and* T-experience, or commit to T-resume only for now (and shelve continuous-field-life explicitly)?
3. **Green-light the cheap, ungated first step** (critical-path step 1 = task #6: the byte-identity + non-empty-discovery + ordering-determinism tests). This is safe, immediately buildable, closes a *proven* gap, and is a prerequisite for any identity work — it does **not** depend on Decision 0.

Recommended immediate move regardless of Decision 0: **do step 1 now** (it's pure test-hardening of an existing, proven gap), and rule Decision 0 next — because the no-drift spike (step 3) can't be honestly designed until both are settled.
