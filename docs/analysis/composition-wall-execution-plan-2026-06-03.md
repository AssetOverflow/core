<!-- CANONICAL | composition-wall-execution-plan-2026-06-03.md | 2026-06-03 | spec-and-review (Opus) lane | read-only analysis / execution plan for ADR-0207 §5 step 2 | verified against origin/main d9fc7f9 | NOT a new design -->

# Composition Wall — Execution Plan (R1/R4 first)

This is the execution scope for **ADR-0207 §5 step 2 (COMPOSITION)** — *not* a new design. It
takes the ratified substrate as given and answers the only question that matters next: *what,
concretely, must change in the built `generate/derivation/` composer to move the live metric,
and where is each target shape actually blocked?* Every per-case claim below was reproduced
read-only against the tree on 2026-06-03 by running the actual composer on the corpus cases.

## 1. The wall, restated from reproduction (folds in the wiring brief)

- `resolve_pooled` (the general pooled composer, `pool.py:62`) **refuses all ten R1/R4/R5/R6
  corpus lift-targets**, so wiring it to serving yields **+0 correct**; and it **wrong-commits
  `0016 → 510`** (gold 2), so wiring it wholesale is a live `wrong=0` regression.
- The only derivation symbol on serving is `product_bridge.resolve_promotable_product`
  (`math_candidate_graph.py:530`), and its safety is a **two-token target near-whitelist**
  (`money`+`make/earn`, `weight`+`total/move`) — it does not generalize.
- Therefore **WIRING is trivial and already done for the safe shapes**; the actual work is
  making the composer *build the right chain for a new shape and certify it*. The wire is the
  last, one-line step (mirror the `:530` block) once a shape builds-and-certifies.

## 2. Grounded per-shape diagnosis (all 15 corpus positives)

Ran `extract_quantities` → `extract_target` → the three composers
(`accumulation_candidates` / `multiplicative_candidates` / `candidate_chains`) on each. "Stage"
is where the shape is blocked (see §3). Golds are dataset-sourced (corpus invariant 6).

| case | comp | gold | #qty | target-agg | acc/mul/chn | result | **stage** |
|---|---|---|---|---|---|---|---|
| cv-0001 | R1 | 64 | 1 | None | 0/0/0 | none | **A** extraction (`$16` not extracted) |
| cv-0003 | R1 | 9 | 6 | None | 0/0/0 | none | **B** target |
| cv-0002 | R1 | 400 | 3 | total | 0/0/4 | wrong-only | **C** production |
| cv-0004 | R1 | 3840 | 4 | None | 0/1/4 | wrong-only | **C** production |
| cv-0005 | R4 | 3 | 3 | None | 0/0/0 | none | **B** target |
| cv-0021 | R4 | 4 | 4 | None | 0/0/0 | none | **B** target |
| cv-0006 | R5 | 14 | 2 | None | 3/0/4 | wrong-only | **C** production |
| cv-0022 | R5 | 38 | 2 | total | 0/1/4 | wrong-only | **C** production |
| cv-0007 | R6 | 21 | 3 | None | 0/0/0 | none | **B** target |
| cv-0008 | R6 | 15 | 1 | None | 0/0/0 | none | **A**+**B** extraction+target |
| cv-0009 | compare_mult | 60 | 1 | altogether | 0/0/0 | none | **A** extraction |
| cv-0018 | *(control)* | 28 | 2 | None | 0/0/2 | wrong-only (derivation) | control — `gate=baseline`, **already solves on serving** (not a lift target) |
| cv-0019 | additive | 1200 | 2 | None | 0/0/0 | none | **B** target |
| cv-0017 | *(control)* | 438 | 5 | None | 0/0/2 | wrong-only | control — solves on serving |
| cv-0020 | *(control)* | 450 | 3 | total | 0/1/2 | **GOLD-BUILT** | control — **D** gate exemplar |

Controls (cv-0017=case 0024, cv-0020=case 0021) already solve on serving via other paths; they
are regression anchors, not lift targets. cv-0020 is the **proof the build-then-gate pattern
works**: the pool *builds the gold* (450) but only commits it on serving because
`product_bridge`'s gate promotes it.

