# ADR-0182 — Cross-composer disagreement pooling: refuse distractor-quantity confusers without a reactive cue rule

**Status:** Proposed (spec only — no code). Follow-on to
[ADR-0163-F2](./ADR-0163-F2-confuser-corpus-spec.md) (the confuser probe),
[ADR-0175](./ADR-0175-calibrated-attempt-and-eliminate-learning.md) (the
self-verification gate), and [ADR-0177](./ADR-0177-cue-precision-learning.md)
(cue precision). Sits *before* CP-2b in the dependency chain: it lets the
**disagreement rule** refuse a class of confusers that cue precision alone cannot
yet, using only structure the composers already produce.

> **One line.** Make the wrong=0 *disagreement* rule do the refusing: when a
> distractor-quantity problem admits both a blunt product reading and a competing
> additive reading, pool the self-verifying candidates **across composers** and let
> their disagreement refuse — instead of trying (and failing) to write a cue rule
> that tells a real multiplier from a distractor.

---

## 1. Why this exists (the failure it fixes)

The confuser probe's two **distractor-quantity** cases misfire — they are 2 of the
5 remaining `wrong` after [ADR-0163-F2 EX-6](./ADR-0179-extraction-richness.md)
(hyphen-bonded units) drove the pseudo-accumulation pair to refuse:

| case | text | committed | gold | via |
|---|---|---|---|---|
| `confuser-v1-0014` | "Kate has 20 pencils. She studies **for** 3 hours and then buys 5 more pencils. How many pencils?" | `20×3×5 = 300` | 25 | `search_chain` |
| `confuser-v1-0016` | "A train travels at 60 miles **per** hour **for** 2 hours. Tom has 8 tickets and buys 4 more tickets. How many tickets?" | `60×2×8×4 = 3840` | 12 | `search_chain` |

Both come from `search_chain`'s **product-of-all-quantities**, licensed by a present
multiplicative cue and forced to consume every quantity by the completeness clause.

### The microscope finding: no tight rule separates these from the legitimate cases

The distractor products are **structurally identical** to the legitimate
multiplicative products that `train_sample` requires to keep committing
(`correct` must never drop):

| case | text fragment | product | cue | operand units | required |
|---|---|---|---|---|---|
| `confuser-0014` (distractor) | "studies **for** 3 hours … buys 5 more pencils" | 20×3×5 | `for` | pencils × hours × pencils | **refuse** |
| `train-0021` (correct) | "bench presses 15 pounds **for** 10 reps … 3 sets" | 15×10×3 = **450** ✓ | `for` | pounds × reps × sets | **commit** |
| `confuser-0016` (distractor) | "60 miles **per** hour … 4 more tickets" | 60×2×8×4 | `for`/`per` | miles × hours × tickets | **refuse** |
| `train-0003` (correct) | "24 erasers in **each** box … 48 boxes" | 48×24×… = **864** ✓ | `each` | boxes × erasers | **commit** |

Every tight lexeme/gate rule was tested and breaks a protected case:

- *"refuse `for`-licensed cross-unit products"* → breaks **0021** (same cue, correct).
- *"refuse products mixing target-unit + foreign-unit operands"* → breaks **0003**
  (`boxes` is foreign to the target `erasers`, yet the product is correct — the
  canonical legitimate product has the **exact** distractor shape).

