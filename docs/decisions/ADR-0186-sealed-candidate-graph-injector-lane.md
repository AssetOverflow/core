# ADR-0186 — Sealed candidate-graph injector lane: resume ADR-0170 W2–W5 under the ADR-0175 seal

**Status:** Proposed (scoping + seal-mechanism ADR; first injector ships behind the seal)
**Date:** 2026-05-29
**Parent / resumes:** [ADR-0170](./ADR-0170-injector-contract-widening.md) (the W1–W5 injector roadmap; W1 type-widening shipped, W2–W5 are scoped-but-unbuilt go/no-go follow-ups)
**Governed by:** [ADR-0175](./ADR-0175-calibrated-attempt-and-eliminate-learning.md) (the serving/sealed two-regime doctrine + the Phase-5 ratification bridge)
**Gating:** [ADR-0166](./ADR-0166-measurement-capability-sequencing.md)
**Cue discipline:** [ADR-0165](./ADR-0165-regex-scope-rule.md)

---

## 1. The microscope finding that motivates this (and corrects a session-long misframe)

A topology audit (2026-05-29) established that the GSM8K substrate has **two
structurally disjoint readers**, sharing only a tokenizer (`_tokens`,
`WORD_NUMBERS`, `_value_grounds` from `generate/math_roundtrip`) — no shared
recognizer, solver, problem-graph, or injectors:

| | **candidate-graph reader** | **derivation reader** (`resolve_pooled`) |
|---|---|---|
| Owns the official metric? | **Yes** — `_score_one_candidate_graph` produces `3/47/0` | No — called only by the confuser runner + tests |
| `train_sample` score | **3 / 47 / 0** (wrong = 0) | 2 / 8 / 40 (wrong = 8) |
| Arithmetic | divide, multiply, add, subtract, `compare_additive`, `Rate` | add + multiply only |
| Status | **frozen serving** ("stays `3/47/0` until ratified") | sealed practice (ADR-0175) |

Three consequences this ADR acts on:

1. **The recent ADR-0182/0184/0185 work matured the derivation reader — which does
   not feed the goal metric.** It is real work on the *sealed comprehension* organ,
   but it moves nothing on official GSM8K, and it cannot until an ADR-0175 Phase-5
   bridge exists.
2. **The goal organ already has the arithmetic.** ADR-0185's premise ("the engine
   cannot divide") is true only of the derivation reader. The candidate-graph reader
   *already* divides, multiplies, and does comparative arithmetic. Adding a division
   *reading* to `generate/derivation/*` cannot move `3/47/0`.
3. **The goal organ's wall is injection coverage + multi-statement composition, not
   arithmetic.** All 47 refusals are at the recognizer→graph boundary: *"recognizer
   matched but produced no injection"* (35) or *"no admissible candidate"* (12). The
   capable solver downstream is never fed.

### 1.1 The 47 refusals, by first-blocking category

| category | n | injector status (per ADR-0170) |
|---|---|---|
| `discrete_count_statement` | 20 | injector EXISTS; refuses these because the statement carries *additional* structure (comparative, multi-count, percentage, partition) — mostly genuine composition, not a leaf gap |
| (no category — "no admissible candidate") | 12 | deep structural (fraction-of-fraction, multi-clause comparative) |
| `descriptive_setup_no_quantity` | 4 | **by design** (no quantity to inject) |
| `rate_with_currency` | 3 | **no injector** — needs `CandidateRate` (the planned `SentenceChoice` union extension, ADR-0170 §Open-Q4, not yet written) |
| `multiplicative_aggregation` | 3 | WAVE-A injector exists, narrows by anchor kind |
| `currency_amount` | 3 | **no injector** — `CandidateInitial`-shaped (ADR-0170 W3) |
| `temporal_aggregation` | 2 | **no injector** — needs `apply_rate` primitive (ADR-0170 W5) |

This is precisely the ADR-0170 W2–W5 backlog. **We are resuming a roadmap the project
already scoped, not inventing one** (ADR cross-reference discipline).

### 1.2 Honest scope — one injector does not solve a case

A per-statement instrumentation probe was **rejected as unreliable**: a standalone
`recognizer_match.match(s)` returns `NO_MATCH` for statements the real loop classifies,
because the live loop feeds `prior_subject` + the ratified registry that the standalone
call lacks. So **no claim is made about which single injector flips which case.** The
refusals are dominated by multi-statement composition; a leaf injector is *necessary
groundwork* whose first effect is **elimination** (grounding a previously-unread
quantity), with **solves arriving only when a case's full statement set + question all
inject and compose.** Claiming a single injector flips N cases would be the overfitting
trap ([[feedback-synthetic-corpus-overfitting-trap]]).

## 2. The tension this ADR resolves

ADR-0170 (2026-05-27) scoped W2–W5 and its Q2 stated the lane is
`evals/gsm8k_math/train_sample/v1` with "each follow-up injector PR runs its own
before/after delta **on the existing report**" — i.e. injectors were expected to
*change* `train_sample` directly.