## 3. The four-stage failure taxonomy (and the `wrong=0` firewall at each)

The composer is a pipeline: **extract → characterize target → build production → certify (gate)**.
A shape can be blocked at any stage; each stage refuses (never commits) when incomplete, so
`wrong=0` holds throughout.

- **Stage A — extraction-thin.** The composer is starved of a needed quantity, so no chain is
  possible. *cv-0001* (currency literal `$16` not extracted — the derivation reader has no `$N`
  production; this is the gap I earlier *overstated as closed*), *cv-0008*, *cv-0009*. Firewall:
  no quantity → no candidate → refuse.
- **Stage B — target-uncharacterized.** Quantities are present but `extract_target` returns
  `aggregation=None`, so the composer doesn't know *what* to build. *cv-0003, cv-0005, cv-0007,
  cv-0019, cv-0021*. **Both R4 cases live here.** Firewall: no target → no admissible chain → refuse.
- **Stage C — production-wrong.** The composer builds chains, but the *wrong* ones (none equals
  gold), and the disagreement rule correctly refuses them. *cv-0002, cv-0004, cv-0006, cv-0018,
  cv-0022.* This is the hard core — "which quantities group, via which ops, in what order."
  Firewall: disagreement among wrong candidates → refuse.
- **Stage D — gold-built, needs gate.** The composer builds the gold (possibly among rivals); a
  *structural* promotion gate certifies and commits it. Exemplar: *cv-0020* via `product_bridge`.
  Firewall: the gate must prove the reading; a lone wrong chain with no rival (the *0016* pattern)
  is exactly what disagreement cannot catch, so **the gate must be structural, never
  disagreement alone.**

## 4. Execution sequence — one shape, end-to-end, instrumented

Each shape is a **hypothesis to test against the gates**, not a guaranteed win. Drive *one* shape
through its blocked stages to green on the corpus, then check the sealed 1,319, before starting
the next.

1. **R4 first — but it is NEW PRODUCTION, not a target tweak** (verified 2026-06-03 by code-read
   of `accumulate.py`: `_build_accumulation` is single-referent gain/loss running-total with **no
   goal/target/residual concept** — target characterization alone does **not** unblock it). cv-0005
   (single-referent `goal − Σchanges`) is the nearest extension of GB-3b.1 and the first build;
   cv-0021 (multi-referent give-away to a remainder) is two layers harder — separate, do not bundle.
   Goal-recognition is a new `wrong=0` surface (must refuse on ambiguous goal-language), and beware
   cv-0005 passing for the wrong reason (`10−3−4=3` also falls out of treating the goal as a start);
   the gate must consume the goal *as a goal*, and the real test is the sealed set, not cv-0005.
   Detailed first-build scope: **§10**.
2. **R1 next (cv-0001) — Stage A (extraction).** Add currency-literal (`$N`) extraction to the
   derivation reader, then test whether the comparative-multiplicative production (multiplier ×
   base) fires and builds `4×16=64`. Extraction-first; different stage from R4, so it exercises a
   different pipeline leg.
3. **Then Stage C shapes (cv-0002/0004/0006/0022)** — the genuine wall: building the correct
   grouping/op-order. Highest risk, do last, with the most instrumentation. Investigation task:
   `docs/handoff/stage-c-composition-investigation-2026-06-03.md`.

## 5. The promotion gate (generalize `product_bridge`, do not relax disagreement)

Every new production needs a co-designed structural gate, modeled on `product_bridge` but real:

- Use `extract_target` + `target_units` to prove the built chain answers *the asked question in
  the asked units* (op-class + target + unit agreement), replacing the two-token whitelist with a
  general op-class/target proof.
- A chain may commit only if it is the unique reading that *structurally* certifies; otherwise
  refuse. **Disagreement is not the defense** — *cv-0016/0016* shows a lone wrong chain commits
  with no rival to disagree. The gate, not the pool, is the `wrong=0` firewall for committed
  compositions.

## 6. Acceptance gates (inherit ADR-0207 §6 verbatim)

