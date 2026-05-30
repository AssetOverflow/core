# ADR-0191 — Candidate-graph completeness guard (the missing wrong=0 leg)

**Status:** Proposed (implemented in this PR). Hardens the
[ADR-0123](./ADR-0123-candidate-graph-reader.md) candidate-graph reader's
admissibility gate. Serving-path firewall fix; landed wrong=0-proven on
the **full real GSM8K train split**, not just the 47-case sample.

> **One line.** The candidate-graph reader checked *grounding* and
> *round-trip* but had **no completeness obligation**, so a problem whose
> later clauses failed to parse still emitted whatever partial graph
> remained. Over the full 7,473-question real GSM8K train split this
> confabulated **5 answers** (wrong≠0). This adds the completeness leg the
> derivation reader's `verify.py` already has: every source quantity must be
> consumed by the chosen reading, else refuse. Result: real-corpus
> **wrong 5 → 0**; `train_sample` byte-identical **4/46/0**.

---

## 1. The gap (full-corpus microscope finding, 2026-05-30)

The 47-case `train_sample` reports wrong=0. Running the **canonical serving
reader** (`generate.math_candidate_graph.parse_and_solve`) over the *entire*
real GSM8K train split (7,473 questions) revealed the sample was hiding a
firewall breach:

```
correct 4 · wrong 5 · refused 7,464      (origin/main @ #488)
```

The 5 confabulations (deterministic, 3× reproduced):

| idx | problem (abridged) | reader | gold |
|----:|--------------------|-------:|-----:|
| 553 | Emma buys 2/school-day … in 3 weeks? | 2 | 30 |
| 605 | Ivan 20 dice; Jerry twice as many; altogether? | 20 | 60 |
| 693 | Ian 20 roses; gave 6/9/4; kept rest? | 20 | 1 |
| 6172| Jimmy 18 cards; gives 3; Mary twice that; left? | 15 | 9 |
| 7369| Wilfred 4 Tue, 6 Wed; total 15 Tue–Thu; Thu? | -4 | 5 |

Two of these (693, 7369) were **regressions introduced by #488** (ADR-0189/0189a):
they refused correctly before that PR and confabulated after. The 47-case gate
could not see it — exactly the lookback hazard CLAUDE.md §Lookback Review warns
about.

**Root cause — one structural hole, not five anecdotes.** A graph is admitted
when its *present* elements ground and round-trip. Nothing checks that every
question-relevant source quantity is *represented*. When later clauses fail to
parse into operations, the residual partial graph still solves and is emitted:

- `605` builds `initial=(Ivan:20), operations=()` — a zero-operation graph
  answering "altogether"; the "twice as many" and the aggregate vanished.
- `693` the "He gave …" subtractions don't bind to "Ian" (live ADR-0174
  pronoun hazard) and 2 of 3 are dropped → bare initial survives.

The derivation reader already refuses this (`verify.py`: grounding ∧ cue ∧
unit ∧ **completeness** ∧ uniqueness). The candidate-graph reader was missing
the completeness leg.

## 2. Decision

Add a **completeness guard** as the final admissibility check in
`parse_and_solve`, in a dedicated module `generate/math_completeness.py`:

> Collect every numeric / multiplier quantity in the source (all statement
> sentences **before** the numeric-only filter, plus the question). Collect
> every quantity the chosen reading actually **consumed** (candidate
> provenance). If a source quantity is not consumed, the reading is
> incomplete → **refuse**.

```text
uncovered = quantity_values(all_statements + question) − consumed_values(chosen_branch)
if uncovered:  refuse("incomplete reading: …")
```

### Why this preserves wrong=0 and cannot regress

- **Refusal-only.** The guard only ever flips an *emitted answer* to a
  *refusal*. It can never invent an answer, so it can only remove wrong
  answers — never create one. Its entire regression surface is the
  graph-path *correct* set, which is exactly `{train_sample 0024}` /
  `{real-train 3343}` (the same Sidney/Brooke day-enum + comparative shape).
  Both still solve (438).
