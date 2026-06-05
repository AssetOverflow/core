# Field-Reasoner Wedge Selection

**Status:** research-control document
**Date:** 2026-06-04
**Scope:** identifies the first honest field-as-reasoner target after the deductive pivot and 3-domain anti-overfit panel.

## 1. Context

The universal-structure arc established three facts:

1. Deductive propositional logic is a checkable substrate, not the best field wedge.
2. A clean algebraic/geometric propositional decoder still behaved as `O(2^n)` enumeration, so logic is combinatorial terrain.
3. Field independence must live in **reading/comprehension**, not merely in solving the same extracted structure.

Therefore the next field-reasoner wedge must be a domain where geometric/metric structure is natural, where independent gold is available, and where success helps return to quantitative comprehension without reopening the unsafe GSM8K serving bridge.

## 2. Candidate domains

| Candidate | Benefit | Risk | Decision |
|---|---|---|---|
| Pure propositional logic | Exact gold already exists | Combinatorial; field route degenerates to enumeration | Reject as first wedge |
| Finite-entity logic | Good grounding compiler | Still Boolean after lowering | Keep as substrate, not field wedge |
| Dimensional reasoning | Already independently golded; unit algebra is metric/type-like | Too narrow if only product/quotient | Use as supporting axis |
| Ratio/proportion | Metric-relational; direct bridge to GSM8K | Needs target binding and structure equivalence | **Choose** |
| Part-whole residuals | Natural quantitative structure | Prior GSM8K traps if promoted early | Include after ratio |
| Euclidean geometry | True geometric territory | Bigger encoding surface | Later wedge |
| Systems/software execution | Excellent independent gold | Not geometric; sandboxing surface | Later fourth panel domain |

## 3. Selected wedge

The first honest field-as-reasoner wedge is:

```text
structured quantitative relations:
  ratios
  proportions
  rates
  part-whole residuals
  dimensional consistency
```

This domain is selected because it is:

- close enough to GSM8K to matter;
- structured enough to avoid uncontrolled natural-language ambiguity;
- naturally metric/geometric rather than purely Boolean;
- independently checkable with a small oracle;
- compatible with the binding-graph interlingua and dimensional lane.

## 4. Minimal structured schema

### Ratio/proportion

```json
{
  "id": "qr-v1-0001",
  "family": "proportion",
  "given": [
    {"name": "flour", "value": 2, "unit": "cup"},
    {"name": "servings", "value": 8, "unit": "count"}
  ],
  "target": {"known": {"name": "servings", "value": 20, "unit": "count"}, "unknown": "flour"},
  "gold": {"value": 5, "unit": "cup"}
}
```

Canonical relation:

```text
flour / servings = 2 / 8
x_flour / 20_servings = 2 / 8
x_flour = 5
```

### Rate

```json
{
  "id": "qr-v1-0002",
  "family": "rate",
  "given": [
    {"name": "distance", "value": 60, "unit": "mile"},
    {"name": "time", "value": 2, "unit": "hour"}
  ],
  "target": {"unknown": "speed"},
  "gold": {"value": 30, "unit": "mile_per_hour"}
}
```

### Part-whole residual

```json
{
  "id": "qr-v1-0003",
  "family": "part_whole",
  "whole": {"name": "apples", "value": 30, "unit": "count"},
  "parts": [{"name": "sold", "value": 12, "unit": "count"}],
  "target": {"unknown": "remaining"},
  "gold": {"value": 18, "unit": "count"}
}
```

## 5. Independent oracle

The quantitative-relations oracle must not import the symbolic compiler, field decoder, or binding-graph implementation.

Oracle responsibilities:

```text
validate schema
reject unsupported families
compute exact rational result
compute/canonicalize result unit
return typed refusal for unsupported or malformed cases
```

Use exact rational arithmetic in the oracle. Floating tolerance should not be part of v1.

Closed oracle outcomes:

```text
correct
wrong
refused_malformed
refused_unsupported_family
refused_dimension_conflict
refused_divide_by_zero
```

## 6. Symbolic compiler

The symbolic compiler is allowed to be direct and typed. It reads the structured JSON and emits canonical quantitative structure.

It should not solve by side effect. It emits:

```text
entities
quantities
relation_edges
target
unit_constraints
provenance_hash
```

The solver/oracle consumes that structure separately.

## 7. Field/geometric compiler

The field compiler must be independent of the symbolic compiler.

Permitted:

- import field/algebra primitives;
- import neutral binding-graph dataclasses, once the structure boundary exists;
- emit the same canonical structure type;
- use dimensional unit primitives only through an allowlisted neutral boundary, if needed.

Forbidden:

- importing the symbolic quantitative compiler;
- importing its parser/case lowering helpers;
- consuming the symbolic compiler's output;
- matching only final numeric answers.

The first field encoding may be modest. Acceptable candidates:

| Encoding | Why acceptable in v1 |
|---|---|
| dimensioned vector relation | Minimal metric structure |
| affine scalar constraint | Good for rates and residuals |
| proportional line relation | Natural geometric ratio representation |
| CGA point/line meet | Stronger, later variant if v1 succeeds |

## 8. Required tests

Minimum test stack:

1. oracle handles all v1 families with exact rational results;
2. oracle refuses malformed/unsupported/divide-by-zero cases;
3. symbolic compiler emits canonical structure without solving;
4. field compiler emits canonical structure without importing symbolic compiler;
5. structure equivalence catches same-answer/different-relation;
6. `symbolic_structure == field_structure` on supported cases;
7. `answer == oracle_gold` on supported cases;
8. disagreement produces refusal, not fallback to one reader;
9. replay hash stability;
10. AST independence tests for oracle and field compiler.

## 9. Initial fixture shape

Start with 24-32 cases.

| Family | Positive | Negative/refusal |
|---|---:|---:|
| proportion | 6 | 2 |
| rate | 4 | 2 |
| part-whole residual | 4 | 2 |
| dimensional consistency | 4 | 2 |
| mixed distractor/exempt | 2 | 2 |

Do not author hundreds of cases. This is not a corpus-tuning lane. It is a mechanism proof lane.

## 10. GSM8K re-entry rule

GSM8K remains out of serving scope until this wedge proves itself.

Allowed after the structured lane:

```text
GSM8K structure diagnostic only
```

Forbidden until held-out/sealed gates pass:

```text
serving bridge
train_sample-only promotion
regex positive branch
field solver fallback on symbolic parse
```

## 11. Research outputs

The wedge is successful only if it produces all of:

1. a structured quantitative-relations lane with independent gold;
2. a symbolic compiler that emits canonical structure;
3. a field/geometric compiler that independently emits equivalent structure;
4. an equivalence gate that refuses on structural disagreement;
5. deterministic evidence traces;
6. no serving changes.

## 12. Next PR stack

1. `core/reasoning/structure_equivalence.py` — canonical structure equivalence.
2. `evals/quantitative_relations/oracle.py` — exact independent oracle.
3. `evals/quantitative_relations/v1/cases.jsonl` — small mixed fixture.
4. `generate/field_reasoning/quantitative_decoder.py` — field reader prototype.
5. `evals/gsm8k_math/structure_diagnostic/` — later, non-serving.

## 13. Stop conditions

Stop if:

- field structure construction cannot be made independent;
- the field route is only a second solver;
- ratios/proportions require broad NL parsing before structured schema works;
- oracle and SUT disagree and the cause is not understood;
- same-answer/different-structure slips through equivalence;
- a serving path becomes tempting before sealed evidence exists.

The correct outcome of a failed wedge is a falsification record, not a workaround.
