# Phase 3.1 Follow-up — Verb-coverage bottleneck on train_sample/v1

**Status:** Open recommendation
**Date:** 2026-05-28
**Author:** Shay (analysis surfaced during ADR-0174 Phase 3a)
**Parent:** [ADR-0174 — Held-Hypothesis Comprehension](../decisions/ADR-0174-held-hypothesis-comprehension.md)
**Related ADRs:** ADR-0163 (path to GSM8K mastery), ADR-0167 (audit-as-teaching-evidence), ADR-0150/0152/0155/0161 (HITL corridor)

---

## Context

ADR-0174 Phase 3 specified a `correct ≥ 8` lift target on
`evals/gsm8k_math/train_sample/v1` (≥ 5 of the 21 currently-empty
`discrete_count_statement` anchors admitted via lookback). Empirical
analysis during Phase 3a implementation found this target is
**not achievable through lookback alone** on this corpus. The
substrate is built correctly; the bottleneck is elsewhere.

## What Phase 3a shipped

- `generate/comprehension/lookback.py` — the `reevaluate` operator,
  `PronounResolution` refinement type, `ReevaluateResult` dataclass.
- Held-anchor emission in `recognizer_match._try_extract_discrete_count_anchor`
  (pronoun-subject statements carry `requires_pronoun_resolution=True`
  rather than refusing).
- Lookback wiring at `math_candidate_graph.parse_and_solve`'s
  recognizer-injection branch — applies `PronounResolution` against
  the existing `_discourse_prior_subjects` map; emits `lookback` JSON
  trace events with `outcome ∈ {admitted, eliminated, no_antecedent}`.
- 17 acceptance tests proving the wiring works on synthetic problems
  (`tests/test_adr_0174_phase3_lookback.py`).
- `wrong = 0` invariant preserved; score unchanged at 3/47/0.

## Why Phase 3a did not lift the score

The 21 empty-anchor `discrete_count_statement` refusals on
train_sample/v1 break down as:

| Structural cause | Cases |
|---|---|
| Pronoun-only (no compound clause) | 2 — 0002, 0034 |
| Compound-only | 8 |
| Pronoun + compound | 5 |
| Other narrowness fail (verb/structure) | 6 |

For Phase 3a to lift any case, **three conditions** must all hold:

1. The matcher's recognizer registry recognises the statement.
2. The extractor passes every narrowness layer **before** the pronoun
   check.  Specifically the verb must be in `_POSSESSION_VERBS` (`has`,
   `have`, `had`) or `_ACQUISITION_VERBS` (`collected`, `collects`,
   `collect`, `received`, `receives`, `receive`, `bought`, `buys`,
   `buy`, `got`, `gets`, `get`).
3. The candidate-graph's regex path (`_filtered_statement_choices`)
   must return empty for the same statement — otherwise the regex
   path commits the candidate (with the pronoun still as actor) and
   the recognizer-injection branch never runs.

Verb checks against the 13 cases with compound/pronoun structure:

| Case | Statement (excerpt) | Verb | In whitelist? |
|---|---|---|---|
| 0002 | She **splits** it up... | splits | No |
| 0034 | He can **run** 40 yards... | run | No |
| 0020 | Two puppies, two kittens... **were for sale**... | were | No |
| 0021 | He **bench presses** 15 pounds... | presses | No |
| 0027 | Malcolm **has** 240 followers... | has | **Yes** |
| 0033 | Rachel **is** 12 years old... | is | No |
| 0040 | He now **has** 2 horses... | has | **Yes** |
| 0041 | Troy **bakes** 2 pans... | bakes | No |
| 0044 | John **invests** in a bank... | invests | No |
| 0045 | On Monday he **finished** 3 surveys... | finished | No |
| 0047 | John **bakes** 12 coconut macaroons... | bakes | No |
| ... | | | |

Only **two** cases (0027, 0040) cross the verb whitelist. Both also
fail at the compound-clause narrowness layer (which comes earlier
than the pronoun check), so even adding compound-clause held
hypotheses (Phase 3b) would have to fire first.

**Conclusion:** the empirical bottleneck on train_sample/v1 is
**verb-set coverage**, not lookback or held hypotheses. ADR-0174 is
the wrong tool for moving this score.

## Recommended path forward

ADR-0163 is the correct scope for verb-coverage expansion via the
HITL corridor. The path:

