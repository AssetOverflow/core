# ADR-0193 — Aggregate total-across: the existential question frame

**Status:** Proposed (implemented in this PR).
**Parent / extends:** [ADR-0131.G.5 — Aggregate Answer Composition](./ADR-0131.G.5-aggregate-answer-composition.md).
**Builds on:** [ADR-0191](./ADR-0191-candidate-graph-completeness-guard.md)
(completeness firewall) and [ADR-0192](./ADR-0192-discrete-count-open-noun-class.md)
(open-vocabulary possession statements).
**Substrate-with-compose: train_sample byte-identical 4/46/0; full-corpus
wrong=0 HOLDS; the frame composes end-to-end (proven below) and advances 23
real problems past the question wall.**

> **One line.** The solver already aggregates a total-across unknown
> (`Unknown(entity=None, unit=X)` sums every matching-unit state entry), and
> ADR-0131.G.5 wired exactly one verb frame for it — `"...do they have
> <cue>?"` — over a closed cue vocabulary. The equally common GSM8K
> *existential* frame, `"How many <unit> are there <cue>?"`, produced zero
> question candidates and refused at the question stage. This adds that frame
> over the **same closed cues** (no cue-vocabulary widening).

---

## 1. The gap (microscope finding, 2026-05-30)

The full-corpus microscope (`scripts/gsm8k_microscope.py`, ADR-0191) partitions
the serving reader's refusals. Among the 46 refusing `train_sample` cases,
exactly **5 are pure question-stage walls** (all statements parse, only the
question refuses): 0007, 0008, 0009, 0025, 0035 — each needing a *different*
solver capability (rate-division, comparative+algebra, inverse target-state,
multiplicative-aggregate). None is a simple total-across aggregate.

On the **full 7,473-question** corpus, however, ~60 problems close with an
explicit aggregate cue in a frame the parser did not recognise:

| surface | count | status before |
|---------|------:|---------------|
| `"How many <unit> are there <cue>?"` | ~31 | refused at question stage |
| `"What is the total number of <unit>?"` | ~29 | refused (ADR-0131.G.5 probe) |

The solver path for both is identical to the working `"do they have <cue>"`
form — `_resolve_unknown` sums `entity=None` across all matching-unit state.
The wall was purely the **question parser's verb-frame coverage**.

## 2. Decision

Add one question pattern, `_Q_THERE_RE` in `generate/math_candidate_parser.py`:

```
^How many <unit:1-2 words> are there <agg-cue>{1,2}?$
```

- `<agg-cue>` is the **same closed vocabulary** ADR-0131.G.5 established —
  `in total`, `altogether`, `combined`, `together`, plus the long-standing
  `in all`. This ADR does **not** widen the cue set; it adds a verb frame.
- The cue is **required** (`{1,2}` occurrences). The bare `"are there?"` form
  is deliberately NOT admitted — it is too ambiguous to map to total-across,
  and ADR-0131.G.5 pins it (`G5-refuse-004`) as a refusal probe, which still
  refuses unchanged.
- Maps to `Unknown(entity=None, unit=<canonical>)` — identical to the working
  frame.

### Why this is safe (the firewall is the precondition)

`wrong=0` is held downstream, not by the question form:
- **question round-trip** (`_question_admissible`) requires the unit token to
  ground in the question span; a conjoined unit (`"dogs and cats"`) fails the
  1–2-word match and refuses;
- **completeness guard** (ADR-0191) requires every source quantity to be
  consumed — a derived unit (`"animal legs"`, needing legs-per-animal
  multiplication) leaves a quantity uncovered and refuses (verified: the one
  full-corpus case reaching the guard, "Adlai has 2 dogs and 1 chicken… how
  many animal legs are there in all?", correctly refuses);
- **branch disagreement** refuses any competing reading.

## 3. What this deliberately does NOT do (ADR cross-reference)

`"What is the total number of <unit>?"` is **NOT** admitted here, even though
the solver would sum it correctly. ADR-0131.G.5 pins that exact surface as an
out-of-closed-cue **refusal probe** (`tests/test_adr_0131_G5_aggregate.py::
TestMismatchedUnitRefusal::test_outside_closed_cue_refuses`, case
`G5-refuse-002`). Promoting it is a correct future step, but it must **amend
ADR-0131.G.5's closed-cue contract** — it must not be contradicted from this
branch. `test_total_number_of_still_deferred` locks that boundary so this ADR
cannot silently break the parallel lane.

This is the discipline the standing doctrine requires ("no contradicting
in-use ADRs"): the non-conflicting verb-frame ships now; the cue-contract
change is surfaced for the ADR-0131.G owner.

## 4. Evidence

- **Composes end-to-end:** "Jamie has 28 marbles. Kyle has 12 marbles. How
  many marbles are there in total?" → **40.0** (proof the frame is
  load-bearing, not inert — any multi-possession problem now solves once its
  statements parse).
- **23 real problems** now parse the question (advance from the question wall
  to their next wall — statement parsing).
- **wrong=0 HOLDS** on the full 7,473-question corpus; `train_sample`
  byte-identical **4/46/0**; full-corpus correct unchanged at 4.
- **No metric delta on train_sample** — no `train_sample` case has the
  (existential-aggregate + all-statements-parsing) shape. This is the recurring
  composition-wall lesson (ADR-0190 / #497, now quantified a third time): a
  single-layer widening advances problems but flips none; every flip needs the
  conjunction of statement-parse + question + solver.
- **Tests:** `tests/test_aggregate_total_question_forms.py` (frame emits
  total-across over each closed cue; composes; conjoined/derived units refuse;
  `total number of` stays deferred). ADR-0131.G.5 lane and the synthetic-registry
  `wrong=0` capability-axis gate both green.

## 5. Consequences & follow-ups

- The aggregate branch's **existential frame** is now complete; the remaining
  aggregate gap is statement-parsing for the 23 advanced problems — dominated
  by **conjunction-of-possessions** ("X has A and B"; ADR-0192 left compound
  closed) and **container-subject possessions** ("Jar A has 28 marbles"; the
  entity recognizer rejects the `Noun + label` subject). The proven compose
  case shows that closing *either* statement gap flips real multi-container /
  multi-category aggregate problems.
- **Surfaced for the ADR-0131.G owner:** amend the closed-cue contract to admit
  `"What is the total number of <unit>?"` (solver-correct; ~29 real cases),
  retiring `G5-refuse-002` as a stale conservatism probe.
