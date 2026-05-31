# CORE Foundation Curriculum Roadmap

Status: proposed planning document  
Scope: documentation only; no runtime, pack, eval, or admission changes  
Purpose: define the lower-level subjects CORE should learn first so later domain studies are built on strong reusable foundations rather than brittle topic accumulation.

---

## 1. Doctrine

CORE should not widen capability by collecting impressive subjects first. It should widen capability by building the reusable primitives that make later subjects lawful, auditable, transferable, and refusal-safe.

The curriculum order is therefore:

```text
language -> relations -> quantity -> units -> logic -> evidence -> data -> algorithms -> systems -> domains
```

The desired result is not broad trivia. The desired result is a model that can read the world as:

```text
typed, evidenced, unit-bearing, logically constrained state transitions
```

This keeps teaching aligned with CORE's core commitments:

- deterministic replay over fluent improvisation
- evidence spans over unsupported assertion
- typed refusal over hidden guessing
- ratified packs over loose memory
- cross-field transfer through shared primitives, not analogy theater
- small load-bearing PRs instead of large speculative rewrites

---

## 2. Foundation-before-domain rule

Do not start with high-level applied subjects such as medicine, law, finance, engineering design, or advanced theology until their lower-level dependencies exist.

Applied domains require foundations:

| Applied domain | Required foundations first |
|---|---|
| Medicine | language, quantity, units, biology, chemistry, statistics, evidence quality, ethics, scope/refusal |
| Law | language, definitions, conditionals, authority, jurisdiction, procedure, evidence, source hierarchy |
| Finance/trading | arithmetic, rates, time, probability, statistics, incentives, risk, uncertainty, causality vs correlation |
| Engineering | units, dimensional analysis, physical science, constraints, systems, algorithms, safety |
| Theology/hermeneutics | language, logic, history, source criticism, ethics, epistemology, Hebrew/Greek depth lanes |
| Research assistance | language, evidence, data, statistics, source evaluation, methodology, uncertainty handling |

The rule is simple:

```text
No domain pack should pretend to reason above the level of its substrate packs.
```

---

## 3. Curriculum ladder

### Stage 0 — Existing base and constraints

Current project direction already includes language packs, epistemic states, reviewed learning, refusal-first behavior, sealed eval discipline, and GSM8K-driven math/reasoning work.

This roadmap does not replace those efforts. It gives them a larger teaching order.

### Stage 1 — Language relation substrate

Purpose: make every later subject parseable.

CORE must reliably identify:

- subject / predicate
- agent / action / object
- modifiers
- prepositional relations
- temporal sequence
- conditionals
- negation
- comparison
- coordination
- reference resolution
- claim boundaries

Canonical representation target:

```text
CLAIM {
  subject
  relation
  object_or_value
  qualifiers
  evidence_span
  epistemic_state
}
```

Initial pack candidates:

```text
packs/language/en_core_syntax_v1
packs/language/en_core_relations_v2
```

Initial eval candidates:

```text
evals/language_claim_parsing
evals/language_relation_binding
```

Acceptance direction:

- Every parsed claim has an evidence span.
- Every relation has typed operands.
- Temporal, conditional, comparative, and negated forms are deterministic.
- Missing evidence produces a typed refusal or undetermined state.
- Existing GSM8K behavior does not regress.

### Stage 2 — Arithmetic semantics and quantity state

Purpose: make story statements compile into deterministic quantity/state transitions.

CORE must treat arithmetic operations as semantic transformations, not just symbols.

Examples:

| Operation | Semantic forms |
|---|---|
| Addition | combine, gain, receive, total, altogether |
| Subtraction | remove, lose, spend, left, difference |
| Multiplication | groups of, each, per, repeated addition |
| Division | share equally, groups of, inverse rate |
| Fractions | part-whole, ratio, scaling |
| Percent | per hundred, relative change |
| Ratios | comparison, mixture, scale |
| Rates | quantity per unit |

Canonical representation target:

```text
ENTITY_LEDGER {
  entity
  attribute
  initial_state
  mutations[]
  final_state
  evidence_spans[]
}
```

Initial pack candidates:

```text
packs/math/arithmetic_semantics_v1
packs/math/quantity_ledger_v1
packs/math/ratio_rate_percent_v1
```

Initial eval candidates:

```text
evals/math_quantity_language
evals/math_state_tracking
```

Acceptance direction:

- Quantity-bearing language becomes a replayable ledger.
- Operations preserve entity and attribute identity.
- Unknown initial/final values remain symbolic until solved or refused.
- Comparative phrases are directionally correct.
- Already-admitted GSM8K cases remain stable.

