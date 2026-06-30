# RB-GSM Solver Design Input Notes

**Status:** design input / cautionary mapping  
**Branch:** `docs/semantic-state-transition-blueprint`  
**Related PR:** #489  
**Related docs:**

- `docs/handoff/SEMANTIC-STATE-TRANSITION-BLUEPRINT.md`
- `docs/decisions/ADR-0184-scoped-semantic-state-transitions.md`

---

## 1. Why this note exists

Josh provided an external-style sketch of a pure rule-based GSM8K solver: loose regex extraction, keyword dictionaries, if-then rules, a state builder, an operation queue, and deterministic arithmetic execution.

The sketch is directionally useful because it reinforces the same high-level move captured in ADR-0184:

```text
English story
  -> signal extraction
  -> state machine
  -> operation / transition list
  -> exact arithmetic replay
```

However, the sketch also contains claims and shortcuts CORE must **not** import as doctrine:

- “100% coverage with 30–50 rules” is an empirical claim, not an architectural fact.
- “Last actor works 99%” is not acceptable as a commit rule under `wrong = 0`.
- Regex and keyword hits may propose readings, but they must not decide answers.
- A first matching rule must not bypass pooling, completeness, target binding, or disagreement refusal.

This document records what to use, what to reject, and how to fold the useful pieces into CORE's semantic-state transition plan.

---

## 2. Useful principles to keep

### 2.1 Loose extraction, strict interpretation

The RB-GSM sketch correctly separates rough signal collection from final logic:

```text
loose regex = candidate signal collector
keyword / cue table = deterministic interpretation proposal
state machine + verifier = final decision path
```

CORE already follows a related discipline in `generate/derivation/extract.py`: extraction should identify lexeme-level quantities and surface evidence, not decide sentence meaning.

ADR-0184 should preserve this:

- regex may collect numbers, word-numbers, units, cue candidates, names, and punctuation boundaries;
- regex must not encode whole problem templates;
- semantic rules decide whether a signal becomes a state transition;
- verifier/pool decides whether the candidate can commit.

### 2.2 State machine before arithmetic

The RB-GSM sketch's strongest idea is the same as ADR-0184:

```text
text -> state builder -> operation queue -> executor
```

CORE should translate this as:

```text
text -> semantic ledger -> GroundedDerivation replay -> verifier / pool
```

The difference is that CORE's operation queue should be a typed, scoped semantic ledger, not a loosely ordered list of calculator commands.

### 2.3 Cue tables as proposal tables

The sketch's keyword dictionary is useful, but in CORE these should be cue tables that propose frame candidates:

```text
"has" / "had"        -> possible SET_STATE
"buys" / "gets"     -> possible GAIN
"loses" / "spends"  -> possible LOSS
"more than"          -> possible COMPARISON / DIFFERENCE
"altogether"         -> possible AGGREGATE target
"left"               -> possible final/net target or loss result cue
"each" / "per"       -> possible RATE / CONTAINER binding
"half" / "twice"     -> possible SCALAR / COMPARATIVE
```

They should not directly commit arithmetic.

### 2.4 Executor remains simple

Once the semantic ledger is correct, arithmetic execution should stay boring:

```text
SET_STATE -> assign
GAIN      -> add
LOSS      -> subtract
RATE      -> multiply when structurally bound
TRANSFER  -> subtract from source, add to target
DIFFERENCE -> subtract two bound states
```

This matches CORE's preference: make the hard part the reading/proof, not the arithmetic.

---

## 3. Claims to reject or downgrade

### 3.1 Reject unproven 100% dataset coverage claims

The provided sketch claims that 30–50 rules can solve every GSM8K problem after small tuning. CORE should not encode this as truth.

Correct CORE posture:

```text
Rule coverage is measured by lanes, not asserted.
```

Any coverage claim must be backed by:

- train_sample report;
- practice report;
- confuser probe;
- sealed holdout where available;
- wrong=0 preservation;
- perturbation / paraphrase checks where available.

### 3.2 Reject last-actor pronoun as a commit rule

The sketch says a simple last-actor rule works for ambiguous pronouns because GSM8K stories are linear.

CORE must not use that as a commit rule.

Allowed:

```text
single active actor + pronoun continuation -> candidate may emit
```

Forbidden:

```text
multiple prior actors + pronoun -> pick most recent and commit
```

Required behavior:

```text
multiple possible antecedents -> refuse / hold until a future safe resolver exists
```

### 3.3 Reject first-matching operation execution

The sketch's operation queue implies sequential execution of matched operations. CORE should avoid any first-match priority that can hide competing readings.

Required behavior:

```text
multiple plausible readings -> pooled candidates -> disagreement refuses
```

This preserves ADR-0182's core lesson.

### 3.4 Reject regex as final logic

Regex should not decide:

- final operation;
- actor binding;
- question target;
- temporal target;
- rate binding;
- comparison direction;
- transfer source/target.

Regex may propose candidates only.

---

## 4. Mapping RB-GSM components into CORE

| RB-GSM sketch | CORE equivalent | Notes |
|---|---|---|
| `number_pattern` | `generate/derivation/extract.py` | Keep lexeme-level only. |
| `name_pattern` | `state/bind.py` entity mention collector | Capitalized names are signals, not proof. |
| `keyword_table` | `state/change.py`, `state/rate.py`, `state/compare.py` cue tables | Cue tables emit semantic frame candidates. |
| `variables` dict | `SemanticLedger` / entity-owned `StateKey` | Must include entity + unit/scope. |
| `op_queue` | ordered `StateTransition` tuple | Transitions remain typed and replayable. |
| `execute_operations` | `state/replay.py` -> `GroundedDerivation` | Existing verifier still judges. |
| `answer_question` | semantic target binding + pool | Target must bind before commit. |
| `readable_steps` | derivation trace / replay explanation | Deterministic, auditable. |

