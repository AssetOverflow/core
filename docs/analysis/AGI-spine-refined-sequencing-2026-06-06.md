# Refined sequencing — from where we actually are to AGI-candidacy (2026-06-06)

**Status:** PLAN (refines [AGI-candidacy-autonomous-improvement-roadmap-2026-06-05](./AGI-candidacy-autonomous-improvement-roadmap-2026-06-05.md), grounded in a 7-layer ground-truth audit of the real tree at main + #596).
**Telos:** [[project-core-is-one-continuous-life]] — `listen → comprehend → recall → think → articulate → learn → replay`, as one continuous, ever-improving life, deployable at the edge (offline, CPU-only, deterministic, never fabricating).

## The finding that reorders everything

The 2026-06-05 roadmap (`MEASURE → COMPREHEND → REALIZE → DETERMINE → LOOP`) assumed the work was *building* each organ. The audit shows otherwise: **the organs are built; they are disconnected libraries.** Each is correct in isolation and callable only from its own tests.

| Layer | Built? | The real gap (verified) |
|-------|--------|--------------------------|
| **MEASURE** | ✅ real composed capability index — `evals/capability_index/`, frozen baseline `0.937258`, breadth 8, `wrong_total=0`, deterministic digest reproduces live | #596's relational reader is **inert** — no adapter; the curve won't register the capability we just shipped |
| **COMPREHEND** | ⚠️ template matcher, not a general reader — coverage *is* the template list; only 51/794 index cases exercise general comprehension | not language-general; #596 reader **inert** (no lane) |
| **REALIZE** | ✅ write/recall/persist correct (R0/R1/R1c, OOV, Shape B+) | **not wired into the live turn loop** — "a library, not a lived organ"; no conversation accrues knowledge |
| **DETERMINE** | ✅ sound one-hop, same-predicate, positive-only, as-told over 17 predicates | **callable only from tests**; no transitive hop (though `proof_chain` ROBDD exists to reuse); not wired |
| **LOOP** | ⚠️ `idle_tick` runs, but only advances **intentionally-partial** discovery chains | does **not learn from lived determined facts**; `determine` not wired in |
| **ESTIMATION** | ✅ calibration machinery (`reliability_gate`, Wilson floors) built | no likelihood→serving path — **correctly gated off** until DETERMINE+MEASURE solid |
| **EDGE-RUNTIME** | ⚠️ runs CPU-only/offline/deterministic today (verified) | offline-readiness **asserted, not proven**; per-turn persistence **O(n²) cliff** bites when `persist_session_state=True`; no budget gate |

**So the remaining critical path is integration + measurement, not open-ended organ-building.** The one genuinely open-ended risk (a *general* COMPREHEND reader) we grow incrementally **on the yardstick**, so generalization is proven, not claimed. #596's wrong=0 hazard — fabricating `sibling_of(carol, dan_during_school)` — is the proof of why: a capability off the yardstick hides its own breaches. (Found by post-merge lookback, fixed in #597.)

## Refined critical path

```
INSTRUMENT ──► WIRE ──► DEEPEN ──► CLOSE ──► [later] ESTIMATION
(put it on    (organs    (transitive  (loop learns
 the yardstick  into one   determine    from determined
 + edge gate)   live loop)  via proof_chain) facts)
```

### Step A — INSTRUMENT (two cheap, independent instruments; parallel-safe)

**A1 · Put #596 on the yardstick.** Add a `comprehension_relational_predicate` capability lane: binary-relation prose → gold `(predicate, subject, object)` triples authored by a source **independent** of `generate/meaning_graph/relational.py` (a small relation-table oracle over the closed predicate vocab), scored through `comprehend_relational → determine`. Append the adapter, **re-freeze `baseline.json`**, watch breadth 8→9 and the digest change deliberately.
- *Falsification:* independent gold (INV-25); reader must not share code with the gold producer (INV-27 disjointness). A genuine climb = breadth 8→9 with `wrong_total` still 0.
- *Edge:* +negligible (<tens of cases; index runs ~0.55s CPU-only).
- *Why first:* it's the only thing that makes "we added a capability" falsifiable — and it would have caught the #596 fabrication as `wrong>0`.

**A2 · Edge budget gate (mission-critical, uncharted by the old roadmap).** Add `evals/edge_budget/`: a fixed-length real chat session with `persist_session_state=True`, Python backend, that **fails on breach** of pinned ceilings — per-turn p95 latency, per-turn checkpoint bytes-written, total session bytes. This converts "edge-deployable" from asserted to **proven**, and instruments the O(n²) persistence cliff before it blocks a clinic/disaster-center deployment.
- *Falsification:* a constrained-device budget the session must stay under across N turns; fails loudly when persistence cost grows superlinearly.
- *Why now:* the mission (disaster center, rural clinic, village school) *is* the edge axis; it must be a gate, not a hope.

### Step B — WIRE: realize + determine into the live turn loop (highest-leverage capability move)

After a declarative (query-free) user turn is comprehended, call `realize_comprehension(comprehension, ctx)` on the **same `SessionContext` the runtime already holds**; answer a later question turn via `determine(...)` over `recall_realized`. This is the first time a **conversation actually accrues knowledge** — the library becomes a lived organ. Directly serves the "one continuous life" telos.
- *Falsification:* a multi-turn replay where turn N+1 answers from turn N's told fact, `wrong=0`, and the fact survives reboot (Shape B+).
- *Edge:* realize write is O(1) + an O(n) linear vault scan (no ANN); fine on a constrained box — but this is what makes A2's persistence gate load-bearing.
- *Depends on:* A1 (so the gain is measured), COMPREHEND coverage (grow incrementally).

### Step C — DEEPEN: transitive determination via the existing prover

When `member(a,c)` isn't directly grounded, collect realized `member` facts reachable from `a` via `recall_realized`, hand them as opaque Boolean atoms to the **existing sound+complete `proof_chain` ROBDD entailment decider** — reuse, don't build new inference. First multi-hop reasoning over realized knowledge.
- *Falsification:* an independent transitive-closure oracle; `wrong=0` preserved; every committed conclusion independently checkable.
- *Depends on:* B (facts must be live in the loop first).

### Step D — CLOSE: the loop learns from determined facts

In `contemplate`/`idle_tick`, promote a **grounded** sub-question (concrete `(connective, object)` + determined polarity) into a *complete* candidate, so the flywheel proposes from what it **determined**, not just the intentionally-partial discovery chains it emits today. This is the step that makes "forever improving" real and falsifiable.
- *Falsification:* a frozen replay shows the capability index (Step A) climbing across loop iterations, autonomously, under HITL ratification — monotonic, junk-free.
- *Depends on:* B + C.

### Step E — ESTIMATION (deliberately last, unchanged from the roadmap)

Only after the assert/refuse floor (B–D) and calibration measurement (A) are solid: wire one `LicenseDecision` from a committed `ClassTally` to gate one served answer on the safest action. Never a designed-in default; HITL-ratified.

## Invariants (unchanged, non-negotiable at every step)

`wrong=0` structural · reviewed learning stays HITL · deterministic replay · identity continuity (L11) · `versor_condition < 1e-6` · no forbidden-site normalization · exact CGA recall · **every step on the yardstick before it counts** · **every step under the edge budget**.

## What changed vs the 2026-06-05 roadmap

- The bottleneck is **integration, not construction** — the organs exist, disconnected. Sequencing is now *wire + measure*, not *build*.
- **EDGE-RUNTIME is promoted to a first-class, gated axis** (A2). The old roadmap had no edge gate; the mission requires one.
- **DETERMINE deepening reuses `proof_chain`** rather than building inference (Step C).
- The single highest-risk item remains a *general* COMPREHEND reader; we de-risk it by growing it **on the yardstick**, incrementally, so generalization is proven.
