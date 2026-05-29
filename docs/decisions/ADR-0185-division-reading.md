# ADR-0185 — Division reading (rate / partition): the first genuine multi-step capability, eliminate-then-solve

> **⚠️ SUPERSEDED (premise refuted) — 2026-05-29.** This ADR's central premise,
> *"the engine cannot divide,"* is true only of the **derivation reader**
> (`generate/derivation/*`, `resolve_pooled`), which the 2026-05-29 topology audit
> proved is **disjoint from the reader that owns the official `3/47/0` metric**. The
> goal organ — the candidate-graph reader (`generate/math_candidate_graph`) —
> **already divides, multiplies, and does comparative arithmetic**; its wall is the
> recognizer→injection coverage gap, not arithmetic. A division *reading* added to the
> derivation reader therefore cannot move `3/47/0`. See
> [ADR-0186](./ADR-0186-sealed-candidate-graph-injector-lane.md) §1 for the topology
> finding. **This ADR is retained as a record only; it is NOT implemented.** Any
> division work belongs in the candidate-graph path under ADR-0186's seal.

**Status:** **Superseded by [ADR-0186](./ADR-0186-sealed-candidate-graph-injector-lane.md)**
(premise refuted; not implemented). Originally: Proposed (spec only — no code). Follow-on to
[ADR-0184](./ADR-0184-distinct-unit-product-rule.md) (which cut the dimensionally-
impossible products, `13 → 8`) and [ADR-0182](./ADR-0182-cross-composer-disagreement-pooling.md)
(pooling + commit-ineligibility).

> **One line.** The engine can multiply and add/subtract but **cannot divide** — and
> ~⅔ of the remaining real-GSM8K failures need division (rate, ratio, partition).
> Add a division *reading* (cue-licensed, gated by self-verification, pooled), used
> **eliminate-first** (a grounded `÷` reading disagrees with the flat product → the
> wrong refuses) then **solve** (the `÷` reading commits when it is the unique
> grounded reading).

---

## 1. The metric this serves (and why the headline is the wrong one)

`serving = 3/47/0` is the conservative recognizer, **frozen** until a Phase-5
ratification ([ADR-0175](./ADR-0175-calibrated-attempt-and-eliminate-learning.md)).
The metric this ADR moves is the **sealed comprehension reader** over the real
`train_sample` (`resolve_pooled`): currently **2 correct / 8 wrong / 40 refused**
(post-ADR-0184). Progress = `correct ↑` ∧ `wrong ↓` toward `≥10 / 0`. Every claim
below is measured there, never on the curated confuser count.

## 2. What the microscope proved about the remaining 8 wrongs

The 8 (`0011 0016 0018 0019 0025 0028 0032 0047`) are **all** the flat product-of-all
committed unopposed. Classifying each by what its *gold* computation needs:

| need | cases |
|---|---|
| **division** (rate / ratio / partition) | 0011, 0016, 0018, 0028, 0047 |
| **percentage / decimal** | 0019, 0028, 0032 |
| comparative arithmetic (`N more/less than M`) | 0016 |
| multi-step grouping | 0025 |
| **extraction gaps** (currency `$100,000 → 100`, units `coconut`/`different`) | 0011, 0028, 0047 |

**Division is the single largest need** (5 of 8), and it is also the most common
missing op across the 47 refused. The engine today has *no* division reading at all —
the only readings it forms are additive accumulation and multiplicative products.

## 3. Why there is no flat shortcut (the two traps measured and rejected)

Eliminate-first is right, but it must not overfit or trade away a correct answer.
Both flat shortcuts were measured and rejected:

| candidate | result | verdict |
|---|---|---|
| remove `per` from multiplicative cues | 8 → 7 (zero loss *on the 50*) | **overfit** — on real GSM8K `12 eggs per carton × 5 cartons = 60` is a legitimate rate×quantity multiply; `per` removal would lose it. Tuning to the sample. |
| downgrade cross-clause flat product → exempt | 8 → 2, but `correct 2 → 1` | **loses `0003`** (a correct rate-chain) — trades a real solve to kill guesses. |

The distinguisher between the 8 wrong products and the 2 correct ones (`0003`
`boxes×erasers×$`, `0021` `pounds×reps×sets`) **is the structure** — rate-binding,
comparative, division — which is exactly what the engine cannot read. So there is no
non-overfitting flat rule; the only honest path is to **read the structure**.

## 4. The mechanism — a division reading

A composer that proposes a grounded `÷` candidate, licensed by a **division cue**
(lexeme-level, ADR-0165-safe — names the markers, does not parse grammar):

- **rate / ratio:** `X per Y`, `X / Y`, `how many X per Y` → `X ÷ Y`.
- **partition:** `split / divide / share N into M`, `N split among M`,
  `packs … into M (groups/bags)` → `N ÷ M`.

