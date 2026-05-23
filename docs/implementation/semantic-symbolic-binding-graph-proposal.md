# Semantic-Symbolic Binding Graph Proposal

**Status:** Proposed architecture direction  
**Date:** 2026-05-23  
**Scope:** Documentation only; no runtime behavior change.  
**Related work:** ADR-0115..0118 math parser/solver/verifier/realizer, ADR-0126 candidate-graph parser, ADR-0131 proof corridor.

---

## Executive summary

CORE's current bounded math path already performs an early version of semantic-to-math compilation:

```text
natural-language statement
  -> candidate initial / operation / unknown
  -> MathProblemGraph
  -> deterministic solver
  -> SolutionTrace
  -> realizer
```

That is the correct direction, but it is not yet a full semantic-symbolic compiler. The next major architecture layer should make the intermediate representation explicit:

```text
natural language problem
  -> semantic proposition graph
  -> semantic-symbolic binding graph
  -> equation / expression system
  -> deterministic solver or typed refusal
  -> proof trace linked back to source spans
```

The goal is to convert word problems into mathematical form **without losing the identity, unit, role, provenance, and context of each symbol**.

---

## Why this matters

The GSM8K arc showed that adding grammar shape after grammar shape is a treadmill. The deeper missing layer is not another regex. It is a typed compiler boundary between language and symbolic reasoning.

A sentence like:

```text
Tina makes $18 per hour and works 7 hours.
```

should not compile directly into anonymous arithmetic:

```text
18 * 7
```

It should compile into bound symbolic facts:

```text
rate(Tina, wage) = 18 dollars/hour
duration(Tina, work) = 7 hours
earnings(Tina, work) = rate(Tina, wage) * duration(Tina, work)
```

The solver may then reduce this to:

```text
earnings(Tina, work) = 126 dollars
```

But the trace must retain where each symbol came from, what it means, which units it carries, and why the equation is admissible.

---

## Problem statement

The current system has strong pieces:

- typed math problem graphs,
- deterministic solver traces,
- verifier discipline,
- realizer surfaces,
- candidate-graph parsing,
- symbolic-equivalence hardening under ADR-0131.

But there is not yet a first-class object that says:

> This symbol corresponds to this semantic entity, this unit, this source span, this variable role, this dependency, and this admissibility contract.

Without that layer, natural-language math will remain either:

1. too brittle, because parser patterns must solve every semantic problem directly; or
2. too unsafe, because collapsing to raw equations discards context.

---

## Proposed abstraction

Introduce a `SemanticSymbolicBindingGraph` as the explicit compiler boundary between language/semantic parsing and symbolic/equational solving.

### Core objects

```text
BindingGraph
  symbols: tuple[SymbolBinding, ...]
  facts: tuple[BoundFact, ...]
  equations: tuple[BoundEquation, ...]
  unknowns: tuple[BoundUnknown, ...]
  constraints: tuple[BoundConstraint, ...]
  provenance: tuple[SourceSpanLink, ...]
```

### SymbolBinding

```text
symbol_id: stable deterministic identifier
name: canonical symbolic name
semantic_role: entity | quantity | rate | duration | count | total | difference | ratio | unknown
entity: optional semantic entity id
unit: optional canonical unit id
source_span: original text span
introduced_by: parser/candidate id
```

Examples:

```text
symbol: q_sam_apples_t0
role: quantity
entity: Sam
unit: apples
source_span: "Sam has 5 apples"
```

```text
symbol: rate_tina_wage
role: rate
entity: Tina
unit: dollars/hour
source_span: "$18 per hour"
```

### BoundFact

A grounded fact from language:

```text
q_sam_apples_t0 = 5 apples
rate_tina_wage = 18 dollars/hour
```

### BoundEquation

A derived symbolic relation with provenance:

```text
earnings_tina_work = rate_tina_wage * duration_tina_work
```

Each equation must carry:

- source fact dependencies,
- operation kind,
- unit transformation proof,
- admissibility status,
- refusal reason if invalid.

### BoundUnknown

The target of the question:

```text
unknown: earnings_tina_work
question_span: "How much does she earn?"
expected_unit: dollars
```

---

## Compilation pipeline

### Phase 1 — Surface parse to semantic candidates

Input:

```text
Tina makes $18 per hour. She works 7 hours. How much does she earn?
```

Output:

```text
CandidateFact(rate, entity=Tina, value=18, unit=dollars/hour)
CandidateFact(duration, entity=Tina, value=7, unit=hours)
CandidateUnknown(earnings, entity=Tina, unit=dollars)
```

This phase should remain refusal-first. If entity resolution or unit parsing is ambiguous, emit multiple candidates or refuse.

### Phase 2 — Semantic candidates to SymbolBindings

Allocate deterministic symbols:

```text
rate_tina_wage
hours_tina_work
earnings_tina_work
```

Symbol IDs must be stable under replay and should include semantic role, entity, unit, and source-order disambiguation.

