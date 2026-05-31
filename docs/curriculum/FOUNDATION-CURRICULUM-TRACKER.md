# CORE Foundation Curriculum Tracker

Status: proposed tracker  
Scope: documentation only; this file tracks planned, in-progress, admitted, and deferred curriculum work.

---

## Status vocabulary

Use these statuses consistently.

| Status | Meaning |
|---|---|
| `PLANNED` | The slice is proposed and ordered but no pack/eval implementation exists yet. |
| `DESIGNING` | A slice-specific design doc or ADR candidate is being drafted. |
| `IMPLEMENTING` | Pack/eval/test work exists on a branch but is not admitted. |
| `BLOCKED` | A prerequisite or contradiction prevents progress. |
| `ADMITTED` | Pack, eval, tests, docs, and admission evidence are present and accepted. |
| `DEFERRED` | Intentionally delayed because prerequisites are missing or priority changed. |
| `RETIRED` | Superseded by a later admitted slice. |

No slice should be marked `ADMITTED` from prose alone.

---

## Admission checklist per slice

A curriculum slice requires:

- [ ] slice design documented under `docs/curriculum/`
- [ ] pack manifest added or updated
- [ ] deterministic pack data added
- [ ] eval README added
- [ ] public/dev eval cases added as appropriate
- [ ] runner or harness support added if needed
- [ ] tests added
- [ ] refusal/undetermined cases included
- [ ] replay/provenance artifacts stable where applicable
- [ ] no unrelated runtime behavior changed
- [ ] existing relevant eval lanes remain non-regressed

---

## Foundation stages

### Stage 1 — Language relation substrate

Status: `PLANNED`

Purpose: make every later subject parseable as typed claims and relations.

Candidate artifacts:

```text
packs/language/en_core_syntax_v1
packs/language/en_core_relations_v2
evals/language_claim_parsing
evals/language_relation_binding
```

Core primitives:

- subject/predicate
- agent/action/object
- modifier attachment
- prepositional relation
- temporal sequence
- conditional
- negation
- comparison
- coordination
- reference resolution
- claim boundary
- evidence span

Admission gates:

- [ ] every parsed claim carries evidence span
- [ ] every relation has typed operands
- [ ] comparative forms are directionally correct
- [ ] temporal forms preserve order
- [ ] conditionals preserve antecedent/consequent scope
- [ ] negations do not invert unsupported claims
- [ ] insufficient evidence yields typed refusal or undetermined state
- [ ] existing GSM8K behavior does not regress

Recommended first branch:

```text
feat/en-core-syntax-relations-v1
```

---

### Stage 2 — Arithmetic semantics and quantity state

Status: `PLANNED`

Purpose: compile story statements into deterministic quantity/state ledgers.

Candidate artifacts:

```text
packs/math/arithmetic_semantics_v1
packs/math/quantity_ledger_v1
packs/math/ratio_rate_percent_v1
evals/math_quantity_language
evals/math_state_tracking
```

Core primitives:

- entity
- attribute
- quantity
- mutation
- initial state
- final state
- unknown value
- comparative quantity
- ratio
- rate
- percent

Admission gates:

- [ ] addition/subtraction/multiplication/division language maps to deterministic relations
- [ ] entity and attribute identity are preserved through mutations
- [ ] unknowns remain symbolic until solved or refused
- [ ] comparative phrases are directionally stable
- [ ] answer derivation is replayable
- [ ] missing quantity evidence refuses rather than guesses

---

### Stage 3 — Measurement, units, and dimensional reasoning

Status: `PLANNED`

Purpose: attach quantities to reality and reject invalid operations.

Candidate artifacts:

```text
packs/math/measurement_units_v1
packs/math/dimensional_analysis_v1
evals/unit_conversion
evals/dimensional_validity
evals/rate_reasoning
```

Core primitives:

- unit
- unit family
- dimension
- conversion
- compound unit
- numerator/denominator unit
- scale
- precision
- exact vs measured value

Admission gates:

- [ ] unit conversions are deterministic
- [ ] incompatible dimensions are rejected
- [ ] compound units preserve structure
- [ ] final answers retain units
- [ ] rate questions preserve per-unit basis
- [ ] measured/rounded/exact quantities are not conflated

---

### Stage 4 — Logic, classification, and conditionals

Status: `PLANNED`

Purpose: preserve truth under inference.

Candidate artifacts:

```text
packs/logic/classification_v1
packs/logic/conditionals_v1
packs/logic/quantifiers_v1
packs/logic/contradiction_v1
evals/basic_logic
evals/claim_entailment_refusal
```

Core primitives:

- identity
- difference
- class membership
- subclass
- part-whole
- necessary condition
- sufficient condition
- quantifier
- negation
- conjunction/disjunction
- contradiction
- equivalence

Admission gates:

- [ ] entailment is separated from plausibility
- [ ] contradiction is explicit
- [ ] quantifier scope is preserved
- [ ] necessary/sufficient conditions are not swapped
- [ ] unknown membership yields refusal/undetermined state

---

### Stage 5 — Scientific method and evidence grammar

Status: `PLANNED`

Purpose: separate observation, hypothesis, inference, verification, contradiction, and scope.

Candidate artifacts:

```text
packs/science/scientific_method_v1
packs/science/evidence_relations_v1
packs/science/causal_reasoning_v1
evals/science_evidence_classification
evals/hypothesis_prediction_experiment
```

Core primitives:

- observation
- measurement
- hypothesis
- prediction
- experiment
- control
- evidence
- model
- theory/law
- confounder
- replication
- scope limit

Admission gates:

- [ ] observed claims are not promoted to verified causal claims without evidence
- [ ] missing controls/sample sizes/methods are surfaced
- [ ] causal claims are distinguished from associations
- [ ] scope limits are preserved
- [ ] contradictory evidence is represented explicitly

---

### Stage 6 — Data literacy, probability, and statistics

Status: `PLANNED`

Purpose: reason under uncertainty without overclaiming.

Candidate artifacts:

```text
packs/math/data_literacy_v1
packs/math/probability_v1
packs/math/statistical_reasoning_v1
evals/table_reasoning
evals/probability_language
evals/base_rate_reasoning
evals/correlation_vs_causation
```

Core primitives:

- data point
- variable
- dataset
- table
- chart
- mean/median/mode
- spread
- outlier
- sample/population
- probability
- conditional probability
- base rate
- false positive/negative
- absolute vs relative risk
- correlation
- causation

Admission gates:

- [ ] table rows/columns are typed
- [ ] denominators are preserved
- [ ] sample vs population is not confused
- [ ] base-rate information is used when present
- [ ] unsupported statistical claims are refused or qualified
- [ ] correlation is not promoted to causation without evidence

---

### Stage 7 — Computational thinking and algorithms

Status: `PLANNED`

Purpose: make procedures, traces, and state machines first-class.

Candidate artifacts:

```text
packs/cs/computational_thinking_v1
packs/cs/algorithm_trace_v1
packs/cs/state_machine_v1
evals/procedure_following
evals/algorithm_trace
evals/branching_logic
```

Core primitives:

- sequence
- branch
- loop
- state
- function
- input/output
- decomposition
- abstraction
- invariant
- error handling
- trace
- rough complexity

Admission gates:

- [ ] procedures produce deterministic traces
- [ ] branch conditions are grounded in evidence
- [ ] state mutations are explicit
- [ ] invalid or missing steps are not silently repaired
- [ ] loop termination is represented or refused if underspecified

---

### Stage 8 — Systems and crosscutting structures

Status: `PLANNED`

Purpose: enable cross-field transfer without collapsing domain boundaries.

Candidate artifacts:

```text
packs/crosscutting/patterns_v1
packs/crosscutting/cause_effect_v1
packs/crosscutting/systems_models_v1
packs/crosscutting/structure_function_v1
packs/crosscutting/stability_change_v1
evals/cross_domain_transfer
evals/systems_reasoning_basic
```

Core primitives:

- pattern
- cause/effect
- scale
- proportion
- system
- model
- structure/function
- stability/change
- feedback
- equilibrium
- constraint
- conservation-like accounting

Admission gates:

- [ ] shared structure is identified across fields
- [ ] domain-specific limits are preserved
- [ ] analogy is not treated as proof
- [ ] transfer does not bypass evidence or scope
- [ ] unsupported cross-domain claims refuse or remain unassessed

---

## Domain foundation backlog

These are intentionally downstream of the foundation stages.

| Domain foundation | Status | Required prerequisites |
|---|---|---|
| Physical science foundations | `DEFERRED` | stages 1-5, units, systems |
| Chemistry foundations | `DEFERRED` | physical science, units, conservation, evidence |
| Life science foundations | `DEFERRED` | systems, chemistry basics, structure/function |
| Earth/space/environment systems | `DEFERRED` | systems, measurement, data literacy |
| History inquiry | `DEFERRED` | language, chronology, evidence/source evaluation |
| Geography/spatial reasoning | `DEFERRED` | measurement, scale, systems |
| Economics basics | `DEFERRED` | arithmetic, rates, incentives, systems, uncertainty |
| Civics/institutions | `DEFERRED` | language, rules, authority, procedure, ethics |
| Medicine | `DEFERRED` | biology, chemistry, statistics, evidence, ethics, refusal |
| Law | `DEFERRED` | language, logic, authority, procedure, evidence, source hierarchy |
| Finance/trading | `DEFERRED` | statistics, probability, time series, risk, uncertainty |
| Engineering | `DEFERRED` | units, physical science, systems, constraints, algorithms |
| Theology/hermeneutics | `DEFERRED` | language, logic, Hebrew/Greek, history, source criticism, ethics |

---

## Immediate next work queue

Recommended near-term order:

1. `feat/en-core-syntax-relations-v1`
2. `feat/quantity-ledger-arithmetic-semantics-v1`
3. `feat/measurement-units-dimensional-analysis-v1`
4. `feat/basic-logic-conditionals-v1`
5. `feat/scientific-method-evidence-grammar-v1`
6. `feat/data-literacy-probability-v1`

Each branch should be narrow, separately reviewable, and independently non-regressing.

---

## Notes log

Add dated notes below as work proceeds.

### 2026-05-30

- Roadmap and tracker introduced as documentation-only planning artifacts.
- No pack, eval, runtime, or admission changes included.
- First recommended implementation slice is language relation substrate.