ADR-0175 (the **later, governing** direction) sealed serving: **`3/47/0` is frozen
until a Phase-5 reviewed promotion.** A W2–W5 injector that changes the frozen
`report.json` would violate the seal and trip `generate_claims.py --check`.

**Resolution.** ADR-0170's injectors are the right capability work; under ADR-0175
they must be developed **sealed** — measured on a sealed lane, with the frozen
`3/47/0` artifact **byte-identical**, and promotion to serving deferred to Phase-5.
This ADR defines that seal.

## 3. Decision — a flag-gated sealed injector dispatch

ADR-0174 Phase 5a retired flag-gated *reader variants* (two parallel question
parsers) because maintaining two reader code-paths bred drift. This ADR does **not**
reintroduce that: there is **one** injector dispatch; the seal is a single boolean on
the dispatch that selects *which categories are eligible to emit*, not a forked reader.

```
inject_from_match(match, sentence, *, sealed: bool = False)
```

- `sealed=False` (default) — the **frozen** behavior. `_INJECTORS` resolves exactly
  the categories that ship today. `_score_one_candidate_graph` and the frozen
  `train_sample` runner call with the default → **`3/47/0` byte-identical.**
- `sealed=True` — the **sealed lane**. The dispatch additionally consults
  `_SEALED_INJECTORS` (the new W2–W5 entries). A separate sealed runner
  (`evals/gsm8k_math/train_sample/v1/run_sealed_injectors.py`) calls with
  `sealed=True` and writes `report_sealed.json` — the progress metric.

Phase-5 promotion is then a **one-line, reviewed flip**: moving a category from
`_SEALED_INJECTORS` into `_INJECTORS` (or flipping the default), accompanied by a
regenerated, ratified `report.json`. Until that review, serving is untouched.

### 3.1 Why a boolean parameter, not an env var or a forked module

- **Not a forked module** — that is the reinvention ADR-0174 Phase 5a warned against;
  the sealed path must be the *same* recognizer/solver, differing only in injector
  eligibility, so a sealed solve is a true preview of the promoted behavior.
- **Not an env var** — invisible global state breaks deterministic replay and is a
  forbidden hidden-behavior surface (CLAUDE.md). An explicit keyword argument is
  inspectable, defaulted-safe, and threaded only through the eval call site.
- **Default-off** — the freeze is the default; you must *opt in* to the sealed lane,
  so no accidental serving drift is possible.

## 4. wrong=0 obligations (the seal's guarantees, before any merge)

1. **Frozen path byte-identical.** With `sealed=False`, `train_sample/report.json`
   stays `{"correct":3,"refused":47,"wrong":0}` byte-identical;
   `generate_claims.py --check` and lane-SHA checks pass unchanged. A test pins this.
2. **Sealed lane `wrong=0`.** On `report_sealed.json`, `wrong` must be **0** — a
   sealed injector that lets the solver commit a wrong answer is rejected outright.
   `correct` may rise (or hold, with refusals converted to grounded-but-still-refused
   eliminations); `wrong` may **never** rise above 0.
3. **The five-layer net is preserved, not weakened** (ADR-0163.D.2 / ADR-0170 Q3):
   matcher narrowness → extraction correctness → injection admissibility
   (`_initial_admissible` / `roundtrip_admissible`) → propose-time replay gate →
   multi-branch decision rule. A sealed injector adds an `_INJECTORS`-shaped entry; it
   passes through every existing gate.
4. **Case 0050 hazard pin** (ADR-0167 W2-D / [[feedback-wrong-zero-hazard-case-0050]]):
   the sealed lane must not widen admissions on the 0050 canary.
5. **No overfitting.** Each injector is a *general* shape (a category the recognizer
   already classifies), validated on the whole `train_sample` + the confuser probe,
   never tuned to specific rows. No per-case rule.

## 5. First injector — selection is code-constrained, not category-aesthetic

The "cleanest leaf" intuition (currency_amount, because it is a plain
`CandidateInitial`) **did not survive contact with the code**, and recording why is
part of the eliminate-first discipline:

- `_match_currency_amount` is **detection-only** — it returns `(tuple(), "amount")`
  with **empty `parsed_anchors`** (no value, no entity). An injector therefore has
  nothing to consume; W3 first requires *extending the matcher to extract values*
  (an `extract_values=True` anchor path), which is upstream surface, not a leaf.
- `CandidateInitial.__post_init__` **whitelists the anchor verb**. `"It cost
  $100,000…"` (case 0028) uses `cost`, which is **not** a registered initial-state
  anchor; emitting an initial for it would raise. So W3 also needs a dataclass
  whitelist change — more wrong=0 surface than assumed.

### 5.1 What the live-loop instrumentation actually showed

Wrapping `inject_from_match` inside the **live** loop (the standalone `match()` probe
of §1.2 is untrustworthy — it lacks `prior_subject` + the ratified registry) over the
47 refusals revealed a **schema-vs-extraction split** that determines surface:

