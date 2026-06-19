# ProblemFrame Bindings and Contract Readiness — 2026-06-18

## Limitation

PR #830 recognized scalar, unit, hazard, and process-frame presence but left
semantic roles declarative. On train 50 / holdout 500, actor/object bindings,
bound question targets, and runnable organ contracts were all zero. A process
trigger therefore could not prove that an organ had the facts it required.

## Map

Three directions were considered:

1. Extend the canonical `ProblemFrame` with span-grounded mentions, bindings,
   bound relations, and a bound question target.
2. Build a parallel diagnostic graph beside `ProblemFrame`.
3. Infer readiness in reporting scripts from raw text.

Direction 1 was selected. It preserves one source of structural truth and lets
contract assessment operate only on typed frame evidence. Directions 2 and 3
would permit disagreement or raw-text fallback at the readiness boundary.

## Binding Model

`GroundedMention` retains kind, exact `SourceSpan`, original source text, and an
optional substrate fact ID. `MentionBinding` currently represents only the two
load-bearing edges: quantity-to-entity and quantity-to-unit. IDs and collection
order derive from source position and stable tie-breaks.

The builder recognizes a deliberately narrow set of local forms. It does not
derive answers, inspect case IDs, or introduce organ-local parsers.

## Bound Relation Model

`BoundRole` points a declared semantic role at a grounded mention or fact.
`BoundRelation` groups those role edges with their evidence spans. The first
diagnostic relations are:

- `transfer`: agent, patient, quantity, object;
- `subgroup_partition`: whole, part, fractional scale;
- `percent_of`: whole, part, percent scale.

Subgroup and percent relations are distinct so readiness cannot be fabricated
by pooling role names from unrelated candidates.

## Question Target Model

`BoundQuestionTarget` records the requested surface, target kind, evidence, and
the grounded target mention. An interrogative that cannot be grounded remains
an explicit target with `target_mention_id=None`; absence and unresolved state
are not conflated.

## Contract Assessment Model

`ContractAssessment` is a diagnostic projection with candidate organ, missing
bindings, unresolved hazards, evidence spans, explanation, and `runnable`.
`percent_partition` is runnable only when:

- a whole and subgroup are grounded by a subgroup relation;
- a percent relation refers to that same subgroup surface;
- the question target is grounded;
- no relevant blocking hazard remains.

Container and temporal contracts are emitted as explicit future-facing gaps.
Assessment does not admit an organ to serving.

## Adequacy Metrics

The new report reads committed case text and optional existing verdict metadata.
Gold answers are not used to synthesize bindings or contracts.

| Metric | Before train 50 | After train 50 | Before holdout 500 | After holdout 500 |
|---|---:|---:|---:|---:|
| frame built | 50 | 50 | 500 | 500 |
| scalar present | 47 | 47 | 470 | 470 |
| unit present | 21 | 21 | 202 | 202 |
| entity mention present | 0 | 50 | 0 | 494 |
| quantity binding present | 0 | 46 | 0 | 452 |
| bound process relation present | 0 | 16 | 0 | 124 |
| bound question target present | 0 | 42 | 0 | 402 |
| contract candidates | 0 | 42 | 0 | 423 |
| `contract_runnable_count` | 0 | 1 | 0 | 1 |

`contract_runnable_count` is the honest readiness metric. Trigger presence is
not readiness.

## Why `percent_partition` Remains Deferred

Case `gsm8k-train-sample-v1-0046` now has five quantity bindings, four bound
relations, a grounded question target, and a runnable diagnostic contract. That
is progress, not a serving migration. Only 1/42 train candidates and 1/423
holdout candidates meet the conservative contract, so broad admission would
still require fallback or overclaim coverage.

Migration becomes safe when the target corpus has adequate runnable coverage,
the remaining gap taxonomy is explicitly addressed, an organ consumes only
`ProblemFrame` evidence, and the serving safety lanes remain wrong-free. This
change intentionally leaves serving, answer admission, `report.json`, and
sealed artifacts unchanged.

## Masterstroke

Readiness is represented as a conjugate of construction: the builder propagates
source evidence into typed relations, while contract assessment exposes exactly
where that propagation fails to close. The design makes a nominal frame call
insufficient; an organ is runnable only when its intrinsic role geometry is
actually bound.
