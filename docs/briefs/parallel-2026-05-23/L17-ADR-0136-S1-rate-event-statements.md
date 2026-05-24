# L17 brief — ADR-0136.S.1 — Statement corridor: rate/event statement parsing

**Worktree (use the one already created):**

```bash
cd ../core-adr-0131-g6-rate-capacity   # branch: feat/adr-0131-g6-rate-capacity
```

> Rename this ADR to ADR-0136.S.1 in all doc headers; the worktree and branch stay.

---

## Taxonomy ground truth (read before coding)

`evals/gsm8k_math/train_sample/v1/refusal_taxonomy.json` (just written, on disk):

| Primary barrier | Cases | Notes |
|---|---|---|
| `context_filler` | **23** | Narrative scene-setters — legitimately refuse; not parser gaps |
| `compound_statement` | 5 | Two ops in one sentence |
| rate/capacity/price class | **4** | Direct S.1 targets |
| `distributive_multiply` | 1 (+5 secondary) | N bags × M items each |
| diverse long-tail | 17 | Age anchors, goal statements, multi-step chains, etc. |

**Key constraint on expectations:** S.1 can honestly claim `0/50 → ≤4/50` admission
lift, not a dramatic jump. The 23 context-filler cases legitimately have no
parseable numeric state in their opening sentence — the parser's refusal there
is correct. Do not attempt to skip or soft-fail context sentences. If a
sentence cannot be parsed, the problem is refused. This is the safety rail.

The one case with **capacity_rate as its only barrier** is `gsm8k-0014`:

```
Bob can shuck 10 oysters in 5 minutes.  How many oysters can he shuck in 2 hours?
```

This is the proof case. It must admit with answer `240.0`.

---

## Scope

Extend the parser and candidate graph to handle two closed statement shapes
that appear as the **primary** (and often sole) barrier in 4 of the 50 cases:

**Shape A — capacity-rate** (cases 0014, 0018-secondary, 0034-secondary):
```
<Actor> can <verb> N <unit> in M <time-unit>.
```
→ rate = N/M (units per time-unit). Question: "How many X can Actor verb in T time?"
→ answer = rate × T (with time-unit conversion).

**Shape B — earnings/price rate** (case 0001 primary, but conditional blocks it;
cases 0011, 0022, 0044 are also rate-class):
```
<Actor> makes/earns/charges/receives N <money-unit> per/an/a <time-or-count-unit>.
```
→ `EarningsRate(actor, amount, money_unit, per_unit)`.
Question: "How much money does Actor make in T time?" → `amount × T` (with
conversion when needed). Start with the simplest closed set; see constraints below.

**Do not** attempt to unlock context-filler-gated cases. The 23 context-filler
sentences refuse correctly; the rate parsing behind them is irrelevant until those
sentences parse.

---

## Pre-flight checks (run before coding)

```python
from generate.math_candidate_graph import parse_and_solve

# Shape A — must currently refuse
r = parse_and_solve("Bob can shuck 10 oysters in 5 minutes.  How many oysters can he shuck in 2 hours?")
assert r.refusal_reason is not None   # gap

# Shape B — must currently refuse  
r = parse_and_solve("Tina makes $18.00 an hour.  Tina works 5 hours.  How much money does Tina make?")
assert r.refusal_reason is not None   # gap (note: simplified, no conditional)
```

---

## Reference docs (these only)

1. `generate/math_candidate_parser.py` lines 424–763 — initial-state extractor
   and question extractor patterns; model new extractors on these shapes.
2. `generate/math_candidate_graph.py` lines 277–400 — `parse_and_solve`
   structure; the capacity short-circuit path goes here (before `_build_graph`).

---

## What to ship

### Parser additions (`generate/math_candidate_parser.py`)

**Shape A — capacity-rate:**

- `CandidateCapacity` frozen dataclass: `actor`, `count` (float), `unit`,
  `per_count` (float), `per_unit`, `source_span`.
- `_CAPACITY_RE` — closed verb set: `shuck`, `pick`, `pack`, `make`, `produce`,
  `type`, `read`, `write`, `paint`, `run`, `score`, `answer`, `complete`;
  closed time-unit set: `second`, `minute`, `hour`, `day`.
  Pattern: `"<Actor> can <verb> N <unit> in M <time-unit>."` (case-insensitive).
- `extract_capacity_candidates(sentence)`.
- `CandidateCapacityQuestion` frozen dataclass: `actor` (str|None), `unit`,
  `per_count` (float), `per_unit`, `source_span`. `actor` is None for pronoun
  forms (`he/she/they/it`).
- `_CAPACITY_Q_RE` — same closed verb + time-unit sets.
  Pattern: `"How many <unit> can <actor-or-pronoun> <verb> in T <time-unit>?"`.
- `extract_capacity_question_candidates(sentence)`.
- Time-unit helper `_to_seconds(count, unit) -> float`: second=1, minute=60,
  hour=3600, day=86400.

**Shape B — earnings rate:**

- `CandidateEarningsRate` frozen dataclass: `actor`, `amount` (float), `unit`
  (canonicalize `dollar`/`$`), `per_unit`, `source_span`.
- `_EARNINGS_RE` — closed verb set: `make`, `earn`, `receive`, `get`, `charge`;
  closed currency tokens: `$`, `dollar`, `dollars`, `cent`, `cents`;
  closed per-unit alternation: `per <unit>`, `a <time-unit>`, `an <time-unit>`,
  `for each <unit>`, `every <unit>`.
  Pattern: `"<Actor> <verb> <$|N> <currency> <per-token> <unit>."`.