| refusing category | n | `parsed_anchors` already populated? | blocked on |
|---|---|---|---|
| `rate_with_currency` | 3 | **yes (3/3)** — `amount, per_unit, currency_symbol, kind` | **schema** — needs `CandidateRate` in the `SentenceChoice` union |
| `temporal_aggregation` | 2 | **yes (2/2)** — `count_token, window_unit, window_quantifier` | **schema** — needs an `apply_rate` primitive |
| `discrete_count_statement` | 20 | no (empty) | matcher **extraction** + downstream composition |
| `currency_amount` | 3 | no (empty) | matcher **extraction** + `CandidateInitial` anchor-whitelist (`cost`) |
| `multiplicative_aggregation` | 3 | no (empty) | matcher **extraction** (WAVE-A partial) |
| `descriptive_setup_no_quantity` | 4 | no (by design) | nothing to inject |

So there is **no 10-line leaf win**: the matcher-complete categories are blocked on a
schema extension, and the schema-free categories are blocked on matcher extraction.

### 5.2 The deeper finding: no case is one injector away

Tracing the matcher-complete cases to their full requirement set:

- **0001** (`Tina makes $18/hour`, gold 990) needs rate **+** the `1/2`-wage overtime
  fraction **+** a `>8 hours` threshold **+** `10 hours × 5 days`.
- **0017** (`$50/day or $500 for 14 days`, gold 800) needs min-cost reasoning over
  `$50×20` vs `$500×⌈20/14⌉` blocks.

**Every refused case is multi-statement.** A single injector grounds one quantity but
leaves the graph incomplete → the case **stays refused** (no report-level delta). The
candidate-graph reader's 47 refusals are therefore **not** unlocked one leaf at a time;
the unit of measurable progress is a **target case's complete injector + composition
set**, landing together.

### 5.3 Consequence for sequencing

1. **Seal mechanism first** (§3) — ships and is validated with an empty
   `_SEALED_INJECTORS` proving the frozen path is byte-identical and the sealed lane
   exists (a true wrong=0 guarantee; not yet a capability claim).
2. **`CandidateRate` schema next** (the planned ADR-0170 §Open-Q4 work) — the highest-
   leverage, most foundational unblock: the `rate_with_currency` + `temporal_aggregation`
   matchers already extract everything; rate is pervasive across GSM8K. This is its own
   ADR + sealed PR.
3. **A first complete target-case unlock** — pick the case with the *smallest* full
   requirement set (injectors + composition), land its set together on the sealed lane,
   and measure a `report_sealed.json` `correct++` with `wrong=0`. Only then is a
   capability claim earned.

In all cases the first effect of any individual injector is honestly **elimination**
(grounding a previously unread quantity); a **solve** requires the whole case's set —
per §1.2/§5.2, no flip count is claimed in advance.

Deferred to follow-ups (each its own go/no-go, all sealed): the remaining W2–W5
injectors and `rate_with_currency` (needs the planned `CandidateRate` union extension,
ADR-0170 §Open-Q4).

## 6. What this ADR does NOT do

- Does **not** change serving `3/47/0` (the whole point of the seal).
- Does **not** touch the derivation reader / `resolve_pooled` (the disjoint sealed
  comprehension organ; its confuser work stands on its own lane).
- Does **not** build the Phase-5 ratification bridge — that remains the ADR-0175
  deliverable and the hard dependency before *any* sealed gain reaches the headline.
- Does **not** add a non-deterministic mechanism, a forked reader, or hidden global
  state.

## 7. ADR-0166 three-question test

- **Q1 — Capability:** a sealed injector lane that lets ADR-0170 W2–W5 injectors be
  developed and measured without mutating frozen serving. First deliverable is the
  seal mechanism itself; the first *capability* is the `CandidateRate` schema (§5.3),
  since the matcher-complete `rate_with_currency`/`temporal_aggregation` categories are
  blocked on schema, not extraction.
- **Q2 — Lane:** `evals/gsm8k_math/train_sample/v1/report_sealed.json` (new, sealed).
  The frozen `report.json` stays the ratified serving artifact.
- **Q3 — Invariant:** `wrong == 0` on both the frozen path (byte-identical) and the
  sealed lane, enforced by the unchanged five-layer net + the §4 pins.

## 8. Why this obeys the standing principles

- **Use the deterministic system as a microscope** (the GOAL): this ADR exists
  *because* the microscope dissected the 47 refusals and proved the wall is injection,
  not arithmetic — and that the session had been maturing the wrong organ.
- **Eliminate failures first, then solve:** a sealed injector's first job is to ground
  an unread quantity (eliminate the unread-refusal), earning a solve only when the
  whole case composes.
- **Decode, don't guess** ([[thesis-decoding-not-generating]]): the injector reads a
  quantity the recognizer already identified; it stores no flat answer.
- **wrong=0 > coverage** (ADR-0175): the seal makes serving regression structurally
  impossible; sealed `wrong` is gated at 0.
- **No reinvention** (ADR cross-reference discipline): resumes ADR-0170's own roadmap
  under ADR-0175's seal, rather than inventing a parallel path.