### Phase 3 — Bind equations

Apply typed operators:

```text
earnings = rate * duration
```

Only if the unit algebra validates:

```text
(dollars/hour) * hour = dollars
```

Otherwise refuse.

### Phase 4 — Solve / verify / realize

The existing deterministic solver and verifier concepts remain, but now operate over equations whose symbols retain semantic meaning.

Output trace should show:

```text
rate_tina_wage = 18 dollars/hour
hours_tina_work = 7 hours
earnings_tina_work = rate_tina_wage * hours_tina_work = 126 dollars
```

---

## Refusal discipline

This layer must refuse rather than guess when:

- a pronoun has multiple valid antecedents,
- a unit conversion is absent from the ratified unit pack,
- a symbol would combine incompatible dimensions,
- a relation is implied but not licensed by a known operator,
- an equation would require unratified common-sense knowledge,
- the question target is not bound to a known symbol,
- multiple admissible symbolic systems produce different answers.

This preserves the project doctrine:

```text
wrong == 0 is more important than coverage
```

---

## Relation to ADR-0131

ADR-0131's Benchmark 3, the bounded-grammar word-problem lane, would become much stronger if backed by this layer.

Instead of merely proving:

```text
parser pattern -> answer
```

it would prove:

```text
bounded language -> bound symbols -> equations -> verified answer
```

This gives the public proof corridor a stronger differentiator:

- deterministic,
- traceable,
- auditable,
- refusal-first,
- source-span-linked,
- unit-aware,
- symbolically inspectable.

---

## Relation to symbolic equivalence

ADR-0131.1.B hardens the symbolic substrate: multivariable polynomials, exact rational coefficients, deterministic canonicalization.

The binding graph is the bridge that lets natural-language tasks use that substrate without losing semantic context.

In other words:

```text
symbolic equivalence = exact algebra substrate
binding graph = semantic compiler into that substrate
```

Both are needed. They should remain separate implementation phases.

---

## Proposed implementation phases

### Phase SSBG-1 — Data model only

Add immutable dataclasses:

- `SymbolBinding`
- `BoundFact`
- `BoundEquation`
- `BoundUnknown`
- `BoundConstraint`
- `SourceSpanLink`
- `SemanticSymbolicBindingGraph`

Acceptance:

- deterministic serialization,
- stable graph hash,
- no runtime parser changes,
- unit tests for construction invariants.

### Phase SSBG-2 — Compiler from existing MathProblemGraph

Create an adapter from the existing bounded math graph into the new binding graph.

Purpose: prove the abstraction can represent current behavior before expanding scope.

Acceptance:

- existing simple arithmetic cases compile,
- source entity/unit context preserved,
- solver answer unchanged,
- trace hash stable.

### Phase SSBG-3 — Unit-aware equation binding

Add dimension/unit validation for rate, duration, count, and transfer patterns.

Acceptance:

- valid unit transforms admit,
- incompatible dimensions refuse,
- missing unit conversions refuse,
- provenance cites pack entry IDs where applicable.

### Phase SSBG-4 — Question target binding

Bind questions to symbolic unknowns.

Acceptance:

- question target points to a known symbol,
- unknown unit is explicit,
- ambiguous targets refuse,
- unbound questions refuse.

### Phase SSBG-5 — Bounded grammar integration

Integrate with ADR-0131 Benchmark 3.

Acceptance:

- each Benchmark 3 case includes expected binding graph shape,
- solver trace links every equation to source spans,
- adversarial out-of-grammar probes refuse.

---

## Non-goals

This proposal is not:

- a general natural-language understanding system,
- an LLM-style chain-of-thought generator,
- a replacement for symbolic equivalence,
- a reason to reopen arbitrary GSM8K parser expansion,
- a promotion gate by itself.

It is a compiler layer for bounded-domain verified reasoning.

---

## Risks

### Risk 1 — Overbuilding too early

Mitigation: start with data model and adapter from existing `MathProblemGraph`; do not attempt broad NL support first.

### Risk 2 — Symbol names become brittle

Mitigation: separate stable `symbol_id` from human-readable `name`; use canonical serialization for hashing.

### Risk 3 — Unit algebra becomes an unbounded project

Mitigation: begin only with dimensions already represented in ratified units work; refuse missing conversions.

### Risk 4 — Hidden claim inflation

Mitigation: keep this behind ADR-0131 Benchmark 3 and explicitly say it proves bounded grammar compilation, not arbitrary GSM8K competence.

---

## Recommended next step

Do not implement this inside ADR-0131.1.B.

After the symbolic-equivalence hardening branch stabilizes, open a dedicated implementation branch:

```text
feat/semantic-symbolic-binding-graph-model
```

First PR should be data-model only.

No parser behavior changes.
No solver behavior changes.
No promotion wiring.

That gives the lead engineer a reviewable seam and avoids repeating the GSM8K parser-expansion treadmill.
