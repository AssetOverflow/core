# Independent Comprehension Agreement Gate

**Status:** research-control document
**Date:** 2026-06-04
**Scope:** non-serving; defines the gate that must exist before any new field-backed or GSM8K-positive capability promotion.

## 1. Problem

The recent GSM8K post-mortem established the central failure mode: a committing reader can appear safe on a built-against slice while being unsound on held-out or sealed data. The repair was not another recognizer branch; it was the independent-gold discipline (INV-25) plus the universal-structure plan.

PRs #554-#558 now give CORE the foundation:

- independent-gold invariant and SHA-pinned deductive lane;
- binding-graph interlingua neutrality (INV-26);
- finite-entity grounding into propositional entailment;
- dimensional reasoning with an independent dimensional oracle;
- a 3-domain anti-overfit panel.

The remaining unsolved problem is not solving after a structure is already extracted. It is **independent comprehension**: can two genuinely independent readers construct the same canonical problem structure from the same task, and only then solve or verify it?

## 2. Doctrine

```text
A second solver over the same extracted structure is not a second derivation.
A second derivation begins with an independently constructed structure.
```

Agreement must therefore be tested at the structure boundary, not only at the final answer boundary.

Bad independence:

```text
shared parser -> symbolic solver
shared parser -> field/geometric solver
```

Good independence:

```text
symbolic reader -> canonical structure
field/geometric reader -> canonical structure
structure-equivalence gate -> oracle/proof solver -> commitment eligibility
```

## 3. Gate definition

A candidate capability may become promotion-eligible only if it passes all of the following gates.

| Gate | Requirement | Failure result |
|---|---|---|
| Reader independence | The two readers do not share parser, candidate generator, gold, or structure-building code. | Refuse / research failure |
| Canonical structure | Both readers emit a canonical, hashable structure with target, facts, relations, dimensions, and provenance. | Refuse |
| Structure equivalence | Structures are equal under a domain-specific equivalence relation stricter than same-answer. | Refuse |
| Independent gold | A proof checker, oracle, sealed set, or other non-SUT arbiter agrees. | Wrong/fail |
| Replay | Structure hashes and verdict traces are deterministic across replay. | Fail |
| Promotion wall | No serving path changes until held-out/sealed wrong=0 holds. | Block promotion |

## 4. Canonical structure minimum

Every participating structure must carry at least:

```text
structure_id
source_case_id
entities
quantities
units_or_types
relations
question_target
provenance_spans_or_hashes
unsupported_features
trace_sha256
```

The target is load-bearing. Two readers that agree on facts but bind different targets have not agreed.

## 5. Equivalence semantics

The first equivalence primitive should be intentionally narrow.

Equivalent:

- same target;
- same required entities;
- same quantity values after canonical numeric normalization;
- same dimensions/types;
- same relation kind and operands;
- same proof obligations;
- same unused-evidence classification.

Not equivalent:

- same numeric answer but different relation;
- same relation but different target;
- one structure ignores a required source quantity;
- one structure treats a distractor as relevant and the other exempts it;
- units/dimensions differ;
- either structure depends on an unsupported inferred fact.

## 6. Disagreement taxonomy

Closed disagreement reasons for the first implementation:

```text
missing_target
relation_mismatch
quantity_mismatch
dimension_mismatch
entity_binding_mismatch
unused_evidence_mismatch
unsupported_feature_mismatch
same_answer_different_structure
oracle_disagreement
reader_not_independent
```

These reasons should feed future contemplation/practice reports directly. The learning signal should identify the failed primitive, not merely the domain class.

## 7. Required proof of reader independence

A reader pair must provide a `DecoderIndependenceProof`-style record:

```text
reader_a_module
reader_b_module
shared_import_allowlist
forbidden_shared_modules
oracle_module
uses_same_parser: false
uses_same_candidate_generator: false
uses_same_gold: false
```

The test should include at least one AST/import scan like INV-25/INV-26, plus at least one behavioral non-vacuity test proving the guard can fail.

## 8. First implementation target

The first implementation should not be GSM8K and should not be broad natural language.

Recommended target:

```text
structured quantitative-relational lane
  -> symbolic structured compiler
  -> field/geometric structured compiler
  -> canonical structure equivalence
  -> independent quantitative oracle
```

This gives the field side a domain where geometry/metric relations are native, while avoiding the prior GSM8K failure mode.

## 9. Stop conditions

Stop and document instead of patching around the result if:

1. the field reader imports or calls the symbolic reader;
2. the two readers only agree on final answers, not structures;
3. equivalence admits same-answer/different-reason cases;
4. the oracle shares code with either reader;
5. a proposed gate passes only on built-against examples;
6. any route to serving is proposed before held-out/sealed wrong=0.

## 10. PR sequence

1. **Structure-equivalence primitive** — `core/reasoning/structure_equivalence.py` plus tests.
2. **Quantitative-relational structured lane** — independent oracle and structured cases.
3. **Field quantitative decoder prototype** — no symbolic reader imports.
4. **Controlled NL compiler** — only after structured symbolic/field agreement exists.
5. **GSM8K structure diagnostic** — non-serving, coverage-only.

## 11. Success definition

The first milestone succeeds when a supported case can be read by two independent readers into equivalent canonical structures, solved against independent gold, replayed deterministically, and refused on disagreement without touching serving.