- `extract_earnings_candidates(sentence)`.
- `CandidateEarningsQuestion` frozen dataclass: `actor`, `unit`, `time_count`
  (float), `time_unit`, `source_span`.
- `_EARNINGS_Q_RE`: `"How much money does <actor> make/earn in T <time-unit>?"`.
- `extract_earnings_question_candidates(sentence)`.

### Candidate graph short-circuit (`generate/math_candidate_graph.py`)

Add before the Cartesian product in `parse_and_solve`:

**Capacity path:** if `len(statement_sentences) == 1` and that sentence yields
exactly one `CandidateCapacity` and the question yields one
`CandidateCapacityQuestion`:
- Actor match: if `question.actor` is not None, require
  `capacity.actor.lower() == question.actor.lower()`; else accept any.
- Compute: `rate_per_sec = capacity.count / capacity.per_count / _to_seconds(1, capacity.per_unit)`;
  `answer = rate_per_sec * _to_seconds(question.per_count, question.per_unit)`.
- Return `CandidateGraphResult(answer=answer, ...)` if `answer > 0`.

**Earnings path:** if `len(statement_sentences) == 1` (or 2 with one being a
named-entity duration statement like `"Tina works 5 hours."`) and the
statement yields one `CandidateEarningsRate` and the question yields one
`CandidateEarningsQuestion`:
- Actor match: require names match (case-insensitive).
- Compute: convert `earnings.per_unit` and `question.time_unit` to seconds;
  derive `rate_per_sec`; `answer = rate_per_sec * question.time_count_seconds`.
- Return answer.

Both paths must gate: `answer > 0` and actor resolved; else fall through to
refusal (do not emit `wrong` answers — if uncertain, refuse).

### Curated axis lane (`evals/math_capability_axes/S1_rate_events/v1/cases.jsonl`)

**≥20 cases** — independent of GSM8K phrasing:

| Shape | Count | Requirements |
|---|---|---|
| Capacity same time-unit (min→min) | ≥4 | base case |
| Capacity cross time-unit (min→hr, sec→min) | ≥4 | conversion required |
| Capacity pronoun question | ≥4 | `he`/`she` question form |
| Earnings same time-unit (hr→hr) | ≥4 | base earnings case |
| Refusal: closed-verb miss (outside verb set) | ≥4 | wrong==0 probe |

Include `gsm8k-0014` verbatim as one of the capacity cases. Include a
simplified Tina-style earnings case (no conditional) as one earnings case.

### Runner + report

`evals/math_capability_axes/S1_rate_events/v1/runner.py` — same shape as G5
runner. `wrong == 0` gate. Byte-equal `report.json`.

### Tests (`tests/test_adr_0136_S1_rate_events.py`, ≥15)

- `_CAPACITY_RE` matches canonical forms; refuses closed-verb misses.
- `_EARNINGS_RE` matches `makes $X an hour`, `earns $X per hour`, `receives $X for each unit`.
- Time conversion: minutes→hours, seconds→minutes.
- `gsm8k-0014` verbatim admits with answer `240.0`.
- Simplified Tina ("makes $18/hr, works 5 hours → $90") admits.
- Pronoun actor resolves.
- Mismatched-actor refuses (not wrong — refuses).
- `wrong == 0` on full axis lane.
- Byte-equal report.
- B3 regression guard.
- GSM8K `admitted_wrong == 0` + post-S.1 `admission_rate` honestly reported.

### ADR (`docs/decisions/ADR-0136.S.1-rate-event-statements.md`)

Parent: `ADR-0136-statement-layer-corridor.md` (write as sibling doc, one
paragraph stub, if parent doesn't exist yet). Document:
- Taxonomy finding: 23/50 context-filler (correctly refused), 4/50 rate-class
  direct targets.
- Closed verb sets and why (no wildcard matching).
- Short-circuit path rationale.
- Honest GSM8K claim: `0/50 → ≤4/50`; exact delta stated in PR body.
- Deferred: context-filler gated problems (need context-sentence semantic
  classification, out of scope), conditional branching (overtime), percentage
  rates (interest), multi-statement earnings (duration in separate sentence).

---

## Hard constraints

- `wrong == 0` on every axis case and GSM8K safety rail.
- No changes to `math_solver.py`, `math_problem_graph.py`, `math_verifier.py`.
- Closed verb sets — no regex wildcards for verbs.
- `gsm8k-0014` must admit verbatim with `answer == 240.0`.
- Do not attempt context-filler cases. If a sentence can't parse, refuse.
- Honest admission delta in PR body: count exactly which GSM8K cases newly admit.

---

## Out of scope

- Context-filler gated rate cases (23 cases — needs semantic classification).
- Conditional branching (`if she works more than 8 hours`).
- Percentage/interest rates (10% simple interest).
- Multi-statement earnings (duration asserted in a separate sentence from the
  rate — needs general duration-statement parser first).
- Any GSM8K admission beyond the 4 rate-class primary cases.

---

## Target branch

PR against `main` from `feat/adr-0131-g6-rate-capacity`. Title:
`feat(ADR-0136.S.1): rate/event statement parsing — capacity + earnings shapes, axis lane N/N, wrong==0, gsm8k-0014 admits`.

Body: taxonomy summary, per-shape case counts, pre/post GSM8K probe delta
(honest count), link to taxonomy JSON and ADR.

**Exit criterion.** CI green; axis runner exits 0 with `wrong == 0`;
`gsm8k-0014` admits with answer `240.0`; GSM8K `admitted_wrong == 0` and
honest admission delta stated; B3 unchanged; ADR committed.
