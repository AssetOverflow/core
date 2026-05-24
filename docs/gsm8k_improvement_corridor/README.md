# GSM8K Improvement Corridor

This directory is the planning and implementation-control surface for moving CORE from bounded-grammar math competence toward broader GSM8K admission without corrupting the architecture.

The controlling posture is:

> GSM8K is a coverage probe, not a promotion gate. Admission must grow only as a side effect of principled capability expansion. `admitted_wrong == 0` remains non-negotiable.

## Why this exists

CORE's current math stack is not failing because arithmetic is absent. It is refusing because the natural-language-to-typed-graph compiler is intentionally narrow. GSM8K stresses ordinary language variation: currency forms, rate phrasing, comparison phrasing, multi-clause initial states, pronouns, ellipsis, and question target binding.

The improvement corridor turns those gaps into sequenced capability work packages.

## Current diagnosis

| Layer | State | GSM8K impact |
|---|---|---|
| Deterministic solver | Present | Not the primary blocker |
| Trace verifier | Present | Supports zero-wrong admission discipline |
| Bounded grammar lane | Present | Proves end-to-end correctness inside declared scope |
| GSM8K coverage probe | Present | Measures admission/refusal honestly |
| Candidate graph parser | Growing | Main admission bottleneck |
| Question target binding | Incomplete for composed/derived states | High-leverage next unblock |
| Numeric literal normalization | Incomplete for currency/percent/decimal forms | Blocks common GSM8K cases |
| Verb-class semantics | Narrow | Blocks ordinary state/transfer/production language |
| Cross-sentence discourse | Mostly refused | Blocks pronouns, aliases, and carried state |

## Corridor documents

- [`roadmap.md`](./roadmap.md) — phased capability sequence.
- [`blueprints/ADR-G5-question-target-binding.md`](./blueprints/ADR-G5-question-target-binding.md) — first implementation blueprint.
- [`blueprints/ADR-G3-numeric-literals.md`](./blueprints/ADR-G3-numeric-literals.md) — numeric normalization blueprint.
- [`blueprints/ADR-G6-verb-class-semantics.md`](./blueprints/ADR-G6-verb-class-semantics.md) — verb class expansion blueprint.
- [`blueprints/ADR-G7-discourse-state.md`](./blueprints/ADR-G7-discourse-state.md) — cross-sentence/coreference blueprint.
- [`implementation_work_packages.md`](./implementation_work_packages.md) — issue-style engineering tasks.
- [`measurement_contract.md`](./measurement_contract.md) — gates, reports, and anti-regression rules.

## Non-negotiables

1. No GSM8K-specific template farming.
2. No best-effort guessing.
3. No parser relaxation without round-trip evidence.
4. Every expansion gets curated non-GSM8K axis cases.
5. Every expansion preserves `admitted_wrong == 0`.
6. Every refusal remains typed and audit-visible.
7. Every admitted answer must pass solver + independent verifier.

## Immediate next implementation target

Start with **G.5 question target binding for derived/composed initial states**.

Reason: G.4 already showed statement-side multi-clause parsing can improve while final GSM8K admission remains blocked downstream. The next highest-leverage work is letting the question layer bind targets produced by safe composed initial-state candidates.
