# Semantic Substrate Affordance Map — 2026-06-20

Status: architecture map supporting ADR-0223

Companion audit: `docs/analysis/semantic-substrate-affordance-audit-2026-06-20.md`

## Purpose

This map distinguishes capabilities that are operational, prepared but disconnected, diagnostic-only, inherited debt, or absent. It also fixes the intended boundary between semantic recognition, mathematical comprehension, solving, and articulation.

## End-to-end map

```text
reviewed language packs
  |-- lexicon / scalar equivalence / units / semantic domains
  |-- [missing] reviewed mathematical construction catalog
  v
compiled immutable pack state
  |-- VocabManifold + exact CGA neighborhood
  |-- deterministic lexical normalization
  v
candidate construction proposals                 EpistemicGraph
  |  [missing for math]                           recognition evidence only
  v
deterministic role binding + hazards
  |  [narrow/local-regex scaffold today]
  v
KernelFacts -> ProblemFrame -> ContractAssessment
  |                         diagnostic only today
  v
typed closed organ input
  |  [missing]
  v
MathProblemGraph / derivation -> articulation target -> PropositionGraph
       solver-specific                           articulation-specific
```

## Capability-state legend

- **Operational** — executes in the live or diagnostic repository path with tested semantics.
- **Prepared** — underlying substrate exists but the relevant path does not consume it.
- **Diagnostic** — produces evidence but cannot change serving behavior.
- **Debt** — inherited mechanism retained for current precision, not a forward pattern.
- **Absent** — no repository mechanism currently provides the claimed capability.

## Affordance inventory

| Affordance | State | Evidence | Architectural reading | Required correction |
|---|---|---|---|---|
| Versor field transition | Operational | `algebra/versor.py`, `field/propagate.py` | Actual geometric state transition | Preserve; do not insert hot-path repair |
| Exact CGA recall | Operational | `algebra/cga.py`, `vault/store.py`, vocab manifold lookup | Exact deterministic neighborhood/recall exists | Keep exact and bounded |
| Language-pack manifold compilation | Operational | pack compiler and semantic-domain data | Reviewed lexical state can become geometric state | Reuse for construction proposal |
| Scalar equivalence | Operational | pack-backed numerics, exact `Fraction`, spans | Correct lexical normalization boundary | Extend formats only with lexical tests |
| Unit dimensions | Operational but narrow | pack-backed lookup; digit-plus-token discovery | Useful typed lexical fact | Improve token discovery without grammar creep |
| Ambiguity hazards | Operational diagnostically | centralized hazard registry and frame annotations | Corrective vocabulary exists | Make hazards participate in binding/readiness |
| `KernelFacts` | Operational diagnostically | scalars, units, entities, hazards, candidates | Stable substrate fact carrier | Preserve exact provenance and deterministic order |
| `ProblemFrame` | Operational diagnostically | builder, adequacy script, tests | Correct location for math comprehension facts | Replace local grammar with constructions incrementally |
| Process-family discovery | Diagnostic debt | hard-coded `trigger_surfaces` scan | Surface resonance is being simulated by string matching | Move reviewed declarations to pack; add exact proposal seam |
| Process role declaration | Diagnostic | candidate relations with unbound roles | Taxonomy exists, comprehension does not | Add deterministic role-binding constructions |
| Transfer role binding | Diagnostic debt | one fixed transfer regex | Demonstrates desired output shape, not general mechanism | Re-express as reviewed construction |
| Fraction/percent binding | Diagnostic debt | local quantity/entity regexes and positional whole selection | Produces some useful facts but weak topology | Close roles through explicit construction obligations |
| Target grounding | Diagnostic and narrow | “how many/how much” question object | Target is recognized as a role but direction is under-modeled | Represent target operator, state, and direction explicitly |
| Contract assessment | Diagnostic and incomplete | one material percent assessment; two skeletons | Right gate, insufficient proof | Define obligation-complete readiness |
| Construction catalog | Absent | math `frames.jsonl` is empty | No reviewed home for math constructions | Compile checksummed declarations from pack data |
| Semantic-neighborhood construction retrieval | Absent | no CGA/manifold call from builder/contracts | Geometric substrate bypassed in math comprehension | Add exact proposal-only retrieval |
| Construction proof record | Absent | candidate and binding are not strongly separated | Candidate presence can overstate readiness | Make candidate/binding/closed assessment distinct states |
| ProblemFrame-fed derivation | Absent | builder imported by scripts/tests, not organs | Diagnostics cannot retire parsers | Migrate one organ after precision proof |
| Raw-text derivation organs | Operational debt | `parse_and_solve` chain of `resolve_promotable_*` | Current serving precision comes from local parsers | Retire one-for-one after contract migration |
| No-new-legacy guard | Operational containment | allowlist-based test | Stops some expansion | Require allowlist shrink on migration |
| Recognition anti-unifier | Operational but narrow | typed slots/spans from taught patterns | A constructional precedent | Reuse principles, not its graph as math IR |
| `EpistemicGraph` | Operational in recognition | per-turn assertions/provenance | Correct recognition evidence boundary | Do not add solver state |
| `MathProblemGraph` | Operational in serving | candidate graph and derivations | Correct solver-specific structure | Accept typed closed contract through adapter |
| `PropositionGraph` | Operational in articulation | planner/target/realizer path | Correct articulation structure | Never use as comprehension mega-IR |
| Deterministic reports | Operational | serving, adequacy, morphology scripts | Enables non-serving architecture work | Add construction precision/confuser views |
| Reviewed mutation | Operational elsewhere | teaching/proposal lifecycle | Correct trust boundary | Apply to construction catalog changes |

