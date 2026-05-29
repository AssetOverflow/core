# ADR-0178 GB-3b — referent-aware accumulation chaining (scope)

**Status:** Proposed (scope only — no code). Sub-phase of
[ADR-0178](./ADR-0178-compositional-structure.md) Gap B. Builds on the GB-3a
referent guard (PR #456) and the CP-2a measurement (PR #461).

> **One-line thesis.** The first cross-clause reading that produces *flips in a
> chunk* and is genuinely "comprehension": a single actor's quantity changes over
> successive clauses (`X has N. He buys M more.` → `N + M`). The win is gated by a
> tight referent + change-cue model so the Alice/Bob hazard still refuses.

---

## 1. The measured opportunity (why this is the next move, not a guess)

Run on the 200 sealed cases (50 `train_sample` + 150 ADR-0163-F additive practice),
deterministic:

| lane | single product/sum == gold | needs multi-step |
|------|---------------------------:|-----------------:|
| `train_sample` | 2 / 50 | 48 |
| `practice-additive` | **46 / 150 (`sum-of-all == gold`)** | — |

All **46** additive cases are the *same shape* and **all currently refuse**
(`practice` lane solves `0/150`). Inspected, every one is **single-referent
accumulation**:

```
Sam has 14 apples. He buys 9 more. How many apples does Sam have now?   -> 14 + 9 = 23
Lisa has 30 coins. She earns 15 more by doing chores. How many...?      -> 30 + 15 = 45
Kate has 18 pencils. Her teacher gives her 5 more. How many...?         -> 18 + 5 = 23
```

The CP-2a measurement (PR #461) showed **no cue is reliable** because the blunt
search's readings are crude. GB-3b is the *better candidate generation* that
measurement said was the real lever — and the 46 cases are the concrete, gold-
verified chunk it should flip. The subtract analog (`has N`, `gives/loses/uses M`)
is the same shape and adds a comparable second chunk.

## 2. Why they refuse now — and why that is *correct*

GB-3a made `compose_sequential` refuse **all** multi-clause same-unit aggregation,
to kill the referent hazards H1/H2/H3 (`Alice has 6 apples. Tom has 2 apples.` must
not sum to Alice's total). These 46 cases **are multi-clause**, so GB-3a refuses
them — correctly, given what it can currently see.

The difference between a **safe** accumulation and the **hazard** is exactly two
readable things:

| | clause 2 | safe? |
|---|---|---|
| accumulation | `He buys 9 more` — *same actor* (pronoun), *change verb* | ✅ `+9` |
| hazard (H1) | `Tom has 2 apples` — *new actor*, no change verb | ❌ refuse |

GB-3b adds precisely this discrimination: **chain across clauses iff (same
referent) ∧ (a licensed change cue); otherwise refuse.** It *generalises* GB-3a
(refuse-all-multi-clause → chain-when-licensed-else-refuse), it does not weaken it.

## 3. The reading GB-3b adds

1. **Anchor.** The running total is clause 1's resolved GB-1 leaf: `(actor, N, unit)`.
2. **Change steps.** Each later clause that (a) is **same-referent** and (b) carries
   a **change cue** applies `± M` to the running total, where `M` is that clause's
   grounded quantity. Op + polarity come from the cue lexeme; the operand from the
   clause's text quantity; the order from clause order.
3. **Gate.** The constructed chain runs through the unchanged self-verification gate
   (grounding ∧ cue ∧ unit ∧ completeness ∧ uniqueness). The gate already keeps
   wrong=0; GB-3b only proposes a *structurally licensed* candidate for it to verify.

**Closed change-cue lexeme sets** (ADR-0165-safe — lexemes, not grammar templates;
refined by the CP ledger, not asserted complete):

- **GAIN (`+`)**: `buys, bought, gets, gments?` → `gets, got, receives, received,
  finds, found, earns, earned, adds, added, gains, gained, makes, made, picks, more`
- **LOSS (`−`)**: `gives, gave, loses, lost, spends, spent, uses, used, eats, ate,
  sells, sold, drops, dropped, removes, removed, fewer, less`

(Final sets curated against the corpus; an unknown change verb → refuse, never guess.)

## 4. Referent model (wrong=0-critical) — cross-reference + decision

**Prior art (must not reinvent):** `ADR-0164.2` (pronoun-entity-resolution),
`ADR-0164.3` (cross-sentence-state), and `ADR-0174` (`PronounResolution` in
`generate/math_candidate_graph.py`, with the **multi-actor pronoun hazard** —
gender-blind most-recent-antecedent — recorded in memory
`project-adr-0174-multi-actor-pronoun-hazard`). That comprehension subsystem is
heavyweight, **did not move GSM8K scoring**, and was partly retired (`generate/
comprehension/lifecycle.py` is dual-use/inert in scoring per `project-lifecycle-
reader-dual-use`).

**Decision:** GB-3b builds a **minimal, refuse-preferring referent guard in the
derivation lane** — it does **not** resurrect the retired reader and does **not**
reuse the gender-blind antecedent resolver (itself a hazard). Rationale: the clean
derivation lane is what has been making progress; the old resolver's failure mode
is exactly the multi-actor confusion we must refuse on.

**The guard (lexeme/orthographic-anchored):**

- Clause 1's **subject** = its leading proper noun (a capitalised token that is not
  sentence-initial-only) or pronoun.
- A later clause is **same-referent** iff it introduces **no new proper-noun actor**
  — i.e. it continues via a pronoun (`He/She/They/Her/His`) or states no new named
  subject.
- If a later clause introduces a **different** proper-noun actor → **multi-actor →
  refuse** (defensive; this is the ADR-0174 hazard's required fix, finally built).

This is deliberately conservative: it refuses on any referent ambiguity rather than
resolving it. Pronoun *gender/number* matching is **not** attempted (that was the
old resolver's trap); "a new name appeared" is the only signal, and it triggers
refusal, not resolution.

## 5. wrong=0 obligations (must be *proven*, not asserted)

A test must **fail** if any of these is violated (CLAUDE.md proof-obligation rule):

1. **Grounded + cue-licensed + unit-consistent** change steps (the existing gate).
2. **Multi-actor → refuse.** H1 (`Alice … Tom …`) stays `None`. A new proper-noun
   subject in any clause refuses the whole chain.
3. **No change cue → refuse.** Two clauses with quantities but no gain/loss lexeme
   do not get summed (no implicit aggregation).
4. **Ambiguous polarity → refuse.** A clause carrying both a gain and a loss lexeme,
   or an unknown verb where a change is implied, refuses.
5. **Comparative bound elsewhere (H2) → refuse**; **question-temporal-scope (H3,
   "how many before giving any away") → refuse** (handling "before/after" question
   scoping is deferred to a later increment; until then it must refuse, never apply
   the change blindly).
6. **Determinism**, **seal** (no `chat/` import), **serving `3/47/0`** byte-identical
   (sealed substrate until a Phase-5 ratification, as with GB-3a/CP).

## 6. Cue-precision coupling (this is what closes the CP-2a loop)

CP-2a measured every existing cue at ~0.0 reliability. The change cues GB-3b
introduces are structurally different: `buys` **always** adds, `gives` **always**
subtracts — they should record **high** reliability in the CP ledger once GB-3b's
candidates are trained through CP-2a. **GB-3b is the phase that finally produces a
reliable cue pattern**, which is the prerequisite CP-2b (trust) was blocked on.
The two tracks compound here: structure produces clean readings → cue-precision
finds signal → trust becomes possible.

## 7. Increments (one PR each, sealed, measured gold-checked)

- **GB-3b.1 — single-referent gain/loss accumulation.** The anchor + one-or-more
  change steps + the minimal referent guard (incl. pronoun-continuation, since the
  46 use `He/She`). Flips the 46 additive `+` cases and the subtract analog.
  **This is the chunk.**
- **GB-3b.2 — multi-step / mixed accumulation.** 3+ changes, gain and loss in one
  problem; running total across several clauses.
- **GB-3b.3 — question-temporal scope.** "before/after he gave any away" — refuse-
  aware reading of the *question's* time reference (closes H3 properly).

## 8. Honest flip expectation (so we are not surprised)

- **Big chunk in `practice-additive`**: GB-3b.1 should take the additive lane from
  `0` correct toward `~46` (the `+` cases) and, with the subtract analog, a
  comparable additional set — the first time the comprehension reading visibly
  *works at scale*. **This is the progress signal**, measured and gold-checked.
- **Modest in `train_sample`**: real GSM8K skews to multi-step *mixed*-operation
  problems (48/50 need >1 op); single-referent accumulation will flip only the few
  that are pure accumulation. GB-3b is the **foundational primitive** the multi-step
  work composes on, not a one-shot GSM8K solve.
- **Serving stays `3/47/0`** (sealed). Progress shows as practice `correct` rising
  with `wrong` held at 0 (or eliminations only) — the two-regime contract.

## 9. Acceptance (Proposed → Accepted)

1. GB-3b.1 lands; the 46 `+` cases (and the subtract analog) flip to `correct` in
   the practice lane under self-verification; `wrong` does not rise; serving frozen.
2. The §5 obligations each have a test that fails under the violation (multi-actor
   admitted, unlicensed/absent change summed, wrong polarity, H1/H2/H3).
3. Change cues record measurable reliability in the CP ledger (CP-2a report),
   demonstrating the structure→precision coupling of §6.
4. Determinism/seal invariants hold; the GB-3a hazards H1/H2/H3 remain refused.
