<!-- CANONICAL | gsm8k-lift-program-strategy-2026-06-04.md | 2026-06-04 | strategy (Opus) lane | program plan for sizeable GSM8K lift under ADR-0207 | grounded against origin/main 3a72d69 | NOT a new design — sequences existing substrate -->

# GSM8K Lift Program — Strategy for Sizeable, Sealed-Verified Lift

**Goal (stated honestly):** move the **real** number — the sealed 1,319 (and full GSM8K),
not the 50-case train_sample — by *meaningful* chunks, with `wrong=0` preserved at every
step. This is the program plan, sequenced from the substrate ADR-0207 ratified.

> ## ⚠ The brutal baseline (read this first)
>
> The **real external number is `0 / 0 / 1319`** — sealed real GSM8K test (HuggingFace
> `openai/gsm8k`), claims_ledger row A: **0 correct out of 1,319. CORE solves *nothing* on
> held-out GSM8K.** The train_sample `7/43/0` is on a **50-case unsealed sample CORE was
> effectively built against** — the ledger's own rule: *"never present A as an accuracy."*
>
> So "sizeable lift" means **getting the sealed number off zero** — a fundamentally harder
> thing than the train_sample increments suggest. The R4 win (cv-0005) moved a *proxy*; it
> may be **+0 on the real 1,319** (goal-residual fires on 2/455 visible cases; whether it
> fires on *any* sealed case is unknown until Stream 0 runs). Every magnitude claim below is
> against this: **we are at zero on the bar that counts.**

**Grounding (origin/main `3a72d69`, 2026-06-04):** train_sample 7/43/0 (R4 goal-residual
landed, sealed-pending). Composition class frequencies across the 44 refusals (multi-tagged,
`composition-capability-scope §8`): **R5 multi-step 27, R1 derived-symbol 24, R6 percent 18,
R4 residual 10, R2 inverse 6, R3 partition 3.** Only R4 is landed.

---

## 0. The leverage equation (why this plan is shaped as it is)

> **lift ≈ Σ over shapes of [ class_frequency × tractability × sealed_transfer ]**, divided by
> **per-shape cost** — and per-shape cost is dominated by the *hand-built promotion bridge*,
> not the composer.

Three consequences fall straight out, and they set the streams:

1. **R4 gave +1 because it is rare (10/44, and most are multi-referent).** Chasing more R4-like
   rare shapes one-by-one is a *trickle*. The big frequencies are **R1 (24)** and **R5 (27)** —
   but both need hard productions (R1 = quantity **reuse / DAG**; R5 = multi-step rate/duration).
2. **Per-shape cost is the bridge, not the reading.** Today every shape needs a *hand-coded*
   serving promotion gate (`product_bridge`, `resolve_promotable_goal_residual`). That is the
   tax that makes lift one-shape-at-a-time. Removing it (Stream A) is the **force multiplier**.
3. **No lift counts until the sealed set says so.** train_sample is a 50-case proxy; the 7/43/0
   win is *unverified on the real bar*. Sealed measurement is the **prerequisite**, not a
   formality (Stream 0).

**Honest magnitude expectation:** there is no single move that jumps the sealed number by a big
chunk *cheaply and safely*. Sizeable lift is **compounding**: build the flywheel + the general
consumption bridge so each subsequent shape is cheap, then spend the expensive research on the
**high-frequency** shapes (R1/R5). The curve bends up when per-shape cost drops, not from any
one production.

---

## Stream 0 — Sealed baseline (PREREQUISITE, blocks everything)

Until this runs, every number below is train_sample theater.

- **0.1** Resolve `docs/handoff/sealed-measurement-obligation-2026-06-04.md`: operator/CI
  decrypts + runs the sealed 1,319 at HEAD, confirms **sealed `wrong==0`** and records the
  sealed **correct** count. *Did R4 (cv-0005) actually move the sealed number, or was it +0 on
  held-out?* This answer calibrates the whole program.
- **0.2** Stand up a **repeatable sealed-measurement gate** the operator can run per-increment
  (decrypt → `parse_and_solve` → counts → ledger row). Without a per-increment sealed check,
  the program cannot tell real lift from overfitting. This is the single most important
  infrastructure item — the program's measuring stick.
- **Exit:** a known sealed baseline `(correct, 0, refused)` and a one-command sealed re-measure.

## Stream A — The force multiplier: general composition-promotion consumer

**The highest-leverage infrastructure in the program.** Replace N hand-built promotion bridges
with one gated consumer.

- **A.1** Design a **ratified-composition-frame → structural-promotion-gate → serving** bridge:
  a single serving consumer that takes a *ratified frame* (shape + op-class + target signature)
  and promotes any reading that passes the **generalized gate** (`extract_target` + `target_units`
  + self-verify grounding∧unit∧completeness + the divergence-firewall pattern). `product_bridge`
  and `goal_residual` become *instances* of this consumer, not bespoke code.
- **A.2** The `wrong=0` firewall is the entire risk: an auto-promotion consumer that admits a
  wrong frame is the prime-directive violation. Gate it harder than any single bridge — every
  promoted frame carries its own divergence-firewall test (the goal-vs-possession pattern,
  generalized) and a sealed-gated ratification.