## Source-of-truth map

### Current duplication

| Meaning | Current source | Duplicate or shadow source | Consequence |
|---|---|---|---|
| Math lexical surfaces | `en_core_math_v1/lexicon.jsonl` | organ-local phrase/regex inventories | semantic aliases drift by organ |
| Process families | `generate/process_frames.py` | derivation organ trigger logic | pack cannot review or checksum construction semantics |
| Roles | `ProcessFrame.required_roles` | local organ extraction assumptions | declared roles do not match proven inputs |
| Hazards | ambiguity registry / process frame fields | local negative checks | readiness corrections are inconsistent |
| Target meaning | `ProblemFrame` target binding | each organ's question parsing | target direction is repeatedly reinterpreted |
| Arithmetic readiness | `ContractAssessment` | organ-local promotability | diagnostic “runnable” can disagree with actual solving |

### Intended source hierarchy

```text
reviewed pack bytes
  -> compiled lexical/manifold state
  -> compiled construction declarations
  -> exact candidate evidence
  -> deterministic construction bindings
  -> ProblemFrame relations and target
  -> obligation-complete ContractAssessment
  -> typed organ adapter
```

Manifest checksums must continue to be computed from bytes written to disk. Python declarations may be generated adapters or compatibility views, but must not remain an independent semantic source of truth.

## Boundary matrix

| Structure | Owns | Must not own | Lifetime | Projection rule |
|---|---|---|---|---|
| `KernelFacts` | lexical facts, spans, normalized exact values, hazards | inferred solution or articulation | one problem parse | source facts only |
| `ProblemFrame` | entities, bindings, process candidates, bound relations, target, contract inputs | answer, token walk, prose realization | one problem comprehension | only exact/provenanced construction output |
| `ContractAssessment` | candidate organ, obligations, hazards, runnable proof state | parsing or arithmetic result | one frame assessment | runnable iff all positive and corrective obligations close |
| `EpistemicGraph` | recognition assertions and provenance | mathematical solver operations | one cognitive turn | optional typed evidence adapter only |
| `MathProblemGraph` | solver operands, operations, candidate derivations | general recognition or articulation policy | one math solve | consume closed math contract, not raw recognition graph |
| `PropositionGraph` | claims and relations needed for articulation | math comprehension and arithmetic execution | one articulation plan | receive derived claims through adapter |

