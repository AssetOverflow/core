<!-- CANONICAL | docs/analysis/deductive-logic-phase-2-benchmark-runway-2026-06-04.md | 2026-06-04 | strategy/implementation-runway | next slice after deductive proof-evidence gates: scale + recognizable benchmark without weakening wrong=0 | verified: planning-only, no ADR number assigned -->

# Deductive logic Phase 2 benchmark runway

This document picks up immediately after the deductive-logic pivot and proof-evidence gates.
It is intentionally planning-only: no ADR number is assigned here, no serving path is changed,
and no capability claim is introduced by this file.

## 0. Latest merged state this continues

The current capability line is now deductive logic, not GSM8K serving promotion.

Merged state to preserve:

1. The GSM8K committing bridges that produced sealed wrong answers are disabled. The standing rule is that no committing bridge is re-enabled unless sealed or independent evidence proves `wrong == 0` on the promoted path.
2. The honest GSM8K held-out dev lane exists. Its baseline is a refusal floor, not a capability result.
3. `generate/proof_chain/entail.py` provides a sound and complete propositional entailment operator over the propositional regime.
4. `evaluate_entailment_with_trace` is the evidence-bearing API; `evaluate_entailment` remains the stable verdict-only wrapper.
5. `evals/deductive_logic/runner.py` treats both wrong answers and refusals on committed in-regime cases as lane failures.
6. The cognitive pipeline records entailment traces as telemetry only for exact verification turns. It does not change the user-facing surface.

These constraints are load-bearing. Phase 2 must scale the checkable capability without turning the GSM8K failure mode back on under a different name.

## 1. Phase 2 objective

Build a recognizable benchmark bridge for CORE's deductive capability while preserving the same anti-recurrence disciplines:

```text
coverage rises only where independent gold says the engine is right;
wrong stays 0;
refusal on committed in-regime cases is a capability failure;
out-of-regime natural language refuses until a reviewed grounding layer exists.
```

The target is not natural-language general reasoning yet. The target is a grounded finite-entity mirror of published deductive-rule benchmarks such as RuleTaker / ProofWriter-style cases:

```text
finite entities + finite predicates + finite rules
  -> deterministic propositional formulas
  -> evaluate_entailment_with_trace
  -> independently checked gold
```

This keeps the answer checkable by construction while making the eval externally recognizable.

## 2. Non-goals for the next PR

Do not do these in Phase 2 PR-1:

- Do not wire the deductive operator into `chat/runtime` as an answering surface.
- Do not add broad natural-language parsing.
- Do not claim RuleTaker / ProofWriter benchmark performance unless the actual benchmark artifacts and scoring policy are present and independently checked.
- Do not collapse finite-entity grounding into opaque text normalization.
- Do not reuse the engine output as gold.
- Do not score on examples authored around observed failures as the main metric.

## 3. Recommended PR stack