### Stage 3 — Measurement, units, and dimensional reasoning

Purpose: attach numbers to reality and reject invalid operations.

CORE must understand:

- unit identity
- unit families
- unit conversion
- compound units
- dimensional compatibility
- rates
- scale
- precision
- exact vs measured quantities

Canonical operation rule:

```text
operation(value_a: unit_x, value_b: unit_y) -> valid only if dimensions permit it
```

Initial pack candidates:

```text
packs/math/measurement_units_v1
packs/math/dimensional_analysis_v1
```

Initial eval candidates:

```text
evals/unit_conversion
evals/dimensional_validity
evals/rate_reasoning
```

Acceptance direction:

- Unit conversions are deterministic and evidence-backed.
- Incompatible operations refuse or mark invalid.
- Compound units preserve numerator/denominator structure.
- Answers include units when units are present in the prompt.

### Stage 4 — Logic, classification, and conditionals

Purpose: preserve truth under inference.

CORE must understand:

- identity and difference
- class membership
- subclass relations
- part-whole structure
- necessary and sufficient conditions
- quantifiers
- negation
- conjunction/disjunction
- contradiction
- equivalence
- causal vs logical implication

Initial pack candidates:

```text
packs/logic/classification_v1
packs/logic/conditionals_v1
packs/logic/quantifiers_v1
packs/logic/contradiction_v1
```

Initial eval candidates:

```text
evals/basic_logic
evals/claim_entailment_refusal
```

Acceptance direction:

- Entailed claims are separated from merely plausible claims.
- Contradictions are explicit, not smoothed over.
- Quantifier scope is preserved.
- Unknown membership or insufficient premises produces refusal/undetermined state.

### Stage 5 — Scientific method and evidence grammar

Purpose: separate observation, hypothesis, inference, verification, contradiction, and scope.

CORE must represent:

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

Initial pack candidates:

```text
packs/science/scientific_method_v1
packs/science/evidence_relations_v1
packs/science/causal_reasoning_v1
```

Initial eval candidates:

```text
evals/science_evidence_classification
evals/hypothesis_prediction_experiment
```

Acceptance direction:

- Observed claims are not promoted to verified causal claims without support.
- Missing controls, denominators, sample sizes, or methods are exposed.
- Causal language is distinguished from correlation/association.
- Scope limits are preserved.

### Stage 6 — Data literacy, probability, and statistics

Purpose: reason under uncertainty without overclaiming.

CORE must understand:

- data point
- variable
- dataset
- table
- chart
- mean/median/mode
- range/spread
- outlier
- sample vs population
- probability
- conditional probability
- base rate
- false positive/negative
- absolute vs relative risk
- correlation vs causation

Initial pack candidates:

```text
packs/math/data_literacy_v1
packs/math/probability_v1
packs/math/statistical_reasoning_v1
```

Initial eval candidates:

```text
evals/table_reasoning
evals/probability_language
evals/base_rate_reasoning
evals/correlation_vs_causation
```

Acceptance direction:

- Tables are parsed into typed rows/columns.
- Claims unsupported by denominator/sample data are refused or qualified.
- Base-rate information is preserved.
- Relative and absolute changes are not confused.

### Stage 7 — Computational thinking and algorithms

Purpose: make procedures, traces, and state machines first-class.

CORE must understand:

- sequence
- branching
- loops
- state
- function input/output
- decomposition
- abstraction
- invariant
- error handling
- trace/replay
- rough cost/complexity

Initial pack candidates:

```text
packs/cs/computational_thinking_v1
packs/cs/algorithm_trace_v1
packs/cs/state_machine_v1
```

Initial eval candidates:

```text
evals/procedure_following
evals/algorithm_trace
evals/branching_logic
```

Acceptance direction:

- Procedures produce deterministic traces.
- Branch conditions are evaluated from evidence.
- State mutations are explicit.
- Invalid or missing steps are not silently repaired.

### Stage 8 — Systems and crosscutting structures

Purpose: enable cross-field transfer without collapsing domain boundaries.

CORE must understand:

- pattern
- cause/effect
- scale/proportion/quantity
- system and system model
- structure/function
- stability/change
- feedback
- equilibrium
- constraint
- conservation-like accounting

Initial pack candidates:

```text
packs/crosscutting/patterns_v1
packs/crosscutting/cause_effect_v1
packs/crosscutting/systems_models_v1
packs/crosscutting/structure_function_v1
packs/crosscutting/stability_change_v1
```

Initial eval candidates:

```text
evals/cross_domain_transfer
evals/systems_reasoning_basic
```

