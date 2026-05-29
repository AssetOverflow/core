# Session 2026-05-29 (pt. 2) — Comprehension chaining, and the overfitting course-correction

**Status:** paused (clean). Continues
[SESSION-2026-05-29 — the multi-step build arc](./SESSION-2026-05-29-multistep-build-arc.md).
**Headline:** Reconciled a wave of remote/operator work, built the cue-precision
ledger + its measurement, shipped the first real *comprehension* reading
(single-referent accumulation), then — prompted by a timely caution — proved that
the synthetic corpus was over-rewarding surface matching, tore down the overfit
work, and built a **confuser corpus** that scores refusal instead of flips.

`serving stayed 3/47/0 byte-identical the entire session.`

---

## TL;DR

1. **Reconciled the remote/ChatGPT extraction work** — integrated EX-1/EX-4/EX-5
   into one coherent extractor (#455), merged the GB-1/GB-2 audit (#450), fixed a
   stale decimal test, closed the superseded/off-brief PRs, and verified+merged the
   parallel operator PRs (CP-1 #458, Track-B scale #459, Track-C EX-3 deferral #460).
2. **GB-3a referent guard** (#456) — the mandated lookback proved the GB-2 hazards
   H1/H2/H3 were *live*; clause-scoped the composer so multi-clause/referent sums
   refuse. The ADR-0174 multi-actor hazard's defensive fix, finally built.
3. **CP-2a cue-precision training + measurement** (#461, + the function-word unit
   filter) — and the load-bearing finding: **no cue is reliable yet** (every pattern
   floors at ~0.0), so CP-2b (trust) is blocked on *candidate generation*, not the
   ledger. Cue-precision and structure are coupled; structure comes first.
4. **GB-3b.1 accumulation** (#464 scope, #465 impl) — the first cross-clause
   comprehension reading (`Sam has 14. He buys 9 more.` → 23). Practice additive
   lane **0 → 55 correct, 0 new wrong**.
5. **The course-correction** — GB-3b.2 (multi-change + vocab growth) reached 96/150
   synthetic but **1/50 on real GSM8K, +1 wrong** (the 0002 cable/fraction problem
   read as accumulation → 996). Recognised as overfitting, **torn down unshipped**,
   lesson recorded in memory.
6. **Confuser corpus** (#468 spec, #471 corpus) — a discrimination probe scored the
   opposite way: `wrong → 0` + pair-consistency, not flip-count. Baseline surfaced
   **7 real defects + 4 surface-match tells** the templated lane had hidden.

---

## The arc, and why each step happened

### Reconciliation (the cost of a contested working tree)

The session opened reviewing remote ChatGPT work. The four EX PRs each rewrote the
same `extract.py` off `main`, so they conflicted pairwise — integration, not merge.
EX-3 was **deferred** (its greedy multi-word unit regresses GB-2 and, on the redo,
hits a *second* trap — postmodifier adjectives like `25 years old`). EX-4's "unblocks
0024" claim was a fabricated-input overclaim; its own audit (#450) admitted 0024
stays blocked. Lesson reinforced: **design against the real corpus, not paraphrases.**

A mid-session hazard: multiple operators (and Claude) ran `git` in the *same*
working directory, which silently wiped uncommitted work. Recovered everything
(it was all in PRs); adopted **dedicated worktrees** for the rest of the session.

### The measurement that set the route

CP-2a trained the CP-1 ledger over 200 sealed cases and reported per-pattern
reliability. Every `(cue, op, unit_shape)` floored at ~0.0 — the blunt search's
readings are almost always wrong vs gold, so the conservative floor correctly trusts
nothing. **This is the microscope working:** it said the lever is not "trust good
cues" (there are none) but "make the readings less crude" → GB-3b structure first.

### The first real comprehension flip — and its honest ceiling

GB-3b.1 reads single-referent accumulation: anchor on the actor's quantity, apply a
grounded `±M` per change clause (`buys`/`more` → +, `gives…to`/`eats` → −), refuse on
a new named actor (the H1 hazard) or ambiguous polarity. Practice additive: **0 → 55
correct, 0 new wrong.** Honest calibration recorded at the time: those 55 are
*curated* cases; `train_sample` (real GSM8K) is the hard bar (48/50 multi-step mixed).

### The course-correction (the most important part)

Pushing GB-3b.2 (multi-change + reactive verb-vocab) reached 96/150 — but the
generalisation check told the truth: **real GSM8K moved 1/50, with a new wrong.**
`train_sample-0002` ("buys 1000 feet… splits into 25-foot sections… gives 1/4 away…")
was read as `buys…gives` accumulation → **996** (gold 15). The synthetic corpus was
rewarding surface-cue matching. Per the user's caution, GB-3b.2 was **torn down**,
and the lesson written to memory (`feedback-synthetic-corpus-overfitting-trap`):

> Positive+negative samples are the ledger's fuel — but only from a *general* reader
> on a *diverse* corpus. Correct-because-genuinely-read = signal;
> correct-because-the-rule-was-fit-to-it = noise. Track-B's templates have no hard
> negatives, so they can't teach refusal and they tempt fitting the reader to them.

### The confuser corpus (the cure)

Built the missing half: ~30 hand-curated, real-sourced cases across the proven
misfire categories (disguised-polarity, pseudo-accumulation/fractions, multi-referent,
multi-actor-pronoun, distractor-quantity, temporal-scope, comparative-referent,
unit-confuser) + genuine-positive minimal-pair twins. Scored **opposite** to a
coverage lane: the bar is `wrong → 0` (answering a confuser is a defect regardless
of value) + **pair-consistency** (solving a twin but answering its confuser = a
surface-matching tell). Baseline: `7 solved / 15 refused / 7 WRONG / 1 spurious`,
4 pair-tells. The 7 wrong are the sealed-composer defects the synthetic flips hid —
now named and **pinned as a no-regression gate** (never reactively patched).

---

## Shipped this session (all serving `3/47/0` byte-identical, lane-SHA 8/8)

| PR | What |
|----|------|
| #455 | Reconcile EX-1/EX-4/EX-5 into one extractor (+ stale-test fix) |
| #450 | GB-1/GB-2 lookback audit (merged) |
| #456 | GB-3a clause-scoped referent guard (H1/H2/H3 refuse) |
| #458 | CP-1 cue-precision ledger substrate (inert) |
| #459 | Track-B: 150 additive practice cases |
| #460 | Track-C: EX-3 second-deferral pin |
| #461 | CP-2a ledger training + measurement + function-word unit filter |
| #464 / #465 | GB-3b scope + GB-3b.1 accumulation (practice 0→55) |
| #468 / #471 | Confuser corpus spec + corpus v1 (baseline: 7 defects surfaced) |

**Torn down unshipped:** GB-3b.2 (overfit multi-change/vocab).
**New substrate on main:** `core/reliability_gate/`, `generate/cue_precision/`,
`generate/derivation/{accumulate,compose,clauses,…}`, `evals/gsm8k_math/{practice,confusers}/`.

## The honest frontier (next, when resumed)

`train_sample` (real GSM8K) is the only capability metric; the synthetic lanes are
mechanism-demos. The confuser baseline names the defects, and the fixes are
**general mechanisms, not reactive patches**, each validated on `train_sample` +
the probe (`wrong` must drop, never rise):

- **extraction completeness** — the gate must *see* the fractions/`25-foot`/distractor
  it currently misses, so pseudo-accumulation & distractor cases refuse (the same
  lever behind 0002→996). Highest leverage.
- **question-time reading** (temporal-scope / H3).
- **referent binding** (comparative-referent / H2, multi-referent).
- **CP-2b** only after the above give the ledger reliable cues to trust.

## Discipline notes (durable)

- Serving wrong=0 is sacrosanct; all new readers are *sealed* until a Phase-5
  ratification. Progress shows as practice `correct` rising with `wrong` at 0.
- Synthetic flip-counts are not capability. Measure on real GSM8K; reward refusal.
- Dedicated worktrees for concurrent work; never two operators in one checkout.
