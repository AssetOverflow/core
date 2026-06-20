# Semantic-Substrate Problem-Solving Master Plan — 2026-06-20

**Status:** proposed implementation plan for architect ratification

**Scope:** math/problem-solving comprehension from substrate proposal through verified derivation

**Governing evidence:** ADR-0223 and its 2026-06-20 audit pack

**Behavioral effect of this document:** none; this is architecture and sequencing only

This plan assumes the merged baseline at `main@60df4fc0` (#833). It does not
authorize serving changes, report mutation, benchmark-case mutation, sealed-artifact
access, pack mutation, or parser deletion. Each material step below remains a separate,
reviewable PR with its own evidence.

## 1. Executive thesis

CORE must replace the current relationship between comprehension and solving:

```text
raw problem text
  -> ordered list of organ-local recognizers
  -> organ-local extraction and arithmetic
  -> answer admission
```

with a constructional, substrate-mediated relationship:

```text
surface chunk
  -> exact semantic-neighborhood proposal
  -> constructional affordance candidate
  -> role-obligation template
  -> exact span grounding
  -> ProblemFrame relation and target
  -> obligation-complete ContractAssessment
  -> typed organ input
  -> independently verified derivation
  -> existing answer admission and articulation
```

The intrinsic space is not a sequence of words and not a bag of numbers. It is a
typed relational field over source spans, entities, quantities, units, events,
states, target operators, temporal order, hazards, and proof obligations. Surface
language is a probe into that field. A probe may resonate with several construction
families, but it cannot determine one by proximity alone.

The governing law is:

```text
semantic closeness proposes;
exact bindings ground;
organ-specific contracts determine;
verification admits;
otherwise CORE refuses.
```

Local raw-text organs are the wrong long-term foundation because each one privately
reconstructs the same semantic facts—entities, quantities, state changes, target
direction, units, and hazards—with different regexes and different failure modes.
That duplicates meaning, makes confuser coverage non-compositional, and prevents a
single correction from improving more than one capability. It also creates a false
choice between broadening a parser and refusing: the missing third door is a reusable
construction layer that can propose broadly while proving narrowly.

The semantic substrate should therefore become the source of *candidate
constructions*, not answers or operators. Reviewed pack entries and exact CGA
neighborhood scans should make `buy`, `purchase`, `acquire`, `gain`, and `receive`
available as related probes. A declarative construction signature should then ask
whether a particular chunk closes roles such as buyer, acquired quantity, acquired
entity, prior state, and target. Hazards provide the conjugate correction: negation,
money targets, entity discontinuity, comparison readings, and incompatible units can
block closure even when the lexical neighborhood is strong.

This transformation is deliberately incremental. The current serving organs remain
the precision reference while `ProblemFrame` builds richer diagnostic evidence.
Only a contract that is runnable from `ProblemFrame` alone, stable under morphology,
blocked by near confusers, deterministic on replay, and parity-checked against the
existing organ may be considered for serving migration. Migration is complete only
when the legacy raw-text parser and its allowlist entry are deleted. Adding a second
path without retiring the first is not migration.

The program optimizes for truthful reusable comprehension, not short-term GSM8K
score. A reduction in runnable count is progress when it removes a false runnable.
The hard safety floor remains `wrong_ids == []`.

## 2. Current-state map

### 2.1 What exists and is sound

| Capability | Evidence | Architectural status |
|---|---|---|
| Geometric field transitions | `algebra/versor.py`, `field/propagate.py` | Live and load-bearing; preserve `versor_condition(F) < 1e-6`. |
| Exact CGA neighborhood/recall | `algebra/cga.py`, `algebra/backend.py`, `vocab/manifold.py`, `vault/store.py` | Exact deterministic scan exists; no ANN, cosine substitution, or stochastic ranking is needed. |
| Checksummed language-pack compilation | `language_packs/compiler.py`, manifests, immutable pack bytes | Correct reviewed source boundary for lexical state. |
| Exact scalar normalization | `language_packs/scalar_equivalence.py`, `language_packs/numerics_loader.py` | Produces exact `Fraction` values and source spans. |
| Unit and dimension facts | `language_packs/unit_dimensions.py` | Useful typed lexical facts; coverage is narrow but the boundary is sound. |
| Central ambiguity vocabulary | `language_packs/ambiguity_hazards.py` | Correct place for reusable corrective conditions. |
| Provenance-bearing kernel facts | `generate/kernel_facts.py` | Immutable facts, exact spans, and provenance distinctions are sound. |
| Purpose-specific graph separation | `ProblemFrame`, `EpistemicGraph`, math state, `PropositionGraph` | Healthy separation; preserve it. |
| Existing math verifier/admission discipline | derivation verification and GSM8K runner | The `wrong == 0` safety posture is the reference constraint. |
| Reviewed learning/promotion boundaries | `teaching/*`, ADR-0218, Vault invariants | Construction/catalog changes must use the same proposal/review discipline. |

### 2.2 What exists but is diagnostic only

`build_problem_frame()` extracts scalars, units, hazards, process candidates,
mentions, bindings, relations, and a bound question target. The adequacy and
morphology scripts expose candidate and runnable contract counts. None of this
changes serving. That is correct at the current maturity level.

`ContractAssessment` is the correct kind of gate but currently carries a coarse
`runnable: bool` and incomplete obligations. The material percent-partition
assessment can report closure without proving numeric-whole provenance, partition
topology, subgroup distinctness/coverage, or target direction.

### 2.3 What bypasses the intended design

- `generate/math_candidate_graph.py::parse_and_solve` invokes a sequence of
  `resolve_promotable_*` functions with raw problem text.
- `generate/derivation/fraction_decrease.py` and
  `generate/derivation/percent_partition.py` independently parse prose, bind values,
  reject confusers, derive answers, and self-verify.
- `ProblemFrame` is imported by diagnostics and tests, not by the serving organs.
- The no-new-legacy test contains the spread but does not shrink it until a migrated
  parser is removed from its allowlist.

### 2.4 What is named like substrate but is still local parsing

- `generate/process_frames.py` declares useful family/role vocabulary, but family
  discovery is a hard-coded `trigger_surfaces` string scan.
- `_ENTITY_AFTER_QUANTITY_RE`, `_FRACTION_ENTITY_RE`, `_ACTOR_VERB_RE`, and
  `_TRANSFER_RE` in `problem_frame_builder.py` are bounded diagnostic scaffolds, not
  semantic-substrate retrieval.
- Percent/fraction relations currently use local surface patterns and a positional
  first-whole heuristic.
- Question binding recognizes a small `how many/how much` surface and under-models
  operator, state, scope, and direction.
- `en_core_math_v1/frames.jsonl` is zero bytes. The manifest pins the SHA-256 of empty
  bytes, so the math pack does not yet carry reviewed construction semantics.

Renaming any of these mechanisms to “affordance retrieval” without changing its
authority, evidence, and tests would be relabeling, not architectural progress.

### 2.5 What must not be touched yet

- Do not wire `ProblemFrame` into `math_candidate_graph.py` during diagnostic
  construction work.
- Do not edit derivation organs in the proportional-closure PR.
- Do not change serving thresholds, report files, case files, sealed artifacts, or
  answer labels.
- Do not add normalization to `generate/`, propagation, Vault, or telemetry paths.
- Do not alter `determine()` or introduce `FrameVerdict`; ADR-0222 remains proposed
  and closed-world semantics are unrelated to math contract readiness.
- Do not turn `PropositionGraph` or `EpistemicGraph` into the math comprehension IR.
- Do not delete a legacy parser before a typed, verified replacement has passed
  shadow parity and confuser evidence.

## 3. Target architecture

### 3.1 End-to-end flow

```text
reviewed pack bytes
  -> compiled lexical manifold + compiled construction catalog
  -> chunk probes
  -> exact semantic-neighborhood proposals
  -> construction candidates and role-obligation templates
  -> exact span/fact binding + competing-binding record
  -> ProblemFrame relations, states, dimensions, hazards, and question target
  -> organ-specific ContractAssessment
  -> immutable typed organ projection
  -> verified derivation / proof
  -> existing admission and articulation
  -> deterministic replay evidence
  -> reviewed proposal gate for durable learning
```

### 3.2 Layer contracts

| Layer | Allowed input | Required output | Must never do |
|---|---|---|---|
| Surface chunking | Original problem text and deterministic token/span boundaries | Ordered chunks with exact character spans | Normalize field state, infer answers, use labels/case IDs, or erase original spans. |
| Semantic-neighborhood proposal | Chunk probes, compiled manifold, reviewed candidate subset | Deterministically ranked candidate construction IDs plus lexical evidence and exact CGA scores | Treat score as proof; choose an operator; use ANN/HNSW/cosine/randomness; mutate packs. |
| Construction catalog | Reviewed, checksummed data-only pack records | Immutable construction signature, role obligations, hazards, candidate relation/operator families | Execute code from pack data; contain organ logic; encode benchmark case IDs; become a universal grammar. |
| Construction binder | Candidate signature, chunk spans, `KernelFacts`, local discourse evidence | Zero or more explicit role bindings, competing bindings, and blocker evidence | Reparse in a derivation organ; invent missing roles; silently resolve ambiguity; compute the answer. |
| `ProblemFrame` | Kernel facts and bound construction evidence | Purpose-specific math facts: entities, quantities, units, state/event relations, target semantics, hazards, provenance | Own epistemic standing, articulation policy, solver steps, or an answer. |
| `ContractAssessment` | One `ProblemFrame` and one organ contract | Candidate/blocked/runnable state, closed obligations, blockers, hazards, and evidence spans | Parse raw text, perform arithmetic, fall back to a legacy parser, or grant generic readiness. |
| Typed organ adapter | A runnable, contract-specific assessment and frame | Minimal immutable organ input with exact values, units, target, and provenance | Pass raw prose, drop target direction/provenance, or project fields for unrelated organs. |
| Derivation organ | Typed closed input | Derivation steps and proof/verification material | Recover missing semantics from raw text; mutate memory; bypass verification. |
| Admission/articulation | Verified derivation and existing runtime policy | Existing answer/surface record with trace evidence | Promote an unverified candidate; collapse walk/articulation/surface contracts. |
| Replay/learning gate | Canonical construction, binding, contract, derivation, and verdict evidence | Stable digest and, when reviewed, a proposal | Directly mutate catalog, packs, identity, policy, or Vault standing. |

### 3.3 State machine

```text
UNSEEN
  -> PROPOSED       semantic or exact construction evidence exists
  -> PARTIAL        at least one required role is grounded
  -> AMBIGUOUS      competing bindings or a blocking hazard remains
  -> CLOSED         all construction roles and corrections are proven
  -> RUNNABLE       a named organ contract accepts a typed projection
  -> VERIFIED       the organ derives and the independent verifier accepts
  -> MIGRATED       serving consumes the typed path
  -> RETIRED        the legacy parser and allowlist entry are deleted

PROPOSED | PARTIAL | AMBIGUOUS | CLOSED -> REFUSED when no licensed transition exists
```

`CLOSED` is construction closure, not answer correctness. `RUNNABLE` is specific to
one organ. `VERIFIED` does not grant epistemic promotion or durable learning.

## 4. Constructional affordance catalog plan

### 4.1 Minimal catalog shape

Use the existing checksummed pack compilation boundary, but version the current
frame artifact into a safe data-only construction catalog. A record needs only:

```text
construction_id
family
semantic_domain anchors
declarative chunk signature
required role declarations
optional role declarations
candidate relation families
candidate operator families
blocking/advisory hazard IDs
negative licenses
provenance/evidence hashes
schema version
```

The signature format must be closed and non-executable: ordered anchor sets, typed
slots, span adjacency/scope constraints, and reference requirements. No Python,
dynamic import, arbitrary regex, template code, or answer expression belongs in
pack data. Exact arithmetic and organ-specific obligations remain outside the
catalog.

Start with one or two reviewed signatures per family. Expand only when morphology
and confuser tests prove the same geometry across surface variants.

### 4.2 Initial families

#### Proportional change

| Axis | Initial design |
|---|---|
| Semantic neighborhood | decrease, reduce, lower, increase, raise, grow; to/by/of; fraction/percent scales |
| Signatures | `state decreases to scale of base`; later `state decreases by scale of base` and `state increases to/by scale` as distinct constructions |
| Required roles | state/entity, prior/base quantity, scale, transition kind (`to` vs `by`), question target operator and direction |
| Optional roles | unit, actor/causer, duration/time anchor, explicit final state |
| Hazards/confusers | final-value vs delta target, affine “fraction more than,” percent-change vs percent-of, multiple scales, ambiguous base, negation, unit mismatch |
| Candidate operators | `scale_final_state`, `difference_from_base`; candidates only |
| Tests | lexical invariance; `0005` positive; final-value, affine, multiple-fraction, unit/entity mismatch, and ambiguous-base refusals |
| Readiness | exactly one base/scale/state transition; `0 < scale < 1` for decrease; entity/unit continuity; explicit delta target for `fraction_decrease`; no blocker |

#### Acquisition / transaction

| Axis | Initial design |
|---|---|
| Semantic neighborhood | buy, purchase, acquire, get, receive, gain, collect; sell/pay/cost as related but distinct transaction probes |
| Signatures | `actor acquires quantity of entity`; `buyer purchases quantity at price`; money-target constructions remain separate |
| Required roles | acquirer/buyer, acquired quantity, acquired entity, event direction, target state |
| Optional roles | seller, unit price, total cost, money delta, prior possession state, time |
| Hazards/confusers | “more” comparison, target asks cost/change, entity mismatch, sale direction, negation, division/fraction subproblem |
| Candidate operators | positive possession delta, total cost, remaining money; contract chooses at most one |
| Tests | `buy/purchase/acquire/receive` topology invariance; money-target and comparison confusers; same-entity continuation; passive voice later |
| Readiness | acquisition event and target refer to the same possession entity; quantity is grounded; target chooses final possession or a separately licensed money contract |

#### Transfer

| Axis | Initial design |
|---|---|
| Semantic neighborhood | give, hand, pass, send, donate, lend, receive, sell, trade |
| Signatures | `source transfers quantity/entity to recipient`; inverse voice is a distinct surface signature over the same relation |
| Required roles | source actor, recipient actor, quantity, transferred entity, direction |
| Optional roles | price/value, unit, prior/final state for either participant, time |
| Hazards/confusers | pronoun ambiguity, passive voice, sell-vs-give value topology, omitted recipient, negation, source/target reversal |
| Candidate operators | paired negative/positive possession deltas; optional value exchange |
| Tests | active variants; source/recipient reversal; missing recipient; pronoun collision; sale with money target |
| Readiness | distinct source/recipient, one grounded quantity/entity, explicit direction, target participant/state, and no unresolved reference hazard |

#### Loss / consumption

| Axis | Initial design |
|---|---|
| Semantic neighborhood | use, spend, eat, consume, lose, remove, discard, give away |
| Signatures | `owner consumes quantity of entity`; `owner loses quantity from prior state` |
| Required roles | owner/affected entity, consumed/lost quantity, resource entity, negative direction, target state |
| Optional roles | prior state, final state, rate, recipient for give-away, time |
| Hazards/confusers | spending money vs consuming objects, “lose weight” goal, gain verb currently mixed into consumption, target asks consumed amount vs remainder, negation |
| Candidate operators | negative possession delta, remainder/final state |
| Tests | use/spend/eat variants; money dimension; goal-language refusal; consumed-vs-remaining target pairs |
| Readiness | resource dimension and entity continuity proven; event ordered after prior state; target explicitly requests loss or final remainder |

#### Rate / per / each

| Axis | Initial design |
|---|---|
| Semantic neighborhood | per, each, every, hourly, daily, rate, for each |
| Signatures | `numerator quantity per denominator unit/entity`; `count repeated for each member/interval` |
| Required roles | numerator quantity/dimension, denominator quantity/dimension, participant/event, requested output dimension |
| Optional roles | duration, count of instances, schedule window, currency, conversion fact |
| Hazards/confusers | occurrence “times,” every-other schedule, unit inversion, per-total ambiguity, incompatible dimensions |
| Candidate operators | dimensional product/quotient, repeated propagation |
| Tests | rate-axis swaps; each/per paraphrases; incompatible units; occurrence-times confusers; exact unit conversion |
| Readiness | numerator/denominator axes are explicit, dimensions compose to target dimension, repetition count/window is grounded, no inferred conversion |

#### Comparison

| Axis | Initial design |
|---|---|
| Semantic neighborhood | more than, fewer than, less than, difference, twice/as many, greater/smaller |
| Signatures | `subject is additive delta from reference`; `subject is multiplicative scale of reference`; `question requests directed difference` |
| Required roles | subject entity/quantity, reference entity/quantity, comparator kind, amount/scale, direction, target |
| Optional roles | unit, time/state scope, equality anchor |
| Hazards/confusers | “more” in acquisition, reversed reference, additive vs multiplicative reading, occurrence “times,” missing subject |
| Candidate operators | directed difference, affine projection, scale relation |
| Tests | role-reversal pairs; additive/multiplicative pairs; acquisition confuser; question-direction pairs |
| Readiness | comparator family and reference direction are explicit; both entities/quantities share a compatible dimension; target scope is grounded |

#### Remainder / final state

| Axis | Initial design |
|---|---|
| Semantic neighborhood | left, remain, remaining, after, still has, final, originally |
| Signatures | `initial state followed by ordered deltas yields final state`; `known final plus licensed deltas reconstructs initial` is a distinct inverse construction |
| Required roles | state entity, state direction, ordered event/delta set, known state, requested state |
| Optional roles | actor, unit, intermediate states, time anchors |
| Hazards/confusers | adjectival/directional “left,” inverse topology, omitted initial state, unordered events, entity discontinuity |
| Candidate operators | forward state fold, inverse reconstruction; never interchangeable |
| Tests | forward/inverse pairs; `0393` remains blocked for forward percent partition; lexical “left” confusers; event-order permutations |
| Readiness | target state/direction explicit; every delta is bound and ordered; entity/unit continuity holds; organ explicitly licenses forward or inverse topology |

#### Container / part-whole

| Axis | Initial design |
|---|---|
| Semantic neighborhood | box, bag, crate, pack, group, part, half, percent of, portion, whole |
| Signatures | `N containers each contain M entities`; `whole partitioned into distinct subgroups`; `scale of subgroup has property` |
| Required roles | container/content/count-per/container-count, or whole/part/scale/subgroup identity/coverage; target aggregation |
| Optional roles | remainder, capacity, loose items, nested container, actor |
| Hazards/confusers | subgroup alias collision, incomplete coverage, final remainder mistaken for whole, nested partition, count-vs-capacity |
| Candidate operators | cardinality product, partition allocation, subgroup aggregation |
| Tests | `0046` positive; subgroup identity/coverage negatives; `0393` inverse blocker; nested container and loose-item confusers |
| Readiness | numeric whole precedes and scopes the partition; required subgroups are distinct and covered; scales bind to the correct subgroup; target is forward aggregate |

#### Temporal / schedule

| Axis | Initial design |
|---|---|
| Semantic neighborhood | before, after, during, hour/day/week, every other, schedule, starts/ends, for N hours |
| Signatures | `event lasts duration`; `event recurs over interval`; `ordered events/states anchored in time` |
| Required roles | event, duration/interval, temporal order or recurrence rule, target temporal quantity |
| Optional roles | start/end, participant, rate, calendar fact, exception window |
| Hazards/confusers | clock time vs duration, every-other parity, inclusive endpoints, unrelated forecast duration, calendar/world-fact provenance |
| Candidate operators | duration sum/difference, recurrence count, schedule projection |
| Tests | clock-vs-duration; inclusive/exclusive boundary; forecast-duration confuser for `0005`; calendar provenance refusal |
| Readiness | time quantities have correct dimension and scope; order/recurrence is explicit; any calendar fact has kernel provenance; target is temporal |

#### Unit / currency relations

| Axis | Initial design |
|---|---|
| Semantic neighborhood | dollars/cents, degrees, miles, hours, items; cost, worth, change; pack-backed unit aliases |
| Signatures | `quantity bears unit`; `exact compatible conversion`; `currency amount per item/time`; `money remainder/change` |
| Required roles | scalar, unit, dimension, target dimension; both endpoints for conversion |
| Optional roles | currency denomination, rate denominator, entity counted, exact conversion fact |
| Hazards/confusers | count noun classified as unit, money vs item quantity, temperature change vs final temperature, unsupported conversion, mixed currencies |
| Candidate operators | identity/unit binding, exact conversion, dimension composition; no approximate conversion |
| Tests | compatible/incompatible dimensions; exact ratio replay; money/item target pairs; unit continuity across state change |
| Readiness | every arithmetic operand has a compatible role dimension; conversions come from exact reviewed facts; target unit/dimension is proven |

## 5. Immediate PR sequence

The sequence separates obligation soundness, catalog authority, proposal geometry,
role binding, organ adaptation, and serving migration. Later PRs may split further;
they must not collapse gates to chase score.

### PR 1 — proportional closure and readiness correction

| Field | Plan |
|---|---|
| Title | `feat(kernel): close proportional-decrease contracts and make readiness obligation-sound` |
| Branch | `codex/problemframe-proportional-change-closure` |
| Purpose | Make train `0005` diagnostically runnable from `ProblemFrame`; keep `0046` runnable under explicit obligations; make holdout `0393` non-runnable. |
| Likely files | `generate/kernel_facts.py`, `generate/problem_frame.py`, `generate/problem_frame_builder.py`, `generate/problem_frame_contracts.py`, `generate/process_frames.py`, `scripts/gsm8k_problem_frame_adequacy.py`, `scripts/gsm8k_substrate_morphology.py`, focused tests listed in §6. |
| Non-goals | No derivation-organ edits, `math_candidate_graph.py`, serving wire, catalog compilation, pack bytes, report/case/sealed files, answer derivation, or score lift. |
| Tests | Builder/contract positives, target-direction and topology confusers, deterministic replay, adequacy metrics, no-new-legacy, serving reports in memory. |
| Expected movement | Train runnable `1 -> 2` (`0005`, `0046`); holdout runnable `1 -> 0`; serving remains train `30/20/0`, holdout `5/495/0`, `wrong_ids=[]`. |
| Safety gates | Contract reads only `ProblemFrame`; no raw-text fallback; exact spans; false-runnable removal required; no serving diff. |
| Agent | Codex/Opus at high reasoning for implementation; XHIGH performs merge-blocker review. Grok is not appropriate for the semantic design. |

### PR 2 — explicit readiness stages and evidence accounting

| Field | Plan |
|---|---|
| Title | `feat(kernel): type contract readiness stages and blockers` |
| Branch | `codex/problemframe-readiness-stages` |
| Purpose | Replace headline dependence on a boolean with candidate/blocked/runnable/verified/migrated diagnostic stages while retaining organ-specific assessments. |
| Likely files | `generate/problem_frame_contracts.py`, adequacy/morphology scripts, focused tests, runtime-contract documentation if a public diagnostic schema changes. |
| Non-goals | No new constructions, organ adapters, serving, or generic solver state. |
| Tests | Serialization/order, illegal stage combinations, blocker preservation, false-runnable accounting, report schema determinism. |
| Expected movement | Counts become more honest; numerical runnable count need not rise. `0393` appears as blocked with stable gap codes. |
| Safety gates | A stage is derived, never user asserted; `verified`/`migrated` cannot be constructed without their evidence; no answer labels enter assessment. |
| Agent | Codex/Opus; cheaper agent may verify report diffs mechanically after design is frozen. |

### PR 3 — reviewed construction catalog foundation

| Field | Plan |
|---|---|
| Title | `feat(packs): compile reviewed math construction catalog` |
| Branch | `codex/math-construction-catalog` |
| Purpose | Give construction signatures, roles, hazards, and negative licenses a checksummed source of truth in reviewed pack bytes. Seed proportional decrease and a minimal cross-family set. |
| Likely files | `language_packs/compile_frames.py`, a typed frame/construction loader, `language_packs/schema.py` or manifest validation, `language_packs/data/en_core_math_v1/frames/*.jsonl`, compiled `frames.jsonl`, manifest checksum, pack/compiler tests. |
| Non-goals | No runtime proposal retrieval, no organ logic in data, no broad grammar, no dynamic regex/code, no serving. |
| Tests | Canonical bytes, checksum-from-written-bytes, schema rejection, deterministic ordering, unknown field/version failure, source/compiled parity. |
| Expected movement | No serving or runnable change. Empty math-frame checksum becomes a reviewed non-empty artifact. |
| Safety gates | Data-only closed schema; pack mutation reviewed; no executable fields; provenance/evidence hashes mandatory. |
| Agent | XHIGH defines the schema; Codex/Opus implements. Grok may perform only exact manifest/fixture updates after schema approval. |

### PR 4 — exact semantic-neighborhood proposal seam

| Field | Plan |
|---|---|
| Title | `feat(kernel): propose constructions through exact substrate neighborhoods` |
| Branch | `codex/exact-construction-proposals` |
| Purpose | Map chunk probes to catalog construction candidates using mounted pack manifold points and exact CGA inner-product scans over a reviewed candidate set. |
| Likely files | new narrow `generate/construction_proposals.py`, catalog loader, `vocab/manifold.py` only if an exact top-k evidence API is unavoidable, `problem_frame_builder.py` integration for diagnostic candidates, tests. |
| Non-goals | No readiness authority, operator selection, approximate retrieval, learned threshold, mutable cache, or serving. |
| Tests | Exact replay/order/tie behavior, lexical-neighborhood invariance, unrelated-neighbor rejection, proposal-with-missing-roles never runnable, backend parity if manifold API changes. |
| Expected movement | Candidate recall may rise; runnable must not rise solely from proximity. |
| Safety gates | Exact O(N) CGA scan; bounded reviewed candidate indices; scores retained as proposal evidence only; existing field closure unchanged. |
| Agent | XHIGH architecture plus Codex/Opus implementation and review. Do not assign geometric threshold semantics to a cheap agent. |

### PR 5 — acquisition, transfer, and loss state-change bindings

| Field | Plan |
|---|---|
| Title | `feat(kernel): bind possession-change constructions` |
| Branch | `codex/problemframe-possession-change-bindings` |
| Purpose | Close reusable event/state roles for acquisition, transfer, and consumption/loss without solving. Replace the fixed transfer regex for migrated diagnostic signatures. |
| Likely files | construction catalog records, binder module, `problem_frame_builder.py`, `kernel_facts.py`/`problem_frame.py` only for reusable typed state/event roles, hazards, tests. |
| Non-goals | No generic event parser, no money solver, no serving migration, no raw-text organ fallback. |
| Tests | Morphology invariance, actor/recipient reversal, money-vs-object target, negation, entity continuity, competing interpretations, deterministic spans. |
| Expected movement | More `PARTIAL` and `CLOSED` possession constructions; runnable may remain unchanged until named contracts exist. |
| Safety gates | Competing candidates preserved; event direction explicit; no candidate implies addition/subtraction by itself. |
| Agent | Codex/Opus with XHIGH review of role topology. Grok may add pre-specified fixture variants only. |

### PR 6 — dimensional, temporal, comparison, and part-whole closure

| Field | Plan |
|---|---|
| Title | `feat(kernel): close dimensional and relational construction topologies` |
| Branch | `codex/problemframe-relational-topology` |
| Purpose | Bind rate axes, unit/currency dimensions, comparison direction, temporal scope, container/part-whole coverage, and forward/inverse state targets. Split if review size exceeds one coherent topology. |
| Likely files | catalog records, binder and target modules, unit/hazard facades where coverage is genuinely lexical, `problem_frame*`, diagnostics, tests. |
| Non-goals | No universal IR, inferred conversions, calendar guessing, serving, or generic parser. |
| Tests | Axis swaps, incompatible dimensions, target-direction pairs, subgroup distinctness/coverage, remainder inverse/forward pairs, event order. |
| Expected movement | Blocker taxonomy becomes more specific; legitimate closed contracts rise only per family; false-runnable count remains zero. |
| Safety gates | Exact units/conversions only; topology-specific contracts; no structure is shared by expanding `EpistemicGraph` or `PropositionGraph`. |
| Agent | XHIGH should split/ratify topology; Codex/Opus implements bounded slices. Mechanical agents only after exact contracts are written. |

### PR 7 — ProblemFrame-only fraction-decrease adapter and shadow parity

| Field | Plan |
|---|---|
| Title | `feat(math): derive fraction decrease from a closed ProblemFrame contract` |
| Branch | `codex/fraction-decrease-problemframe-shadow` |
| Purpose | Add the first immutable typed projection and a ProblemFrame-fed derivation entry point; run it in diagnostics/shadow evidence only. |
| Likely files | new contract-specific adapter/input type, `generate/derivation/fraction_decrease.py` refactored so arithmetic consumes typed input, shadow/parity harness, tests; no serving branch yet. |
| Non-goals | No fallback from typed input to raw text; no serving selection; no parser deletion until parity passes. |
| Tests | Typed input construction, exact arithmetic, verifier parity, positive morphology, confusers, legacy-vs-frame shadow comparison, deterministic proof evidence. |
| Expected movement | One `ProblemFrame-only verified contract`; serving metrics unchanged. |
| Safety gates | The typed entry point accepts no problem text; adapter accepts only runnable assessment; discrepancies refuse and block migration. |
| Agent | Codex/Opus high reasoning; XHIGH reviews the adapter boundary and parity evidence. |

### PR 8 — migrate fraction decrease and retire its parser

| Field | Plan |
|---|---|
| Title | `refactor(math): serve fraction decrease from ProblemFrame and retire raw parser` |
| Branch | `codex/fraction-decrease-parser-retirement` |
| Purpose | Wire the verified typed path into existing admission, remove raw-prose parsing from the organ, and shrink the legacy allowlist. |
| Likely files | `generate/math_candidate_graph.py`, `generate/derivation/fraction_decrease.py`, typed adapter, no-new-legacy allowlist/test, serving/confuser tests, runtime contract docs only if externally visible behavior changes. |
| Non-goals | No second organ migration, score-chasing broadening, fallback parser, or report mutation. |
| Tests | Full shadow parity, serving train/holdout/confusers, verifier evidence, no-new-legacy shrink, architectural invariants, smoke/full relevant lanes. |
| Expected movement | Serving should remain at least `30/20/0` train and `5/495/0` holdout with `wrong_ids=[]`; capability lift is optional. Parser-retirement count improves by one. |
| Safety gates | Any legacy/frame disagreement refuses; raw parser and allowlist entry removed in the same PR; no hidden fallback. |
| Agent | Codex/Opus implements; XHIGH performs mandatory merge-blocker review. Grok should not own the migration. |

### PR 9 — readiness/replay inspection projection

| Field | Plan |
|---|---|
| Title | `feat(workbench): expose substrate construction evidence` |
| Branch | `codex/workbench-construction-evidence` |
| Purpose | Project already-persisted or explicitly journaled construction candidates, bindings, blockers, and readiness stages into Workbench without claiming live capability. |
| Likely files | curated runtime/workbench schemas and readers, API projection, UI trace components, tests; exact files chosen only after persistence review. |
| Non-goals | No UI-driven mutation, replay in browser, raw field arrays, synthetic green stages, or capability claims. |
| Tests | Missing-evidence honesty, deterministic projection, no raw field persistence, accessibility/UI tests, replay divergence. |
| Expected movement | Operator inspectability only; no serving/readiness movement. |
| Safety gates | UI labels diagnostic vs migrated explicitly; absent evidence stays absent; work waits until the core evidence schema is stable. |
| Agent | Codex/Opus for schema; cheaper agent may implement frozen UI mechanics. XHIGH reviews claims and persistence boundaries. |

## 6. Proportional-decrease implementation plan

PR 1 remains the correct next implementation PR. The repository evidence does not
justify migrating `percent_partition`, broadening process triggers, or touching
serving first.

### 6.1 Bind `decrease_to_fraction`

Add a diagnostic proportional-change construction that consumes existing scalar,
unit, mention, and span facts at the `ProblemFrame` construction boundary.

For `0005`, emit one bound relation:

```text
relation_type = decrease_to_fraction
roles:
  base_quantity -> grounded scalar 84
  scale -> grounded scalar 3/4
  state_entity -> exact “temperature” mention
  unit -> exact “degrees” mention/fact
  transition -> exact “decrease to” span
```

The relation must preserve the original double-space source text and exact character
spans. `scale` and `base_quantity` bind by fact identity, not by numeric position.
The relation may be proposed only when the construction distinguishes `decrease to`
from `decrease by` and from affine `fraction more than` surfaces.

This PR is an obligation-closing diagnostic bridge, not the final semantic-neighborhood
implementation. Any temporary signature declaration must live at the construction
boundary, be explicitly marked for catalog migration in PR 3, and must not be called
geometric substrate retrieval.

### 6.2 Represent delta question targets

Extend target semantics so the bound target carries at least:

```text
target_operator = difference
target_state = delta
target_direction = decrease
target_entity = same state entity as the relation
unknown_slot = delta_quantity
```

Do not encode this as a free-form `unknown` string alone. Illegal combinations such as
`target_state=final` with `target_operator=difference` should be rejected by typed
construction or explicit validation. Preserve the exact question span
`what will the temperature decrease by?`.

### 6.3 Make `fraction_decrease` runnable for train `0005`

Add `assess_fraction_decrease(frame)` and emit it only when a
`decrease_to_fraction` relation exists. Its positive obligations are:

1. exactly one base quantity and one scale are bound by fact identity;
2. `0 < scale < 1` for this organ;
3. state entity continuity is proven between transition and target;
4. unit/dimension continuity is proven when a unit is present;
5. target explicitly requests the decrease delta, not the final state;
6. all relation and target spans are provenance-bearing;
7. no blocking hazard or competing construction remains.

`runnable=True` means only that a future typed adapter could construct every input the
existing organ requires. It must not calculate 21, call the organ, or affect serving.

### 6.4 Keep confusers blocked

Required negative fixtures:

- `decrease to 3/4 ... what is the final temperature?` — closed proportional
  construction, not runnable for the delta organ;
- `3/4 more than 84` — affine comparison, not proportional decrease;
- `decrease by 3/4 of 84` — distinct transition semantics, not silently treated as
  `decrease to`;
- multiple fraction scales or multiple candidate bases — ambiguous/refuse;
- forecast duration (`one hour`) — never chosen as the base;
- entity discontinuity (`temperature ... decrease in pressure`) — block;
- incompatible units across state/target — block;
- negated or hypothetical decrease — block unless explicitly supported later.

### 6.5 Remove false percent-partition runnable holdout `0393`

Tighten `assess_percent_partition` to require the organ's actual forward topology:

1. a numeric original whole bound to the whole entity before partition events;
2. explicit subgroup identities, distinctness, and required coverage;
3. each scale linked to the correct subgroup by mention/fact identity rather than
   lowercase surface equality;
4. a forward aggregation target over subgroup results;
5. no final-state/remainder quantity used as the original whole;
6. no inverse-reconstruction target.

For `0393`, the grounded `28 chocolates left` is a final state and the question asks
for the original state. The current forward `percent_partition` organ does not license
that inverse topology. The assessment must therefore be blocked with stable reasons
such as `inverse_topology_unlicensed` and `original_whole_unbound`; it must not infer
80 or route to another organ.

Train `0046` remains runnable only if the frame proves the numeric whole `100 students`,
the girls/boys half partition, distinct subgroup bindings, both percentages linked to
their respective subgroup, and the forward aggregate target `students own dogs`.

### 6.6 Files and tests

Expected production edits are limited to the diagnostic substrate path:

- `generate/kernel_facts.py`
- `generate/problem_frame.py`
- `generate/problem_frame_builder.py`
- `generate/problem_frame_contracts.py`
- `generate/process_frames.py` only if a proportional-change candidate declaration is
  required
- `scripts/gsm8k_problem_frame_adequacy.py`
- `scripts/gsm8k_substrate_morphology.py`

Focused tests:

- `tests/test_problem_frame_skeleton.py`
- `tests/test_problem_frame_builder.py`
- `tests/test_problem_frame_contracts.py`
- `tests/test_gsm8k_problem_frame_adequacy.py`
- `tests/test_gsm8k_morphology_missing_kernel_labels.py`
- a new narrow proportional-change/confuser test file if keeping the existing files
  readable
- `tests/test_kernel_no_new_legacy_derivation_surfaces.py`

Forbidden edits in PR 1:

- `generate/derivation/*`
- `generate/math_candidate_graph.py`
- `evals/**/report.json`
- any `cases.jsonl` or sealed `.age` file
- language-pack compiled bytes/manifests

## 7. Readiness metric evolution

Readiness must express authority and evidence, not merely coverage.

| Stage | Meaning | Required evidence | Allowed effect |
|---|---|---|---|
| Candidate contract | A construction family and organ may be relevant | Proposal evidence and at least one supported role | Diagnostic count only |
| Blocked contract | Candidate exists but roles, target, topology, dimension, or hazards do not close | Stable blocker codes and evidence spans | Refusal/diagnostic only |
| Runnable diagnostic contract | Every organ input can be projected from `ProblemFrame` alone | Closed obligations, no blocking hazard, deterministic typed projection schema | Diagnostic count only; no organ call |
| ProblemFrame-only verified contract | Typed input was derived without raw prose and the organ/verifier accepted it | Derivation proof, independent verifier, morphology/confuser evidence, replay digest | Shadow evidence only |
| Migrated serving contract | Existing admission consumes the typed path | Serving parity, wrong-zero gates, explicit ratification | May answer through existing surface policy |
| Retired legacy parser | No raw-text fallback/call site remains for the migrated organ | Parser deletion, call-site deletion, no-new-legacy allowlist shrink | Architectural debt reduced |

Headline metrics should include:

- candidate count and candidate precision;
- blocked count by stable gap code;
- binding closure rate by construction;
- diagnostic runnable count and per-case obligation proof;
- false-runnable count, which must be zero before promotion;
- ProblemFrame-only verified count;
- migrated serving contract count;
- retired parser/allowlist count;
- serving `correct/refused/wrong` and exact `wrong_ids`.

Progress is not monotonic in runnable count. PR 1's expected train movement `1 -> 2`
and holdout movement `1 -> 0` are both improvements: one closes a legitimate contract,
the other removes a lie. Candidate recall without stable precision is not progress.

## 8. Parser retirement strategy

1. **Inventory.** Keep a mechanically checked list of raw-text organs, parsing
   helpers, raw-prose call sites, and allowlisted legacy files. Classify shared lexical
   extraction separately from sentence-structure parsing.
2. **Shadow diagnostics.** Build `ProblemFrame` and assessments beside serving without
   changing answers. Record candidate, blockers, and false-runnable cases.
3. **Parity checks.** For one organ, compare the typed `ProblemFrame` projection with
   the legacy organ's accepted/rejected domain across positives, morphology variants,
   and near confusers. Disagreement blocks migration and must default to refusal.
4. **ProblemFrame-only readiness.** Add a typed organ entry point that accepts no raw
   text. Prove the derivation and verifier from that input. No fallback is allowed.
5. **Migration.** Wire the typed path through the existing admission boundary only
   after architect ratification and serving evidence.
6. **Legacy fallback removal.** Remove raw-text parsing and any compatibility call in
   the same migration PR. Do not retain it “temporarily” behind the typed consumer.
7. **Final deletion.** Shrink the no-new-legacy allowlist and delete dead helpers only
   after call-site scans and the full relevant lanes prove equivalence or stricter
   refusal.

The unit of retirement is one organ. A broad rewrite that deletes several parsers
before independently proving each contract is not reviewable.

## 9. Governance and ADR implications

### 9.1 ADR-0223

ADR-0223 supplies the binding doctrine for this program: words/chunks probe; semantic
closeness proposes; bindings ground; contracts determine. Future substrate PRs must
show which audit gap codes they close and must not claim substrate use merely because
they execute inside `problem_frame_builder.py`.

There is status drift: ADR-0223 still says **Proposed for architect ratification**
while its required audit is merged in #833 and this plan depends on its conclusions.
Before PR 1 merges, the architect should ratify ADR-0223 and update its status to
Accepted, recording that the audit requirement was fulfilled by #833. This can be a
docs-only amendment in the plan review; it must not be silently inferred from merge
history.

### 9.2 ADR-0144 graph separation

- `ProblemFrame` owns problem comprehension state.
- Math-specific derivation state remains in math structures/organs.
- `EpistemicGraph` may carry recognition/provenance evidence through a typed adapter,
  but never solver operands or target arithmetic.
- `PropositionGraph` receives claims for articulation after derivation; it does not
  become the construction or solver graph.

### 9.3 ADR-0207 anti-universal-IR posture

The construction catalog is not a universal parser, and `ProblemFrame` is not a
universal cognition graph. Every consumer receives a narrow immutable projection.
Shared concepts are represented by typed facts and adapters, not by adding all fields
to one object.

ADR-0207 also freezes bespoke regex positive serving capability. The temporary
diagnostic construction in PR 1 cannot become a new positive serving branch. Positive
serving capability ultimately flows through the verified typed path.

### 9.4 ADR-0218 promotion discipline

A verified derivation does not promote catalog data or memory. Durable construction,
pack, or epistemic changes remain reviewed. Runtime observations may produce replayable
proposals, but they cannot rewrite the catalog, activate new signatures, or promote
standing. Existing Vault mutation ownership and INV-29 remain unchanged.

### 9.5 ADR-0222 / FrameVerdict contamination

`ContractAssessment` is a readiness decision, not an epistemic verdict. A blocked
contract means “this organ is not licensed from these facts,” not “the proposition is
false.” Do not import, construct, emulate, or rename `FrameVerdict` here. Do not add an
`answer=False` path or use absence of a binding as proof of negation.

## 10. Agent allocation strategy

| Work | Primary agent | Review | Constraint |
|---|---|---|---|
| Architecture, catalog schema, graph boundaries, promotion criteria | XHIGH | Architect | Owns doctrine and merge-blocker analysis; no bulk implementation. |
| Bounded builder/contract/adapter implementation | Codex or Opus | XHIGH for semantic boundaries | Must implement the written obligations, not reinterpret them. |
| Mechanical fixtures, manifest/checksum updates, allowlist edits | Grok only when instructions and expected bytes are exact | Codex/Opus | No authority to widen signatures, relax blockers, or change topology. |
| Preflight, inventory, docs-only consistency, branch/diff verification | Gemini/Flash or equivalent cheaper agent | Implementer | May report evidence; may not approve capability or doctrine. |
| Serving migration | Codex/Opus | Mandatory XHIGH + architect review | Requires ProblemFrame-only verification and wrong-zero evidence first. |

Every implementation handoff must state exact files, positive obligations, negative
fixtures, non-goals, and expected metrics. No agent may substitute score movement for
contract evidence or reinterpret “semantic neighborhood” as permission to select an
operator.

## 11. Validation matrix

Run the smallest lanes first. Use the repository CLI when available; the module
entrypoint is an equivalent fallback when `core` is not on `PATH`.

### 11.1 Focused ProblemFrame and contract tests

```bash
uv run python -m pytest -q \
  tests/test_problem_frame_skeleton.py \
  tests/test_problem_frame_builder.py \
  tests/test_problem_frame_contracts.py \
  tests/test_gsm8k_problem_frame_adequacy.py \
  tests/test_gsm8k_morphology_missing_kernel_labels.py \
  tests/test_process_frames.py \
  tests/test_language_packs_scalar_equivalence.py \
  tests/test_language_packs_unit_dimensions.py \
  tests/test_ambiguity_hazards.py
```

Acceptance: all pass; repeated frame/assessment construction is byte/structure equal;
`0005` has a runnable `fraction_decrease`; `0046` has a runnable
`percent_partition`; `0393` has no runnable contract and exposes stable blockers.

### 11.2 Adequacy diagnostics

```bash
uv run python scripts/gsm8k_problem_frame_adequacy.py \
  --cases evals/gsm8k_math/train_sample/v1/cases.jsonl

uv run python scripts/gsm8k_problem_frame_adequacy.py \
  --cases evals/gsm8k_math/holdout_dev/v1/cases.jsonl
```

Acceptance after PR 1:

```text
train contract_runnable_count = 2, exactly 0005 and 0046
holdout contract_runnable_count = 0
false_runnable_count = 0
```

Do not write these outputs into committed report artifacts.

### 11.3 Serving reports in memory

```bash
uv run python - <<'PY'
from evals.gsm8k_math.train_sample.v1.runner import _CASES_PATH, _load_cases, build_report
r = build_report(_load_cases(_CASES_PATH))
wrong = [row["case_id"] for row in r["per_case"] if row["verdict"] == "wrong"]
print(r["counts"], wrong)
PY

uv run python - <<'PY'
from evals.gsm8k_math.holdout_dev.v1.runner import build_report
r = build_report()
wrong = [row["case_id"] for row in r["per_case"] if row["verdict"] == "wrong"]
print(r["counts"], wrong)
PY
```

Acceptance for PR 1: train `30 correct / 20 refused / 0 wrong`; holdout
`5 correct / 495 refused / 0 wrong`; both wrong-ID lists empty. PR 1 must not alter
serving output at all.

### 11.4 Legacy and architectural invariants

```bash
uv run python -m pytest -q \
  tests/test_kernel_no_new_legacy_derivation_surfaces.py \
  tests/test_architectural_invariants.py \
  tests/test_epistemic_invariants.py

core test --suite smoke -q
# fallback when core is not on PATH:
uv run python -m core.cli test --suite smoke -q
```

Acceptance: all pass; no new derivation raw-parser surface; INV-21/24/29/30 remain
unchanged; no field/runtime path was modified in diagnostic PRs.

### 11.5 Diff and artifact gates

```bash
git diff --check
git status --short
git diff --name-only origin/main...HEAD
test -z "$(git diff --name-only origin/main...HEAD | \
  rg '(^|/)(report\.json|cases\.jsonl|[^/]+\.age)$')"
```

Acceptance for PR 1:

- no `generate/derivation/` diff;
- no `generate/math_candidate_graph.py` diff;
- no report, case, or sealed diff;
- no pack/manifest diff;
- no case-ID logic;
- only intended source/tests/docs changed.

Before a serving migration, additionally run the relevant CLI runtime/algebra/full
lanes and `core eval cognition`; the exact migration PR must record why each lane is
proportionate to its risk.

## 12. Workbench/UI implications

Workbench should eventually make the middle layer inspectable:

```text
original chunk and source span
  -> exact semantic neighbors and scores
  -> candidate construction IDs
  -> required/optional roles
  -> grounded role targets and provenance
  -> competing bindings/hazards
  -> ContractAssessment blockers and stage
  -> typed projection / derivation / verification evidence, when present
```

The UI must label `candidate`, `blocked`, `diagnostic runnable`, `verified shadow`,
and `migrated serving` distinctly. It must never render a candidate as a live
capability, synthesize missing stages, replay raw runtime state in the browser, or
persist field arrays merely for visualization.

This is PR 9, not immediate work. The evidence schema must stabilize first; otherwise
the UI will freeze diagnostic accidents into a public contract.

## 13. Risks and failure modes

| Risk | Failure signature | Required correction |
|---|---|---|
| Local parser relabeled as substrate | A new regex/trigger is added and described as affordance retrieval | Classify it honestly as bounded scaffold; move authority to reviewed catalog plus exact proposal seam. |
| False runnable inflation | Runnable count rises while topology/target obligations remain implicit | Audit every runnable case; add explicit obligations and confusers; count removal as progress. |
| Raw-text fallback behind a `ProblemFrame` consumer | Typed adapter fails and consumer reparses `problem_text` | Prohibit text on typed entry point; failure returns refusal; scan call sites. |
| Universal-IR drift | Solver, recognition, and articulation fields accumulate on one graph | Keep purpose-specific structures and narrow projections per ADR-0144/0207. |
| Score chasing | A GSM8K case or phrase causes a special branch | Ban case IDs/labels; require heterogeneous morphology and near-confuser evidence; preserve wrong-zero. |
| Premature serving migration | Diagnostic runnable is wired before typed derivation/verifier parity | Require ProblemFrame-only verified stage and architect ratification first. |
| Benchmark overfitting | Only `0005`/`0046` exact prose passes | Test same geometry across reviewed lexical variants and different entities/units; hold target/topology confusers. |
| Hidden normalization | New binder repairs field/versor state or coerces units silently | Keep normalization at approved boundaries; bind facts without modifying geometric state. |
| Semantic closeness mistaken for proof | High CGA score directly chooses organ/operator | Proposal record only; contract cannot read score as an obligation; exact bindings and hazards decide. |
| Catalog becomes executable grammar | Pack records contain regex/code/answer expressions | Closed data schema; no dynamic import or arbitrary regex; schema rejects unknown executable fields. |
| Mutable/stochastic proposal | Learned threshold/cache changes candidate order across runs | Exact scan, immutable reviewed subset, deterministic tie order, replay tests. |
| Target semantics collapse | “How many” grounds an entity but not state/operator/direction | Typed target axes and illegal-combination checks. |
| Readiness conflates truth | Blocked contract is interpreted as false proposition | Keep `ContractAssessment` separate from `Determined` and proposed `FrameVerdict`. |
| Duplicate semantic authority | Python process frames and pack catalog drift | Establish pack bytes as authority, parity-test compatibility views, then retire duplicate declarations. |
| Parser accumulation | Typed path lands but old parser remains as fallback | Migration PR must delete parser and shrink allowlist in the same change. |

## 14. Final recommendation

### Exact next PR

```text
branch: codex/problemframe-proportional-change-closure
title:  feat(kernel): close proportional-decrease contracts and make readiness obligation-sound
```

Keep it diagnostic-only. It must bind `decrease_to_fraction`, type the delta target,
make train `0005` runnable, retain train `0046` under stronger obligations, and block
holdout `0393`. It must not edit derivation organs, `math_candidate_graph.py`, pack
bytes, serving, reports, cases, or sealed artifacts.

### Exact next agent

Use Codex or Opus for the bounded implementation, with high reasoning and a mandatory
XHIGH merge-blocker review. The implementation is narrow enough for a code-focused
agent, but target/topology semantics are too consequential for an unguided mechanical
agent.

### Exact handoff prompt

```text
Implement PR: feat(kernel): close proportional-decrease contracts and make readiness
obligation-sound on branch codex/problemframe-proportional-change-closure.

Read GPT55.md/your agent supplement, AGENTS.md, docs/runtime_contracts.md,
docs/analysis/semantic-substrate-problem-solving-master-plan-2026-06-20.md,
the ADR-0223 audit pack, and HANDOFF-gpt55-2026-06-20.md. Complete the repository
bootstrap and pre-edit sweep before editing.

Scope:
1. In the diagnostic ProblemFrame path, bind a provenance-bearing
   decrease_to_fraction relation for train case 0005 with roles for base quantity 84,
   scale 3/4, state entity temperature, unit degrees, and the exact transition span.
2. Represent the question as an explicit decrease-delta target: operator=difference,
   state=delta, direction=decrease, same target entity, exact source span.
3. Add an obligation-complete assess_fraction_decrease(frame) that is runnable only
   when base, scale, entity/unit continuity, delta target, provenance, and hazards close.
4. Tighten assess_percent_partition(frame): require a pre-partition numeric whole,
   distinct/covered subgroups, identity-linked scales, and a forward aggregate target.
   Keep train 0046 runnable. Make holdout 0393 non-runnable with stable blockers for
   missing original whole / inverse topology; do not solve or reroute it.
5. Add positive, final-value, affine, decrease-by, multiple-scale/base, forecast-time,
   entity/unit mismatch, inverse-target, subgroup, and deterministic replay tests.
6. Update adequacy/morphology diagnostics only as required for stable blocker evidence.

Hard stops:
- Do not edit generate/derivation/* or generate/math_candidate_graph.py.
- Do not change serving, reports, cases, sealed artifacts, pack bytes/manifests, or
  answer labels.
- Do not add raw-text fallback, case-ID behavior, generic parsing, hidden normalization,
  approximate retrieval, or a second semantic authority.
- Do not call local signature matching “semantic substrate retrieval”; exact CGA
  proposal is a later PR.

Required evidence:
- focused ProblemFrame/contracts/process/scalar/unit/hazard tests green;
- no-new-legacy and architectural invariants green;
- adequacy: train runnable 1->2 (0005, 0046), holdout 1->0;
- serving in memory unchanged: train 30/20/0, holdout 5/495/0, wrong_ids=[];
- git diff --check; no derivation/candidate-graph/report/case/sealed/pack diff.

Before coding, state the exact files and explain why the relation and target types make
false readiness unrepresentable. At handoff, list every obligation and confuser proven.
```

### What not to do next

Do not migrate `percent_partition`, wire `ProblemFrame` into serving, build a generic
parser, add embeddings/ANN/cosine retrieval, broaden trigger lists for score, or start
Workbench UI. First make diagnostic readiness truthful. Then establish the reviewed
construction catalog and exact proposal seam. Serving comes only after one
ProblemFrame-only contract is independently verified.