Acceptance direction:

- Shared structure is identified across domains.
- Domain-specific limits are preserved.
- Analogies are marked as analogies unless structurally proven.
- Transfer does not bypass evidence or scope.

### Stage 9 — Domain foundations

Only after Stages 1-8 should domain foundations expand aggressively.

Recommended order:

1. physical science foundations
2. life science foundations
3. earth/space/environment systems
4. social studies foundations: history, geography, economics, civics
5. applied domains: medicine, law, finance, engineering, research assistance, theology/hermeneutics

---

## 4. Cross-field transfer patterns

The curriculum should deliberately test reusable structure across fields.

### Rate transfer

```text
math:      60 miles / 2 hours       -> 30 miles/hour
finance:  $60 / 2 items             -> $30/item
medicine: 60 mg / 2 kg              -> 30 mg/kg
chemistry: 60 g / 2 L               -> 30 g/L
computing: 60 requests / 2 seconds  -> 30 requests/second
```

Expected behavior:

- same abstract rate structure
- distinct units
- distinct domain safety boundaries

### Conservation transfer

```text
arithmetic: total objects
physics: energy/momentum
chemistry: mass/atoms
accounting: money balance
inventory: stock
law: chain of custody
```

Expected behavior:

- identify accounting/conservation-like invariant
- preserve domain rules
- refuse unsupported conservation claims where the domain does not justify them

### Structure/function transfer

```text
biology: heart -> pump blood
engineering: pump -> move fluid
software: queue -> preserve order of work
civics: court -> adjudicate disputes
```

Expected behavior:

- identify structure/function relation
- avoid pretending equivalent mechanisms
- surface evidence and scope

---

## 5. Standard eval shape

Every curriculum slice should include four eval types.

### 5.1 Recognition eval

Can CORE identify the structure?

```text
Input: John has 4 fewer apples than Mary.
Expected: comparative_quantity_relation
```

### 5.2 Transformation eval

Can CORE produce the typed representation?

```text
john.apples = mary.apples - 4
```

### 5.3 Execution eval

Can CORE solve, infer, classify, or validate deterministically?

```text
mary.apples = 10
john.apples = 6
```

### 5.4 Refusal eval

Can CORE refuse when evidence is insufficient?

```text
Input: John has fewer apples than Mary. How many apples does John have?
Expected: insufficient quantity evidence
```

---

## 6. Minimum documentation required per slice

Each implemented curriculum slice should add or update:

```text
docs/curriculum/<slice-name>.md
packs/<domain>/<pack-name>/manifest.json
evals/<eval-name>/README.md
```

The curriculum doc should include:

- purpose
- prerequisites
- non-goals
- typed primitives introduced
- expected representations
- eval surfaces
- refusal boundaries
- cross-field bridges
- admission criteria
- follow-on dependencies unlocked

---

## 7. Recommended immediate implementation sequence

The next six load-bearing slices should be:

1. `en_core_syntax_v1` and `en_core_relations_v2`
2. `quantity_ledger_v1` and `arithmetic_semantics_v1`
3. `measurement_units_v1` and `dimensional_analysis_v1`
4. `classification_v1`, `conditionals_v1`, `quantifiers_v1`, `contradiction_v1`
5. `scientific_method_v1`, `evidence_relations_v1`, `causal_reasoning_v1`
6. `data_literacy_v1`, `probability_v1`, `statistical_reasoning_v1`

Recommended first implementation branch after this planning PR:

```text
feat/en-core-syntax-relations-v1
```

Recommended first runtime/eval scope:

```text
packs/language/en_core_syntax_v1/
packs/language/en_core_relations_v2/
evals/language_claim_parsing/
evals/language_relation_binding/
tests/test_language_claim_parsing.py
tests/test_relation_binding_replay.py
```

Do not widen into domain foundations until these first six slices are either admitted or explicitly scoped as incomplete dependencies.

---

## 8. Non-goals

This roadmap does not authorize:

- bulk domain ingestion without substrate dependencies
- open-ended web-corpus learning
- probabilistic guessing to fill missing relations
- hidden correction of invalid statements
- promotion from observed to verified without evidence
- manual manifest drift
- eval promotion without replay artifacts
- replacement of refusal with best-effort fluency

---

## 9. Definition of done for this roadmap

This planning document is useful only if it remains trackable.

Use `docs/curriculum/FOUNDATION-CURRICULUM-TRACKER.md` as the living checklist. A curriculum slice should not be marked admitted until the relevant pack, eval, test, and documentation artifacts exist and pass their admission criteria.