The candidate runs through the **unchanged** self-verification gate (grounding ∧ cue
∧ unit ∧ completeness) and the pool. Two roles, in order:

1. **Eliminate (first).** A grounded `÷` reading that competes with the flat product
   forces a **disagreement → refuse** (the wrong product stops committing). Even an
   incomplete `÷` reading (isolated-foreign / partial) enters as a commit-ineligible
   `exempt` candidate and still forces the refusal (the ADR-0182/0184 pattern).
2. **Solve (then).** When the `÷` reading is the unique grounded reading, it commits —
   coverage.

### 4.1 The `per` cue-semantics correction (done right)

`per` is currently in `MULTIPLICATIVE_CUES`, which is wrong: **`X per Y` denotes a
rate `X/Y` (division)**, not `X×Y`. But §3 showed *removing* it overfits. The correct
fix is **reclassification, not removal**: `per` licenses the new **division**
composer (the rate numerator/denominator), and the multiply that *scales by* a rate
(`rate × quantity`) is licensed by the quantity structure, not by `per`. This makes
`per`-products refuse-or-divide instead of blindly multiplying, without losing
legitimate rate×quantity multiplies (which the division reading + a scaling step
recover). Validated on `train_sample` + the confuser probe, not the 50-sample alone.

## 5. Honest scope — division alone will not flip most of the 8

This is the load-bearing caveat. Division is **necessary but not sufficient** for the
8 because they are entangled with other missing capabilities:

- `0016` needs **comparative arithmetic** (`2 more than 5 → 7`) *and* `per`-as-rate
  before `14 ÷ 7 = 2`.
- `0011`/`0028` need **currency extraction** (`$100,000`, `$2`) before any op.
- `0019`/`0032` need **percentage** reading.

So division's *immediate* `train_sample` effect is mostly **elimination** (flat
products refuse where a `÷` reading disagrees), with **solves** arriving only as the
companion capabilities land. The obligation (§7) is therefore framed as `wrong ↓`
(never ↑) with `correct` held or rising — not an inflated solve claim. Claiming
division alone flips these would be the overfitting trap (`feedback-synthetic-corpus-
overfitting-trap`).

## 6. The roadmap this opens (eliminate-then-solve, each measured)

Division is capability **1** of the multi-step reading the goal requires. Sequenced by
leverage × foundational-ness, each gated by `wrong=0` and measured on `train_sample`:

1. **Division reading** (this ADR) — rate/ratio/partition + `per` reclassification.
2. **Comparative arithmetic** — `N more/less than M → M±N` (a reading-correctness fix;
   unblocks `0016` and is general across GSM8K).
3. **Currency / decimal extraction richness** — `$100,000`, `$2`, `1%` (the
   extraction gaps that garble `0011`/`0028`).
4. **Percentage reading** — `N% of X`, `N% less/more` (`0019`/`0032`).
5. **Multi-step chain shapes** — `anchor − sum`, `sum-then-scale`, division-then-±
   (the mixed-op chains gold actually uses).
6. **Ratification bridge** ([ADR-0175](./ADR-0175-calibrated-attempt-and-eliminate-learning.md)
   Phase 5) — the hard dependency: until a reviewed promotion path exists, **none** of
   this moves the serving `3/47/0` headline, however good the sealed reader gets.

## 7. wrong=0 obligations (before any merge of the implementation)

1. **`train_sample`:** sealed-reader `wrong` must **drop, never rise**; `correct` held
   or rising. Failing-under-violation: the cases a `÷` reading refuses (disagreement)
   are pinned; any case it *commits* is gold-checked.
2. **Confuser probe:** `wrong` does not regress; positives still solve. A division
   composer must not let any curated case commit a wrong `÷`.
3. **Serving frozen:** the composer is sealed (`chat/` does not import it); `3/47/0`
   byte-identical, lane-SHA 8/8.
4. **No overfitting:** every cue is a *general* division marker validated beyond the
   50-sample; the `per` reclassification is justified by cue semantics, not by a
   sample delta. No per-case rule.
5. **Commit-ineligibility:** an incomplete `÷` reading may force a refusal but never
   commit alone (full completeness still required to commit — the ADR-0175 guarantee).

## 8. Why this obeys the standing principles

- **Decode, don't guess** (thesis): a division *reading* comprehends rate/partition
  structure; it does not store a flat product. It teaches the engine to *find* better.
- **Eliminate-first:** the `÷` reading's first job is to make wrong flat products
  refuse (disagreement), before it earns any commit.
- **wrong=0 > coverage** (ADR-0175): obligations gate on `wrong ↓`, not solve count.
- **ADR-0165:** cues are lexeme markers, not grammar templates.
- **No contradiction** with in-use ADRs: extends the pool/gate, changes no serving
  path, reuses the commit-ineligibility mechanism rather than inventing a new gate.