> **Status (2026-06-04): PR-1 and PR-2 SHIPPED** (PR #556), as Phase 2 of the
> universal-structure plan
> (`docs/analysis/universal-structure-and-field-symbol-coherence-gate-2026-06-04.md`).
> `evals/deductive_logic/grounding.py` is the lowering compiler; the committed
> `finite_entity/v1/cases.jsonl` carries oracle-derived gold; the test file gates
> `engine == oracle == gold` (PR-2 parity). PR-3 (published-benchmark mirror) and
> PR-4 (scale + SHA-pin) remain open. The grounding lane is registered under the
> deductive oracle's INV-25 independent-gold coverage.

### PR-1 — finite-entity grounding contract and tiny mirror fixture — **✅ SHIPPED (#556)**

Add the deterministic contract before scaling data.

Files likely involved:

- `evals/deductive_logic/grounding.py`
- `evals/deductive_logic/finite_entity/README.md`
- `evals/deductive_logic/finite_entity/v1/cases.jsonl`
- `tests/test_deductive_logic_finite_entity_grounding.py`

The contract should define a small, explicit input schema:

```json
{
  "id": "fe-v1-0001",
  "entities": ["cat"],
  "facts": [{"predicate": "furry", "entity": "cat", "polarity": true}],
  "rules": [{"if": [{"predicate": "furry", "var": "x", "polarity": true}], "then": {"predicate": "mammal", "var": "x", "polarity": true}}],
  "query": {"predicate": "mammal", "entity": "cat", "polarity": true},
  "gold": "entailed"
}
```

Lowering rule:

```text
predicate(entity) -> predicate__entity
negative atom     -> ~predicate__entity
rule body         -> conjunction of lowered body literals
rule              -> body -> head
```

In v1, the accepted grammar should be intentionally narrow:

- finite named entities only;
- unary predicates only;
- universal single-variable rules only, grounded by explicit entity expansion;
- no existential quantifiers;
- no binary relations;
- no functions;
- no unbounded variables;
- no English sentence ingestion.

Refuse any case outside that grammar with a typed reason.

### PR-2 — independent oracle parity for finite-entity cases — **✅ SHIPPED (#556)**

Before adding benchmark data, assert that the finite-entity lowered formulas score identically under:

1. the CORE ROBDD entailment engine; and
2. the independent truth-table oracle already used by `evals/deductive_logic/oracle.py`.

The key invariant:

```text
lower(case).premises, lower(case).query
  -> engine outcome == independent oracle gold
```

A single disagreement fails the lane.

### PR-3 — published-benchmark mirror adapter

Only after PR-1/PR-2, add an adapter that maps a small frozen subset of recognizable benchmark cases into the finite-entity schema. The adapter should record provenance without making the benchmark fixture a hidden training set.

Required report fields:

- source benchmark name;
- source split or subset policy;
- source case id/hash;
- lowering decision;
- unsupported feature reason when refused;
- engine outcome;
- independent gold;
- trace hash.

### PR-4 — scale fixture and promotion threshold

Scale after the contract holds. Promotion gates should require:

```text
wrong == 0
refused == 0 on committed in-regime lowered cases
correct >= threshold on externally recognizable finite-entity cases
all trace hashes deterministic across replay
```

The threshold should be explicit and conservative. The first scaled PR should be allowed to report coverage without serving promotion.

## 4. Data contract details

### Atom canonical form

Use a closed ASCII-safe atom form:

```text
[predicate_slug]__[entity_slug]
```

Examples:

```text
furry__cat
mammal__cat
needs_food__cat
```

Slugging must be deterministic and reject unsafe ambiguity:

- lowercase ASCII letters, digits, and single underscores only;
- no leading digit;
- no empty slug;
- no double-underscore inside a component;
- no component that already contains the separator `__`;
- reject instead of silently repairing.

### Grounding universal unary rules

For each rule and each entity:

```text
if furry(x) then mammal(x)
entities = [cat, dog]
```

lowers to:

```text
furry__cat -> mammal__cat
furry__dog -> mammal__dog
```

### Conjunctive rule bodies

```text
if furry(x) and living(x) then animal(x)
```

lowers per entity to:

```text
(furry__cat & living__cat) -> animal__cat
```

### Refusal reasons

Use a closed reason vocabulary for the grounding layer, distinct from entailment reasons:

- `unsupported_predicate_arity`
- `unsupported_quantifier`
- `unsafe_symbol`
- `unknown_entity`
- `unknown_variable`
- `malformed_case`
- `empty_case`

This mirrors the proof operator's typed refusal discipline instead of letting malformed benchmark rows leak into ambiguous failures.

## 5. Reporting semantics

Extend reporting without weakening the existing deductive runner semantics.

Recommended categories:

- `correct`: engine outcome equals independent gold;
- `wrong`: engine outcome differs from independent gold and engine did not refuse;
- `refused_in_regime`: finite-entity lowering succeeded but the engine refused;
- `refused_out_of_regime`: finite-entity lowering rejected an unsupported case by contract;
- `unsupported`: benchmark source case was outside the v1 finite-entity grammar.

Only committed in-regime cases count toward the Phase 2 capability metric. Unsupported/out-of-regime counts are useful honesty telemetry, not correctness credit.

## 6. Tests that should exist before scale

Minimum tests for PR-1/PR-2:

1. deterministic atom lowering;
2. rejection of unsafe symbols and separator ambiguity;
3. fact lowering, including negative facts;
4. unary universal rule expansion over all entities;
5. conjunctive rule body lowering;
6. unknown entity query refuses at grounding boundary;
7. unsupported arity refuses at grounding boundary;
8. engine/oracle parity for a tiny finite-entity fixture;
9. trace hash stability across replay;
10. runner fails on wrong or refused-in-regime cases.

## 7. Why this is the right continuation

This is the narrow bridge from Phase 1 to externally legible capability:

- It keeps CORE on checkable-conclusion terrain.
- It reuses the exact propositional entailment operator rather than adding a new reasoning engine.
- It introduces grounding as a typed compiler, not as loose natural-language interpretation.
- It gives a path toward RuleTaker / ProofWriter without pretending natural-language parsing is solved.
- It preserves the lesson of the GSM8K breach: no capability claim without held-out or independent gold.

## 8. Stop conditions

Stop and document the failure instead of patching around it if any of these occur:

- Lowering cannot preserve benchmark semantics without adding hidden interpretation.
- The independent oracle disagrees with the engine on in-regime formulas.
- Refusals on committed in-regime cases become non-zero.
- A benchmark subset requires binary relations, existential quantification, or arithmetic to look impressive.
- Any proposed serving promotion lacks sealed or independent wrong-zero evidence.

The correct move under those conditions is to tighten the contract or split the benchmark subset, not to add another shallow committing bridge.
