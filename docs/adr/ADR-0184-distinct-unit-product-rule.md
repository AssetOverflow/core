# ADR-0184 — Distinct-unit product rule: cut the product-of-all over-commit (the first lever measured against real GSM8K)

**Status:** Accepted / Implemented. Implementation refined the mechanism: the rule
is a **commit-ineligibility downgrade in `classify_derivation`** (§3), *not* the
shared unit-clause failure §3 originally proposed — putting it in the shared gate
regressed the disagreement refusals ADR-0182 relies on (see §3.1, the finding).
Follow-on to
[ADR-0175](./ADR-0175-calibrated-attempt-and-eliminate-learning.md) (the
self-verification gate), [ADR-0182](./ADR-0182-cross-composer-disagreement-pooling.md)
(pooling), and [ADR-0177](./ADR-0177-cue-precision-learning.md) (cue precision — the
*next* lever this one hands off to).

> **One line.** A multiplicative product may compose quantities of **distinct**
> dimensions but must not multiply two operands of the **same non-empty unit**
> (`apples × apples`, `cards × cards × cards` → a meaningless squared unit). This
> single dimensional rule cuts the sealed reader's real-GSM8K wrong count
> **13 → 8 with zero coverage loss**, measured on `train_sample`.

---

## 1. Why this exists — the headline `3/47/0` was hiding the real reader