This separation is the anti-mega-IR rule. Shared facts should be projected, not shared through a growing universal object.

## Construction family coverage map

### Required affordance families

| Family | Representative surfaces | Construction/chunk | Intended semantic neighborhood | Role obligations | Current support | Missing pieces and principal risk |
|---|---|---|---|---|---|---|
| Acquisition / transaction | buy, bought, purchase, acquire, get, gain, receive | actor acquires quantity of same entity; optional counterparty/cost | possession change, positive object delta, transaction | buyer, acquired entity/quantity, prior state, same-entity continuation; optional seller/price/money delta; target direction | transaction/comparison trigger candidates only | no event binding; `3` may bind to “more”; comparison or money target can be confused with acquisition |
| Loss / consumption | spend, use, eat, lose, give away, remove | owner loses/consumes quantity from prior state | possession change, negative object delta, consumption | owner, entity, lost quantity, prior/final state, ordered event, target direction | consumption/partition candidates only | no state transition; “left” can over-trigger partition; spending money vs consuming objects needs dimensions |
| Transfer | give, send, receive, sell, trade | source transfers quantity/entity to target | possession transfer, dual source/target deltas | source actor, target actor, entity, quantity; optional price/value; voice and direction | one fixed transfer regex can bind core roles | variants, pronouns, passive voice, selling/value topology; fixed regex is not a reviewed construction |
| Proportional change | decrease to, reduced to, increase to, fraction of | state becomes scale times base; question may request final or delta | scaling, state transition, part/base relation | base quantity/entity/unit, target scale, prior/final state, requested final/delta direction | scalar/unit facts may exist; no construction or contract | immediate gap for `0005`; risk of confusing “decrease by” with “decrease to” |
| Rate / frequency | per, each, every, daily, hourly, every other | numerator quantity per denominator interval/entity | dimensional rate, repeated propagation | numerator unit, denominator unit, interval/count, participant/event, target dimension | labor frame candidate; temporal contract skeleton | worker/rate/duration unbound; “every other” and monetary targets require distinct topology |
| Comparison | more than, fewer than, difference, how many more | left entity stands in directed delta/ratio relation to right | comparative ordering, directed difference, relative scale | left/right entities, comparator, amount/ratio, reference direction, delta target | comparison trigger only | “more” mistaken for entity; direction and target scope absent |
| Remainder / final state | left, remain, after, still has | ordered deltas reconstruct final or initial state | state transition, residual, inverse reconstruction | initial state, ordered deltas, final state, entity continuity, target state/direction | loose consumption/partition triggers; local serving organs | current false runnable `0393`; “left” is polysemous and cannot license a forward partition |
| Container / part-whole | box, bag, pan, group, half of, percent of | containers hold count-per contents; parts/subgroups relate to whole | containment, cardinality product, partition topology | container, content, count per, container count; or whole, part/subgroups, scale, coverage, aggregate target | container/partition candidates; weak generic percent/fraction bindings; skeletal contract | roles/topology mostly unbound; surface-local subgroup links can create false closure |

Semantic neighborhoods in this table are proposal domains, not synonym lists that automatically select operators. Each construction still requires exact binding and corrective hazards for negation, incompatible entities/units, target mismatch, and competing interpretations.

### Current closure status

| Family | Candidate detection | Bound roles today | Contract today | Serving today | Next structural obligation |
|---|---|---|---|---|---|
| Proportional decrease | None or incidental | scalar/unit only | None | local `fraction_decrease` parser | base state, final scale, entity continuity, delta target |
| Percent partition | Loose partition/consumption triggers | weak whole/subgroup/percent links | Material but unsound | local parser | topology, numeric whole, target aggregation/direction |
| Nested fraction remainder | Container trigger | none | missing-role skeleton | local parser | container, content, count-per, remainder/total direction |
| Temporal tariff/labor | Labor trigger | none | missing-role skeleton | local parser | worker, rate, duration, unit dimensions, earnings target |
| Transfer | transfer trigger and fixed regex | agent, patient, quantity, object in one shape | None | several local organs | construction variants and state transition |
| Acquisition | transaction/comparison triggers | none | None | local organs/candidate parser | actor, acquired amount, entity continuity, additive target |
| Loss/remainder | consumption/partition triggers | none | may create false percent candidate | local organs | initial state, loss event, remaining state, target direction |
| Comparison | comparison trigger | none | None | local organs | subject/reference, difference/ratio, comparison direction |
| Container/count-per | container trigger | none | missing-role skeleton | local organs | container, content, count-per, container count, requested total |