---

## 5. Recommended adjustments to ADR-0184 implementation

### 5.1 Add a cue-table policy

ADR-0184 S1/S2 should explicitly define cue tables as **proposal tables**, not answer rules.

Policy:

```text
A cue table entry may create a candidate semantic frame.
A cue table entry may not directly commit an arithmetic operation.
Every emitted candidate must still pass replay, verification, classification, and pooling.
```

### 5.2 Add a loose-signal collector concept

S1 can stay helper extraction only, but S2 should prepare the seam for:

```text
SignalBundle:
  names
  quantities
  cue_hits
  question_markers
  temporal_markers
```

This does not need to be implemented immediately, but the model should not prevent it.

### 5.3 Keep accumulation as the first worked example

Use the Natalia-style pattern from the sketch as a future fixture class, but implement in CORE terms:

```text
Natalia sold 48 clips in April.
She sold half as many in May.
How many altogether?
```

Expected semantic reading:

```text
SET_STATE(Natalia.clips.April, 48)
SCALE_COPY(Natalia.clips.May, Natalia.clips.April, 0.5)
TARGET(aggregate Natalia.clips over April+May)
```

Important: this is **not** S1 or S2. It requires scalar-copy and aggregate target support, likely after basic accumulation ledger and semantic target wrapper exist.

### 5.4 Treat rate examples as S7, not S1

The Weng babysitting example:

```text
Weng earns $12 an hour. Yesterday she babysat 50 minutes. How much did she earn?
```

requires rate binding and unit conversion. It belongs under ADR-0184 S7 or a later rate/unit sub-ADR, not under S1 helper extraction.

### 5.5 Add anti-overfit language

Every semantic-state ADR/sub-ADR should include:

```text
Regex collects signals; it does not license final meaning.
Cue dictionaries emit candidates; they do not bypass verifier/pool.
New keyword entries require tests showing both positive use and at least one refusal guard.
```

---

## 6. Revised immediate S1 non-scope

Even with the RB-GSM input, S1 should remain behavior-equivalent.

Do not add yet:

- broad keyword table;
- operation queue executor;
- scalar-copy / half-as-many logic;
- rate conversions;
- cross-month aggregation;
- all-problem solver loop;
- last-actor pronoun resolver;
- confidence string or any claim of 100% coverage.

S1 remains:

```text
extract proven helper logic from accumulate.py
  -> state/bind.py
  -> state/change.py
  -> helper tests
  -> no behavior change
```

This matters because if S1 expands capability, it becomes impossible to tell whether the new semantic-state seam is safe.

---

## 7. Future capability ordering informed by RB-GSM

The RB-GSM sketch is most useful as a reminder of common GSM8K frame families. The ordering should be:

1. **Existing accumulation extraction** — already proven; refactor only.
2. **Semantic ledger replay** — `SET_STATE`, `GAIN`, `LOSS`.
3. **Semantic question target** — final/prior/count/aggregate skeleton.
4. **Scalar copy / comparative amount** — half/twice/as-many; Natalia-style cases.
5. **Aggregate target over scoped states** — altogether / total / in all across compatible states.
6. **Transfer** — source and target entity mutations.
7. **Difference questions** — how many more/fewer than.
8. **Rate/container binding** — each/per/hour/minutes.
9. **Temporal replay** — before/after/originally/finally.
10. **Held worlds / DAGs** — quantity reuse and branching.

This ordering differs slightly from the first ADR-0184 sequence by inserting scalar-copy and scoped aggregation before transfer. That may be higher payoff for GSM8K because many problems ask for totals over derived period/entity states.

This should be reviewed before coding S3+.

---

## 8. New guardrail tests suggested by this input

Add these once their phase begins:

### Loose regex must not over-decide

```text
"Alice has 5 apples. Bob has 3 apples. How many apples does Alice have?"
```

A loose name/number extractor may see `Alice`, `Bob`, `5`, `3`, and `apples`, but no rule may sum 5+3 for Alice.

### Cue hit must not commit alone

```text
"Kate studies for 3 hours and buys 5 pencils. How many pencils?"
```

A `for` cue may be collected, but it must not force multiplication into the pencil target.

### Last actor is not proof

```text
"Alice has 5 apples. Bob has 3 apples. She buys 2 more apples. How many apples does Alice have?"
```

If gender/antecedent resolution is not proven, refuse.

### Half-as-many requires source binding

```text
"Natalia sold 48 clips in April. She sold half as many in May. How many altogether?"
```

`half` is not merely `current_result *= 0.5`; it creates a state for May by copying from a bound prior April state, then aggregate target sums April+May.

### Rate conversion requires dimensional binding

```text
"Weng earns $12 an hour. She babysat 50 minutes. How much did she earn?"
```

`minutes` and `hour` require unit conversion only because the rate denominator is hour and the worked duration is minutes. No global minutes/hour rule should fire without a rate frame.

---

## 9. Bottom line

The RB-GSM sketch strengthens the ADR-0184 direction but does not replace CORE's safety discipline.

Use:

```text
loose signal collection
cue dictionaries
state machine
operation/transition replay
simple arithmetic execution
```

Do not use:

```text
unproven 100% claims
last-actor commits
first-rule-wins execution
regex as final meaning
keyword hits that bypass verification
```

CORE's version should be:

```text
loose lexeme signals
  -> cue-table semantic frame proposals
  -> scoped state ledger
  -> GroundedDerivation replay
  -> existing verifier/classifier
  -> pooled disagreement/commit eligibility
```

That keeps the useful classic rule-based insight while preserving the project doctrine: deterministic, auditable, refusal-first, and wrong=0-safe.