- **A.3** Wire **cue-precision (ADR-0177)** as the *ranking* signal into this consumer (it is
  currently inert / consumed nowhere on serving) — it ranks which frame promotes when several
  self-verify, replacing per-shape disagreement-refusal with learned precision.
- **Payoff:** after A, a new shape is "ratify a frame + its firewall test," not "write a bridge."
  Per-shape cost collapses; the flywheel's output finally reaches serving.

## Stream B — Harvest at scale (the trickle, industrialized)

The cheap wins, mined from the real corpus instead of the 50.

- **B.1** Acquire **full GSM8K train (7,473 cases, public)** into a harvest lane (the repo has
  only the 50-sample + the encrypted sealed holdout — the harvest pool must be added).
- **B.2** Point the existing **practice / contemplation / propose** loop (`evals/gsm8k_math/practice/v1/`,
  `propose_runner.py`) at the full train set: attempt → diagnose refusals → for each, classify
  *structural match but lexeme/frame miss* vs *needs new production*.
- **B.3** The **lexical-variant harvest** (your idea, grounded): structurally-built shapes that
  refuse only on a closed-set miss — a goal verb, a progress verb (`saved` is a live example —
  not in the change-cue vocab), a residual cue. Each becomes a one-lexeme ratification through
  the contemplation→HITL corridor, firewall-gated, landed via Stream A. The visible proxy showed
  a **~58-case remainder-question family** (9% of visible) — at full-train scale this is the
  steady trickle, *if* A makes landing cheap.
- **Honest cap:** B is a trickle, not a flood. Its value is *steady + cheap*, and it compounds
  only once Stream A removes the landing tax.

## Stream C — The high-frequency research bets (where the big chunk lives)

The expensive, uncertain work — but the only path to a *sizeable* single move.

- **C.1 — R1 derived/intermediate symbol (24/44, the biggest single class).** Needs **quantity
  reuse** (`base + multiplier×base`, the value used twice) — a **DAG**, which the linear chain
  cannot express (flagged GB-5). This is the genuine research. Cracking it unblocks the largest
  class at once. Build the DAG composer + its promotion frame (via A), prove on the near-pure
  exemplars (0027/0008/0029/0038), **measure on sealed**.
- **C.2 — R5 multi-step rate/duration/scalar (27/44, biggest overall).** Multi-step chains with
  a scalar-of-a-prior-stage and referent binding (0030/0015). Medium-hard; large frequency.
- **C.3 — Sequence by frequency × tractability:** the Stage-C investigation
  (`docs/handoff/stage-c-composition-investigation-2026-06-03.md`) is the input that ranks the
  cheapest real entry into C; run it first to pick C.1-vs-C.2 ordering on evidence, not guess.
- **Risk discipline:** each C build is a hypothesis tested against the **sealed** set, not the
  corpus. A corpus flip that does not move sealed is overfitting (ADR-0207 §6) and is reverted.

## Stream D — Measurement & `wrong=0` discipline (the spine)

- Every increment: train_sample (fast proxy) **and** the Stream-0 sealed gate (the real bar).
- The serving metric "moves only via ratified PRs" (CLAUDE.md) — each lift PR carries its sealed
  delta or an explicit sealed-pending obligation note (as R4 did).
- Track the **sealed correct count** as *the* program metric. train_sample is a smoke proxy.

---

## Sequencing & priorities

```
NOW    Stream 0  (sealed baseline + per-increment gate)         ── blocks all claims
THEN   Stream A  (general promotion consumer)  ║ Stream B.1-2  (full-train harvest lane)
        — A is the force multiplier; B feeds it cheap wins
NEXT   Stream C.3 → C.1/C.2  (the big-frequency research, ranked by the Stage-C investigation)
ALWAYS Stream D  (sealed-gated, wrong=0, ratified-PR discipline)
```

**Priority order if forced to pick one:** **Stream 0**, then **Stream A**. Reason: without 0 we
are flying blind on the real number; without A every win costs a hand-built bridge and the
flywheel never compounds. C is where the big chunk lives, but it is wasted effort until 0 can
measure it and A can land it cheaply.

## What "meaningful lift in sizeable numbers" honestly requires

1. The sealed gate exists and the R4 win is confirmed real (Stream 0).
2. The landing tax is gone (Stream A) — so the flywheel and each new shape are cheap.
3. The expensive research lands on the **high-frequency** shapes R1/R5 (Stream C), each
   sealed-verified.

That is the honest path to a curve that bends up. It is a program, not a patch — and the first
real milestone is **Stream 0**, because we do not yet know whether today's 7/43/0 moved the
number that actually counts.

## Cross-references
- Substrate: ADR-0207 (ratify · freeze · execute), §5 lever order, §6 gates.
- Inputs: `composition-capability-scope.md` (§8 class frequencies), `composition-wall-execution-plan-2026-06-03.md` (stage taxonomy), `stage-c-composition-investigation-2026-06-03.md` (Stream C ranking), `sealed-measurement-obligation-2026-06-04.md` (Stream 0.1).
- Landed exemplar of the build-then-gate pattern Stream A generalizes: `generate/derivation/goal_residual.py` + `resolve_promotable_goal_residual`.
