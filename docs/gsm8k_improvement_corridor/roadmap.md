# GSM8K Capability Roadmap

## Philosophy

The roadmap grows capability axes, not benchmark-specific hacks.

Every phase must:

- increase capability generally;
- improve curated axis coverage;
- preserve deterministic replay;
- preserve typed refusal;
- preserve `admitted_wrong == 0`.

## Phase G.5 — Question Target Binding

Goal:

Bind question targets against derived/composed initial-state graphs.

Examples:

- "How many apples does Ella have altogether?"
- "How many apples are there total?"
- "How much money did they save combined?"

Current failure mode:

Statement-side parse succeeds or partially succeeds, but the question layer cannot bind the requested quantity against composed state.

Expected effect:

First meaningful rise in GSM8K admission after G.4.

Primary deliverables:

- target-binding graph node;
- aggregate target resolution;
- verifier-aware target trace;
- composed-state target audit;
- curated target-binding axis lane.

---

## Phase G.3 — Numeric Literal Normalization

Goal:

Normalize typed numeric forms into canonical quantities.

Examples:

- `$40`
- `40 dollars`
- `3,000`
- `12.5`
- `50%`
- `1/2`

Current failure mode:

Value slots reject otherwise-valid statements.

Expected effect:

Large reduction in parser-level refusals.

Primary deliverables:

- literal tokenizer;
- canonical numeric representation;
- currency-aware quantity typing;
- percentage/fraction normalization;
- provenance-preserving numeric decomposition.

---

## Phase G.6 — Verb-Class Semantics

Goal:

Expand ordinary math-language verbs into typed operation semantics.

Examples:

- earned
- spent
- saved
- bought
- sold
- received
- left
- remaining
- needs

Current failure mode:

Parser recognizes only narrow operation predicates.

Expected effect:

Substantial increase in ordinary-school-word-problem admission.

Primary deliverables:

- operation verb ontology;
- polarity-aware transfer semantics;
- state-change classification;
- operation provenance trace;
- ambiguity refusal policy.

---

## Phase G.7 — Discourse State / Coreference

Goal:

Track entity continuity across sentences.

Examples:

- "Aaron has 5 apples. He gives 2 to Bob."
- "Sarah bought books. She then sold 3."

Current failure mode:

Cross-sentence references are mostly refused.

Expected effect:

Unlock multi-sentence GSM8K cases.

Primary deliverables:

- discourse entity registry;
- pronoun resolution;
- alias tracking;
- sentence-local confidence discipline;
- ambiguity refusal.

---

## Phase G.8 — Comparative/Rate Composition

Goal:

Safely compose comparison, rate, aggregation, and multiplicative structures.

Examples:

- "twice as many"
- "3 more than"
- "$5 per hour"
- "half as much"

Current failure mode:

Substrate exists in places, but composition across structures remains narrow.

Expected effect:

Large admission increase on higher-complexity GSM8K problems.

Primary deliverables:

- compositional operation graph;
- unit-consistent rate algebra;
- comparison aggregation semantics;
- nested-operation verifier traces.

---

## Final target state

The target is not:

> "Get a benchmark score."

The target is:

> Build a deterministic natural-language mathematical compiler whose admitted reasoning is auditable, replayable, and verifier-backed.