1. **Run `core eval math-contemplation` on the 11 failing verbs** —
   `splits`, `run`, `bench presses`, `is`, `bakes`, `invests`,
   `finished`, `donated`, `wants`, `gained`, `eat`. These surface as
   `MathReaderRefusalEvidence` audit rows that the contemplation lane
   already consumes (ADR-0167).
2. **Operator review in workbench** — categorise each verb:
   - Acquisition-class (engine should treat as `add`): `received`,
     `bought`, etc. — verbs that grammatically gain quantity to actor.
     Candidates from list: `gained`, `won`, `earned`, `saved`,
     `accumulated`, `acquired`.
   - Depletion-class (engine should treat as `subtract`): `gives`,
     `loses`, `spends`. Candidates: `donated`, `gave`, `eats`,
     `consumed`, `lost`, `spent`.
   - Non-arithmetic verbs (engine should refuse and ask): `is`,
     `wants`, `bench presses`, `splits`, `run`, `bakes`, `invests`.
     These do not carry possession/acquisition semantics; the right
     answer is a different intent (rate / capacity / descriptive),
     not a wider `add`/`subtract` whitelist.

   The first two classes ratify into the registry via the existing
   ADR-0150/0152 corridor (proposal → review → packed). The third
   class becomes refusal-typed evidence that informs whether a
   separate recognizer category is needed (e.g. a `capacity_statement`
   recognizer for "He can run 40 yards in 5 seconds" rather than
   forcing it into `discrete_count_statement`).

3. **After verb widening lands** — re-run Phase 3a's lookback wiring
   on the corpus. The cases that were previously verb-blocked now
   reach the pronoun-check layer, and the held-hypothesis path admits
   them. Expected lift from this combination: roughly the 13 cases
   with pronoun/compound structure that have an arithmetic-class verb
   under the widened whitelist.

## What this means for ADR-0174

The held-hypothesis substrate (Phase 1 + 2 + 3a) is correct
architecture and load-bearing for Phase 4 (in-loop contemplation) and
Phase 5 (legacy-parser removal).  Its **eval impact** depends on
upstream recognizer coverage maturing through the ADR-0163.x
corridor.  These two efforts are complementary, not competing — the
substrate makes lookback possible, the recognizer expansion gives
lookback something to fire on.

The cleanest sequencing is:

1. **ADR-0174 Phase 3a (this PR)** — substrate landed.
2. **ADR-0163.x verb expansion** (this brief's recommendation) —
   widens the corpus surface that the substrate can act on.
3. **ADR-0174 Phase 3b** — compound-clause held hypotheses. Once the
   verb-coverage bottleneck is gone, compound-clause expansion
   surfaces real cases. Currently it would surface zero on
   train_sample for the same reason Phase 3a does: most compound
   cases also fail the verb check before reaching the clause-split
   narrowness layer.
4. **ADR-0174 Phase 4** — in-loop contemplation. Builds on Phase 3
   substrate.
5. **ADR-0174 Phase 5** — legacy parser removal.

## Decision needed (from operator)

- **Authorise the ADR-0163.x verb-expansion contemplation pass?**
  Concretely: run `core eval math-contemplation` against the 11
  failing verbs above; review the proposals in workbench; ratify
  acquisition/depletion entries that are unambiguous.

- **Re-scope ADR-0174 Phase 3b** to "post-recognizer-expansion
  re-measurement" rather than "compound-clause held hypotheses"?
  Phase 3b should land only after verb expansion exposes cases that
  exercise its compound-clause logic.

No timelines are proposed; this is a sequencing recommendation. The
substrate work in Phase 3a is already merged on its own merits
(correctness and Phase 4/5 prerequisite); Phase 3b waits on
recognizer coverage.

## Cross-references

- ADR-0174 §Phase 3 acceptance — the criteria this brief documents
  as unmet (with structural-cause analysis).
- `tests/test_adr_0174_phase3_lookback.py` — proves the substrate
  works on synthetic problems even though no train_sample case
  exercises it.
- `feedback-wrong-zero-hazard-case-0050` memory — verb expansion
  must preserve the case-0050 canary; the recommended depletion-class
  additions should be reviewed against this hazard before ratification.
- `thesis-decoding-not-generating` — the verb-class
  contemplation/HITL path is the right "teach the engine to find
  better" mechanism; widening the static whitelist directly would be
  "storing another found thing."