train_sample stays `wrong=0` (6/44/0 or better); the no-reference `<N> times` hazard stays
refused; no partial chain commits with an unbound quantity; **progress measured on the 22-case
corpus AND the sealed 1,319** — a train_sample/corpus gain that does not move held-out does not
count; each gain lands as composer/extractor enrichment behind a gate, audited to confirm it is
**not** a new serving recognizer/injector branch (the §4 freeze).

## 7. Honest uncertainty

This is the research wall, not engineering. The payoff against the **sealed 1,319** is genuinely
unknown: the composer building gold on a corpus case does not mean the same production fires on
held-out paraphrases, and Stage C (correct grouping/op-order) is an open research problem, not a
known build. I can scope the work and the gates; I cannot promise R1/R4 transfer until the
productions exist and the sealed number actually moves. The gates (§6) are what keep that honest
— they will tell us the truth either way.

## 8. Correction recorded

I earlier asserted "extraction is substantially done; only EX-3 deferred; extraction is not the
open lever." Stage A (cv-0001: `$16` present in text, not extracted) shows that was overstated —
the ADR-0179 lever was largely shipped *for its four cases*, but per-shape extraction gaps remain
(currency literals at minimum). This does not unwind ADR-0207; the per-shape gaps are execution
detail and live here, not in the ratification ADR.

## 9. Reproduction-methodology correction

The `target-agg` column was first computed by passing the **full problem text** to
`extract_target`; serving passes only the **question clause**. For cv-0004 and cv-0006 the
aggregation word is in the body, not the question, so full-text wrongly read `combined`/`total`
where the serving-faithful call returns `None` (now corrected above). The other agg cells are
unaffected (their agg word is in the question). This changes no stage (both are Stage C) and no
claim. Methodology fix carried forward: reproduce serving behaviour with serving's inputs —
`extract_target` gets the question clause, the composers get the full problem.

## 10. R4 first-build scope (from code-read of `accumulate.py`)

R4 is **new production, not a target tweak** — confirmed by reading the source (not a trace):
`compose_accumulation` / `_build_accumulation` (GB-3b.1) computes single-referent gain/loss
*running-total* `start ± changes` and consults **no goal/target/residual concept**. Hard bails:
the anchor must establish exactly one quantity (`accumulate.py:70`); a new named actor refuses
(`continues_anchor_referent`, `:76`/`:143`); no unambiguous licensed change cue refuses
(`:87`/`:149`). So R4's `goal − accumulated` cannot be expressed regardless of target — both R4
cases build **0 candidates** at `d9fc7f9e` (latent, nothing passes for any reason yet).

- **cv-0005 first (single-referent, nearest extension of GB-3b.1).** A new production recognizing
  (a) a **goal** quantity as a distinct anchor type (*not* a running total), (b) accumulated
  same-referent changes, (c) a **residual** question target, computing `goal − Σchanges`. Single
  referent (Michael), so it reuses GB-3b.1's referent/cue guards.
- **cv-0021 second (harder).** Multi-referent give-away to a remainder —
  `(start − desired_remainder) − Σgiven`. Outside GB-3b.1's single-referent scope (refused at
  `continues_anchor_referent`); needs multi-referent accumulation **and** residual handling. Two
  layers beyond cv-0005; do not bundle.
- **Gate (mandatory, co-designed).** The residual chain commits only if `extract_target`
  structurally proves the residual question + op-class + unit agreement, and completeness consumes
  the **goal** quantity. Never disagreement alone (the 0016 firewall).
- **`wrong=0` hazard (latent, build-time guard).** `10 − 3 − 4 = 3` also falls out of
  *mis-anchoring* the goal as a running-total start — coincidental correctness. The production must
  consume the goal *as a goal*; the real test is the **sealed set**, not cv-0005's arithmetic.
- **Build-time discipline.** Whoever builds instruments the exact `_build_accumulation` interaction
  and the new production's path through `self_verifies` (completeness must require the goal
  consumed) **in-tree** — the code-read scopes *what* to build; the runtime path confirms *that it
  fires* before the one-line wire.