## Candidate-to-proof state machine

```text
UNSEEN
  -> PROPOSED       exact neighborhood or exact construction anchor found
  -> PARTIAL        at least one role bound with provenance
  -> AMBIGUOUS      conflicting bindings or blocking hazard
  -> CLOSED         every required role and corrective obligation proven
  -> RUNNABLE       a contract-backed organ accepts the closed projection

PROPOSED/PARTIAL/AMBIGUOUS -> REFUSED
```

Required invariants:

- `PROPOSED` cannot expose an organ input.
- `PARTIAL` cannot be serialized as runnable.
- `AMBIGUOUS` records competing bindings; it must not select one silently.
- `CLOSED` is construction closure, not an answer.
- `RUNNABLE` is specific to an organ contract; a closed construction may still have no capable organ.
- every transition is deterministic and replayable.

## Duality map: forward affordance and correction

| Forward operation | Required conjugate/correction |
|---|---|
| Semantic-neighborhood proposal | exact construction obligations and confusers |
| Scalar normalization | ambiguity and span-overlap hazards |
| Entity continuity | pronoun/reference ambiguity evidence |
| Process-family activation | negative licensing and incompatible target checks |
| Quantity binding | unit/dimension and role compatibility |
| Partition binding | topology, subgroup distinctness, and coverage |
| Target grounding | target operator, state, and direction |
| Runnable assessment | explicit missing obligations and blocking hazards |
| Serving promotion | report comparison and legacy-parser deletion |
| Reviewed pack change | checksum, deterministic compilation, and replay evidence |

## Tests that prove substrate use rather than parser growth

### Construction invariance tests

For a supported construction, vary lexical surfaces within reviewed neighborhoods while preserving role geometry. The resulting bound relation topology and normalized quantities must remain identical, modulo source spans.

### Confuser tests

Hold surface vocabulary roughly constant while changing target direction, event roles, negation, temporal order, inverse/forward form, or entity continuity. The incorrect construction must remain partial, ambiguous, or refused.

### Proposal/proof separation tests

A close semantic-neighborhood match with missing roles must produce a candidate but never a runnable assessment. This is the direct test that CGA is proposing rather than deciding.

### Projection tests

A closed construction projects only consumer-required fields into `ProblemFrame`, `MathProblemGraph`, or recognition evidence. No graph acquires fields owned by another layer.

### Retirement tests

When an organ migrates, remove its legacy parser from the no-new-legacy allowlist and prove equivalent or stricter serving behavior. A new substrate path without deletion is incomplete migration.

## Decision checkpoints

1. **After proportional closure:** train `0005` is runnable, train `0046` remains runnable, holdout `0393` is not runnable, and serving wrong IDs remain empty.
2. **After construction catalog:** no independent Python trigger taxonomy remains authoritative; pack bytes and checksums are the source.
3. **After neighborhood proposal:** confuser precision proves semantic proximity alone cannot grant closure.
4. **After first organ migration:** the organ consumes a typed closed contract and its local raw-text parser is removed.
5. **Before broader rollout:** exact CGA cost and deterministic construction matching meet hot-path performance requirements without caching mutable state.

## Architectural conclusion

CORE already has the lower substrate and the upper cognitive pipeline. The missing middle is a reviewed construction layer that turns semantic resonance into proven relational affordances. The correct bridge is not a universal parse tree and not another derivation regex. It is a deterministic candidate-and-correction boundary whose closed output can be projected into the existing purpose-specific graphs.