- **Set semantics, not multiset.** `required − consumed` over value SETS
  tolerates a quantity echoed in the question (no false refusal) while still
  catching a clause whose distinct quantity was dropped — which is what every
  observed confabulation does.
- **Short-circuits are immune.** Capacity / earnings / conditional / embedded
  short-circuits return before the graph decision rule, so the guard never
  touches them.

### Pack-authoritative number-sense (no hand-rolled lexicon)

Both the *required* scan and the *consumed* normalization resolve quantities
through the `en_numerics_v1` pack and the parser's own `_resolve_value`, so
identical surface forms cancel exactly and the guard never disagrees with the
engine about what a number is:

- Compound cardinals via `parse_compound_cardinal` (`one hundred` → 100,
  `two thousand five hundred` → 2500, `twenty-five` → 25).
- Multiplier anchors via `lookup_multiplier` — **read from the pack, not
  hardcoded**, so the guard automatically covers `twice, thrice, half,
  double, triple, quadruple, quintuple` and excludes ordinal-ambiguous
  `third` / `quarter` (which are not multipliers in the pack).
- All six currency symbols (`$ ¢ € £ ¥ ₱`) tokenize as whole spans.

### Provenance for aggregating extractors

Aggregating initials collapse several source tokens into one derived value, so
they now expose every consumed token via a new
`CandidateInitial.consumed_value_tokens` field (default `()` → falls back to
`matched_value_token`, preserving all existing behavior):

- day-enumeration → every per-day count;
- embedded-quantifier → both `N` and `M` of `N×M`;
- conjoined-embedded → all four factors;
- multi-word cardinal → the full phrase.

## 3. Evidence

- **Real GSM8K train (7,473):** wrong **5 → 0**; correct held at 4. Firewall
  HOLDS. The 5 confabulations now refuse with `incomplete reading: …`.
- **`train_sample` (official metric):** byte-identical **4/46/0**, set
  `{0014, 0018, 0024, 0042}`.
- **Capability axes:** G1–G5 + S1 + numerics extensions (G3.1) all green; the
  first guard draft over-refused 20 G3 numerics cases (currency/decimal/
  hyphenated/compound-cardinal mis-parse) — fixed by making the number-sense
  pack-authoritative. Two pre-existing failures
  (`test_committed_report_matches_fresh_run`, `test_full_session_round_trips`)
  fail identically on `origin/main` and are unrelated.
- **Smoke suite:** 67 passed.
- **Pinned serving lanes:** `math_teaching_corpus_v1` report byte-identical;
  no pinned lane exercises `parse_and_solve`.
- **New tests:** `tests/test_candidate_graph_completeness_guard.py` (5
  confabulations refuse; Sidney/Brooke still solves; refusal-only invariant).

## 4. Consequences

- The candidate-graph reader now refuses partial readings instead of
  confabulating — the wrong=0 firewall holds on real data, not just the
  sample. This is the prerequisite for any further capability work: a flip is
  only real if it does not also widen the confabulation surface.
- The guard makes some genuinely-incomplete shapes refuse that previously
  emitted a (wrong) answer. That is the point. It never blocks a *complete*
  reading; once a future capability consumes the dropped quantity, coverage is
  satisfied and the case admits.
- **Limitation (documented, not load-bearing):** fraction *words* beyond the
  multiplier set (e.g. `two-thirds`) are not yet recognized as required
  quantities; this is conservative (can only under-refuse, never confabulate)
  and is future work when a fraction capability lands.

## 5. Follow-ups

- Re-run the full-corpus microscope after each future capability PR as a
  standing wrong=0 regression check (not just `train_sample`).
- The 693 confabulation also exposed the live ADR-0174 multi-actor pronoun
  hazard; the completeness guard now refuses it, but the pronoun-binding fix
  remains the proper long-term resolution.