The only real difference is semantic: `"for 10 reps"` is a multiplicative binder;
`"for 3 hours"` is a durational adjunct. Distinguishing them by cue is precisely the
**cue-precision** problem that [ADR-0177](./ADR-0177-cue-precision-learning.md)
measured as *not yet solvable* ("no cue is reliable yet — every pattern floors at
~0.0"). Writing a rule to refuse 0014/0016 specifically would be a **reactive
surface patch** — the overfitting trap recorded in
`feedback-synthetic-corpus-overfitting-trap`.

So the lever is **not** "tell a good cue from a bad one." It is "make the engine
notice it has two incompatible readings and refuse the ambiguity" — which is the
wrong=0 disagreement rule it already owns.

## 2. Why naive pooling is not enough (the completeness obstacle)

The disagreement rule (`select_self_verified`) refuses when ≥2 **self-verifying**
derivations disagree. The obvious idea — run accumulation *and* the product search
and pool their candidates — does **not** work as-is, because the distractor problem
has only **one** self-verifying reading:

- The additive reading of 0014 (`20 + 5 = 25`, the actual structure) **leaves
  `3 hours` unused**.
- The **completeness clause** (ADR-0175: "a trustworthy derivation must account for
  every quantity the problem states") therefore **rejects** the additive reading —
  it does not self-verify, so it never enters the pool.
- The product reading consumes every quantity, so it *is* complete, *is* the unique
  self-verifying candidate, and commits `300`.

This is the deep cause: **for a distractor problem, completeness guarantees that the
only self-verifying reading is the one that wrongly consumes the distractor.** The
clause that protects multi-step problems is the same clause that mandates the
distractor misfire. Pooling must come *with* a principled, narrow completeness
relaxation, or it changes nothing.

## 3. The mechanism

Two coupled changes, both refuse-preferring, both gated by wrong=0 obligations.

### 3a. Isolated-foreign completeness exemption (read-only, commit-ineligible)

Relax completeness for a quantity that is an **isolated foreign unit** *relative to a
reading*: its unit is non-empty and equals **no *used* operand's unit** in that
reading. Such a quantity is a *candidate distractor* — it stands alone in a
dimension the reading does not touch. (The signal is the reading's own used-operand
units, which is always available — see §7 Q2: the question's asked-for unit is *not*
currently extracted, so the exemption must not depend on it.)

Crucially, a derivation that uses the exemption is **commit-ineligible**: it may
enter the candidate pool to *create disagreement*, but it may **never resolve as the
sole answer**. Committing still requires *full* completeness (every quantity used).
The exemption only ever buys a **refusal**, never an answer.

This is the load-bearing safety property: the completeness guarantee for *commits*
is untouched, so the multi-step-incomplete attempts ADR-0175 added it to catch (the
9→2 practice fix) still cannot commit. The exemption widens only what can *refuse*.

### 3b. Cross-composer candidate pooling

`select_self_verified` is invoked once over the **union** of candidates from all
composers (accumulation, in-clause multiplicative, target-guided chain) for a single
problem, rather than each composer resolving in isolation and the runner taking the
first non-`None`. Uniqueness/disagreement then operates across readings of
*different shapes*, which is where the real ambiguity lives.

Distractor-aware accumulation (3a's enabling reading): in a change clause that
carries >1 quantity, instead of refusing outright (current GB-3b.1 behavior),
accumulation may drop an **isolated-foreign** quantity and read the remaining
single same-unit change — producing the competing additive candidate. That
candidate is commit-ineligible (it left the foreign quantity unused), so it can only
force disagreement.

### Worked outcomes

| case | complete (commit-eligible) reading | exempt (refuse-only) reading | pool verdict |
|---|---|---|---|
| `0014` | product `300` | additive `25` (`3 hours` exempt) | disagree → **refuse** ✓ |
| `0016` | product `3840` | additive `12` — **requires anchor-skip** (see below) | disagree → **refuse** *(if anchor-skip)* |
| `0021` | product `450` | *none* (single clause, no anchor/change; no isolated-foreign) | unique → **commit** ✓ |
| `0003` | product `864` | *none* (no additive cue; no isolated-foreign) | unique → **commit** ✓ |

The legitimate products survive because they have **no competing reading** to
disagree with — exactly the property that distinguishes a real product from a
distractor, expressed structurally rather than by cue.

**0016 is the harder sub-case (honest accounting).** Its distractor occupies the
*anchor-position* clause ("A train travels 60 miles … for 2 hours" — two
foreign quantities), so the competing additive reading `8 + 4 = 12` is generated
only if **anchor selection** also skips an all-foreign leading clause, not just
foreign quantities inside a change clause. 0014's distractor sits in a change
clause, so it falls out of 3b directly. The implementation should treat anchor-skip
as a distinct, separately-tested step: **0014 is the guaranteed win (wrong 5→4); 0016
lands only when anchor-skip is built and validated (wrong →3).** Claiming both
before 0016's anchor-skip is proven would be the kind of overclaim the lookback
discipline exists to catch.

## 4. wrong=0 analysis (the obligations this spec must discharge before code)

1. **Commit path unchanged.** A derivation may resolve only under *full*
   completeness. The isolated-foreign exemption is strictly commit-ineligible.
   *Obligation:* a failing-under-violation test — flip the exemption to
   commit-eligible and a known multi-step-incomplete case must commit a wrong
   answer.
2. **Exemption is narrow.** "Isolated foreign" = unit non-empty ∧ not equal to any
   *used* operand's unit in the reading. A quantity sharing a unit with any used
   operand is **never** exempt (it is real signal); an empty-unit quantity is never
   exempt (it cannot be shown foreign). *Obligation:* a test where a same-unit
   "distractor" is *not* exempted and the reading stays complete-or-refused.
3. **Pooling cannot manufacture a new sole committer.** Pooling adds candidates;
   the hazard is that a newly-pooled *complete* reading becomes a unique committer
   on a case that previously refused. *Obligation:* re-run the full `train_sample`
   and practice lanes; `wrong` must stay 0 and `correct` must not drop. Any new
   commit must be inspected and gold-confirmed.
4. **Disagreement, not preference.** When complete and exempt readings disagree,
   the result is refusal — never "prefer the additive reading." The engine does not
   *know* 25 is right; it knows it has two incompatible readings.

## 5. Validation plan (the lanes that prove it)

- **Confuser probe:** `wrong` 5 → **4** (0014 refuses) from 3b alone; → **3** once
  anchor-skip lands 0016. pseudo-accumulation stays at 0 wrong (EX-6); genuine
  positives still solve; the pair-tell on 0014 (currently a tell) clears.
- **`train_sample` (capability):** `3/47/0` byte-identical — no new commit, no drop.
- **practice accumulation/search:** `wrong = 0` held; `correct` not reduced.
- **smoke + lane-SHA freeze:** green; serving untouched (sealed lane only).
- **Tightened baseline:** `_BASELINE_WRONG` 5 → 3 in
  `tests/test_adr_0163_f2_confusers.py`, plus a `test_distractor_quantity_refuses`
  obligation that fails loudly if pooling or the exemption regresses.

## 6. Scope boundaries (what this is *not*)

- **Not** a cue-precision fix. It does not learn which cues license multiplication;
  it sidesteps that by refusing the ambiguity. CP-2b
  ([ADR-0177](./ADR-0177-cue-precision-learning.md)) remains the path to *solving*
  (rather than refusing) distractor cases later.
- **Not** a completeness weakening for commits. Commits still require full
  completeness; only the *refusal* surface widens.
- **Not** a general distractor *detector*. "Isolated foreign unit" is a deliberately
  narrow, conservative structural signal; many distractors (same-unit ones) are out
  of scope and must continue to refuse via other means.
- **Sealed.** `chat/` does not import the derivation composers; serving `3/47/0`
  cannot move. This is practice/confuser-lane capability only, until a Phase-5
  ratification.

## 7. Open questions for review

1. **Where does pooling live?** A new `generate/derivation/pool.py` that owns the
   union + single `select_self_verified` call, with the confuser runner and practice
   runners delegating to it (so the "first non-`None`" ordering disappears and the
   two lanes cannot drift) — vs. threading a flag through each composer. The former
   is cleaner and removes the implicit composer-priority ordering; preferred.
2. **No asked-for-unit signal exists yet.** Verified during scoping: MS-1
   `extract_target` exposes `Target.units` as the **union of body unit-shapes**
   (`('pencils','hours')` for 0014, `('miles','hours','tickets')` for 0016) — *not*
   the unit the question asks for. Isolating the asked-for unit ("pencils" from "How
   many pencils") would need a question-head-noun parse that does not exist (and is
   out of scope here). The exemption is therefore defined **relative to a reading's
   used-operand units** (always available), not an asked unit. If a question-unit
   parse later lands, it becomes an *additional* tightening, never a prerequisite.
3. **Interaction with the deferred slash-fraction leak**
   ([ADR-0179 EX hazard pin](./ADR-0179-extraction-richness.md)). A fraction-operand
   PR will change which quantities exist; sequence pooling and fraction support so
   their completeness interactions are validated together, not pairwise-blind.