`3/47/0` is the **serving recognizer** (conservative; refuses what it can't read).
Run the **sealed comprehension reader** (`resolve_pooled` — everything ADR-0182
built) over the same 50 real cases and the picture is very different:

```
serving (recognizer):        3 correct / 47 refused /  0 wrong   ← the headline
sealed reader (resolve_pooled): 2 correct / 35 refused / 13 WRONG ← what we are building
```

The confuser probe's `wrong=0` is real *on its 30 curated cases* but was a
**misleading proxy** for real-GSM8K safety: the same reader commits **13 wrong**
answers on real problems. **All 13 are the whole-text product-of-all** — every step
`multiply`, every one the *unique* `complete` candidate, so it commits unopposed:

| case | committed | gold | operand units |
|---|---|---|---|
| 0042 | 2,400,000 | 30 | bags × apples × **bags** × **apples** × apples |
| 0048 | 19,200 | 4 | cards × weeks × **cards** × **cards** × **cards** |
| 0001 | 14,400 | 990 | _ × hours × your × **hours** × days |
| 0017 | 7,000,000 | 800 | _ × _ × days × **days** |
| 0018 | 60 | 16 | minutes × goals × hours |

The product-of-all self-verifies because **multiplication is unit-permissive**
(clause 3 of the gate lets multiply compose across any units) and it uses every
quantity (completeness ✓). The gate cannot tell a *rate-chain* product from a
coincidental one — the "self-verification is necessary but not sufficient" finding
(ADR-0175). This ADR removes the **dimensionally impossible** subset of those
products; the rest hands off to cue precision (§6).

## 2. The measured lever (decided by the real metric, not a guess)

Each candidate refusal rule, evaluated on the sealed reader over `train_sample`
(the metric that matters — `correct↑` ∧ `wrong↓`):

| rule | correct | wrong | refused |
|---|---|---|---|
| baseline (today) | 2 | **13** | 35 |
| **product repeats a non-empty unit** (this ADR) | **2** | **8** | 40 |
| product spans >1 clause | 1 | 4 | 45 |
| drop all products | 0 | 2 | 48 |

The **distinct-unit rule** is the only option that **cuts wrongs with zero coverage
loss**. "Span >1 clause" cuts more but destroys `0003` (a *correct* 3-sentence
rate-chain `48 boxes × 24 erasers/box × $0.75`); "drop all products" loses both
correct answers. Coverage is never bought at the cost of a correct answer.

## 3. The rule (as implemented)

The dimensional predicate (`_is_repeated_unit_product`): a **pure multiplicative
chain** (every step `multiply`) whose operands — including the start — repeat a
**non-empty** unit forms `unit²` (`apples × apples`, `cards × cards`), which is
almost never the answer to a word problem asking for that unit. Empty-unit operands
are exempt (an unknown unit cannot be shown to collide — and the *correct* `0003`
multiplies a blank-unit `0.75`). Divide is exempt — same-unit division (`feet /
feet`) is a legitimate dimensionless count. Dimensional, not lexical (ADR-0165-safe).

Such a product is **classified `exempt` (commit-ineligible) in
`classify_derivation`**, *not* failed in the shared `_base_reasons` gate. It stays in
the pool — it may force a disagreement refusal — but can never resolve as the answer.
A unique repeated-unit product is therefore `exempt`-only → refuse (the `0042`-class
cut); a distinct-unit product stays `complete` → commit (`0003`/`0021`).

### 3.1 Finding — why a shared unit-clause failure was wrong

The first implementation put the predicate in the shared unit-consistency clause, so
a repeated-unit product **failed** (was dropped from the pool entirely). That cut the
5 `train_sample` wrongs **but regressed the confuser probe `1 → 3`**: the
disguised-polarity cases `0001`/`0003` refuse only because the `coins × coins` product
*disagrees* with the `coins + coins` accumulation reading. Dropping the product left
the (wrong) additive reading unique → it committed (`0001 → 80`, `0003 → 30`). The fix
is the **downgrade**: keep the product as a commit-ineligible `exempt` candidate so it
still forces the disagreement, but can never commit. (This is the same commit-
ineligibility concept ADR-0182 introduced.) Pinned by
`test_downgrade_not_removal_preserves_disagreement_refusal`.

### Why this keeps the correct products

| case | product units | repeated non-empty unit? | verdict |
|---|---|---|---|
| 0003 ✓ | boxes × erasers × `''` | no | **commit** (kept) |
| 0021 ✓ | pounds × reps × sets | no | **commit** (kept) |
| 0042 ✗ | bags × apples × bags × apples | yes (bags, apples) | **refuse** (cut) |
| 0048 ✗ | cards × weeks × cards × cards | yes (cards) | **refuse** (cut) |

A genuine rate-chain composes *distinct* dimensions by construction; a product that
revisits a dimension is multiplying independent groups (`4 bags×20 + 6 bags×25`,
mis-read as `4×20×6×25`) — never a real quantity.

## 4. wrong=0 obligations (must discharge before merge)

1. **`train_sample` (real, the metric):** sealed-reader `wrong 13 → 8`, `correct`
   held at 2 (0003/0021). Failing-under-violation: a test that the 5 named cases
   (0001/0017/0042/0045/0048) refuse, and 0003/0021 still commit.
2. **Confuser probe:** `wrong` must not regress and positives still solve. The
   §3.1 finding makes this load-bearing: the naive shared-clause version regressed
   it `1 → 3`; the downgrade holds it at baseline (`1` on main pre-#481; `0` once
   anchor-skip lands). `0001`/`0003` must stay **refused**, not commit `80`/`30`.
3. **Practice search lane:** `search_runner` commits products; confirm `wrong=0` and
   `correct` not reduced (the rule may only *add* refusals there).
4. **Serving frozen:** `verify` is not on the serving path (`chat/` →
   `_score_one_candidate_graph`), so `3/47/0` stays byte-identical. Lane-SHA 8/8.
5. **Scope of the rule:** applies to `multiply` (and `divide`) steps only; `add`/
   `subtract` unchanged. A rare *legitimate* same-unit product (area `ft × ft`) will
   refuse — accepted (refuse-preferring; vanishingly rare in GSM8K).

## 5. Where it lives

`generate/derivation/verify.py`: `_is_repeated_unit_product` (the dimensional
predicate) consulted by `classify_derivation`, which downgrades an otherwise-
`complete` repeated-unit product to `exempt`. `self_verifies` / `_base_reasons` are
**unchanged** — so the search lanes (practice) and serving stay byte-identical, and
the change is confined to the pool's commit-eligibility (where the over-commit lives).
Sealed lane only. `tests/test_adr_0184_distinct_unit_product.py` pins the predicate,
the downgrade, the `0042`-class refusal, and the §3.1 downgrade-not-removal
regression guard.

## 6. What this does NOT fix — the honest hand-off to cue precision

`wrong` drops to **8**, not 0. The remaining 8 (0011, 0016, 0018, 0019, 0025, 0028,
0032, 0047) are products over **distinct** units that are *still the wrong shape* —
rate problems like 0018 (`2 goals / 15 min × 120 min`, mis-read `15 × 2 × 2`). Telling
a correct rate-chain (`distinct units bound by per/each`) from a coincidental
distinct-unit product is exactly the **cue-precision** problem
([ADR-0177](./ADR-0177-cue-precision-learning.md) CP-2b) — *which* multiply a cue
licenses. That is the next lever and must not be faked with a per-case rule here (the
overfitting trap, `feedback-synthetic-corpus-overfitting-trap`).

This ADR is a **safe, general down-payment** (`13→8`, zero coverage loss), not the
finish. It also establishes the **real scoreboard**: every future coverage lever is
measured by `resolve_pooled` over `train_sample` (`correct↑` ∧ `wrong↓` toward
`≥10, 0`) — never by the curated confuser count alone.

## 7. Dependency for any of this to reach the headline

Even at `wrong=0` the sealed reader cannot move serving `3/47/0` without a
**ratification bridge** (ADR-0175 Phase 5): a reviewed path that promotes the sealed
reader's reliable readings into the serving path. Cutting the 13→8→0 wrongs is the
*precondition* (a wrong-prone reader can never be ratified); the bridge is the
separate, later step that makes the headline finally move.
