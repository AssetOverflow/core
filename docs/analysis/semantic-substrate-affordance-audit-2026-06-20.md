# Semantic Substrate Affordance Audit — 2026-06-20

Status: decision audit; no serving-path change

Governing decision: ADR-0223

Evidence baseline: detached `564e360e` (`docs(adr): require semantic substrate affordance audit`)

## Executive decision

CORE has a real geometric substrate, but mathematical problem comprehension does not yet use it. Exact CGA neighborhood operations, deterministic field propagation, pack compilation, provenance-carrying facts, and separated graph roles all exist. The diagnostic `ProblemFrame` path instead discovers process families from hard-coded surface triggers and binds its few relations with local regular expressions. The serving path bypasses `ProblemFrame` entirely and invokes a sequence of raw-text derivation organs.

The immediate decision is therefore not to add another parser or to promote diagnostics into serving. The next load-bearing change should close the proportional-decrease affordance in `ProblemFrame` as an obligation-sound construction, while strengthening percent-partition readiness so that inverse/remainder cases cannot be declared runnable. That slice should establish the shape of the eventual construction system: pack-backed construction declarations, exact semantic-neighborhood proposal, deterministic span binding, explicit obligations and hazards, and typed projection into `ProblemFrame`.

The masterstroke is separation of **proposal** from **proof**:

```text
exact semantic neighborhood
  -> candidate construction family (proposal only)
  -> deterministic construction binding with exact spans
  -> obligation and hazard assessment
  -> ProblemFrame facts and relations
  -> organ readiness
```

CGA retrieval may suggest which construction deserves inspection. It must never, by similarity alone, license a relation, an answer, or a serving organ.

## Scope and non-negotiable invariants

This audit inspected architecture and diagnostics only. It does not change serving behavior, migrate a derivation organ, mutate benchmark cases or sealed artifacts, mine answers, introduce raw-text fallback, add broad parsing, weaken exact recall, normalize a hot path, or create unreviewed learning.

The preserved safety conditions are:

- `versor_condition(F) < 1e-6` remains the field invariant.
- exact CGA recall remains exact; no ANN, cosine, HNSW, or stochastic retrieval is proposed.
- `surface`, `walk_surface`, and `articulation_surface` remain distinct.
- `ProblemFrame`, `EpistemicGraph`, `PropositionGraph`, and `MathProblemGraph` retain separate responsibilities.
- diagnostic coverage may increase only with `wrong_ids == []`.
- unknown remains unknown; absence of a relation is not evidence that it is false.
- reviewed teaching and pack mutation remain proposal/review controlled.

## Map: four architectural directions

### Direction A — Continue local organ parsers

Each new mathematical family gets another `resolve_promotable_*` function with local regexes, phrase checks, and extraction logic.

This is locally cheap and can preserve benchmark precision, but it duplicates recognition, binding, hazards, and provenance in every organ. It makes semantic equivalence a maintenance problem and leaves the geometric substrate irrelevant to comprehension. The no-new-legacy guard limits the number of new regex-bearing files but does not retire the existing allowlist or prevent phrase-based local grammars.

Decision: reject as the forward architecture. Existing organs remain bounded debt until a contract-backed replacement is proven.

### Direction B — Build a universal parser or universal graph

A broad parser would turn prose into one maximal intermediate representation and feed recognition, reasoning, articulation, and solving from it.

This appears to consolidate work but violates the repository's graph-boundary discipline. Recognition evidence, mathematical solver structure, and articulation plans have different invariants and lifetimes. A universal graph would accumulate optional fields, erase epistemic distinctions, and make illegal cross-layer states representable.

Decision: reject. Use typed adapters between purpose-specific structures.

### Direction C — Constructional affordances over the semantic substrate

Reviewed construction declarations define candidate families, required roles, admissible lexical neighborhoods, exact binding rules, hazards, and contract obligations. Exact CGA retrieval proposes candidates; deterministic construction code proves bindings and emits `KernelFacts`/`ProblemFrame` relations with spans and provenance. Contracts decide readiness.

This direction fits the intrinsic space: a word problem is not a bag of numbers or a flat parse. It is a partially observed relational field in which several constructions may resonate, but only constructions whose role obligations close may act.

Decision: select. Implement incrementally, beginning with proportional decrease and false-readiness correction.

### Direction D — Learned or stochastic semantic parsing

A model could infer latent structures or select organs probabilistically.

That would make current gaps harder to inspect, undermine replay, and conflate candidate confidence with semantic proof. It may be reconsidered only after deterministic construction contracts provide a gold interface and replayable evidence.

Decision: defer; not licensed by the current architecture.

## What the substrate actually affords today

### Real and operational affordances

1. **Geometric vocabulary state.** Language-pack compilation builds vocab manifolds and resonance structures. `VocabManifold.nearest` and vault recall use exact `cga_inner` scans. Field transitions use `versor_apply` and preserve the hard versor invariant.
2. **Exact lexical normalization.** Pack-backed scalar equivalence maps number surfaces to exact `Fraction` values with source spans. Unit dimensions provide deterministic exact lookup. These are lexical affordances, not grammar parsers.
3. **Provenance-bearing diagnostic facts.** `KernelFacts` and `ProblemFrame` preserve source spans, normalized values, bindings, candidate relations, targets, and hazards with deterministic ordering.
4. **Separated graph meanings.** `EpistemicGraph` carries recognition evidence, `PropositionGraph` plans articulation, and `MathProblemGraph` is a solver graph. Their current separation is architecturally correct.
5. **A narrow construction precedent.** The recognition anti-unifier produces typed slots and spans from taught examples. It demonstrates deterministic constructional recognition, though it is currently narrow and disconnected from math comprehension.
6. **Deterministic evaluation.** Serving reports, adequacy reports, morphology reports, trace hashes, and CLI lanes allow a proposal to be measured without silently changing behavior.

### Prepared but unused affordances

The `en_core_math_v1` pack contains 57,106 bytes of lexical material and compiled semantic domains, but `frames.jsonl` is empty and its manifest carries the SHA-256 of empty bytes. Mathematical process-frame declarations instead live in `generate/process_frames.py`. The pack therefore prepares vocabulary neighborhoods but does not provide a reviewed construction layer.

`ProblemFrame` does not load a pack manifold, call `cga_inner`, or query exact vault recall. Its process-family detection scans `ProcessFrame.trigger_surfaces` using boundary text matching. In this path, “semantic neighborhood” is an architectural intention, not an implemented recognition mechanism.

### Merely named affordances

- Semantic similarity does not currently retrieve mathematical constructions.
- Process frames declare roles but do not bind them.
- Contract candidates do not consistently prove the facts their organs require.
- Hazards are attached, but most do not participate in readiness decisions.
- A `ProblemFrame` does not currently serve as the input to any promoted derivation organ.

## Concrete path audit

### Real current pipeline after #831

Confirmed from repository call sites:

```text
diagnostic path
raw text
  -> scalar/unit/entity/hazard extraction
  -> hard-coded ProcessFrame trigger scan
  -> local-regex mentions and narrow bound relations
  -> ProblemFrame
  -> assess_contracts
  -> adequacy/morphology report

serving path
raw text
  -> generate.math_candidate_graph.parse_and_solve
  -> ordered raw-text resolve_promotable_* organs
  -> MathProblemGraph/candidate result
  -> serving result or refusal
```

There is no serving edge from `ProblemFrame` or `ContractAssessment` to a derivation organ. There is also no math-comprehension edge from a mounted manifold or exact CGA recall operation into `build_problem_frame`. The intended constructional loop is therefore a proposed architecture, not current behavior.

### `ProblemFrame` extraction and binding

`generate/problem_frame_builder.py` has a useful deterministic shell and exact provenance, but its semantic core is narrow:

- `_extract_process_frame_candidates` (line 179) matches every hard-coded trigger surface.
- `_extract_candidate_relations` (line 201) creates unbound declarations rather than evidence-backed roles.
- `_ENTITY_AFTER_QUANTITY_RE`, `_FRACTION_ENTITY_RE`, `_QUESTION_ENTITY_RE`, `_ACTOR_VERB_RE`, and `_TRANSFER_RE` (lines 280–298) form a local grammar.
- `_bound_relations` (line 397) binds generic fraction/percent relations and one exact transfer shape.
- the “whole” is selected positionally as the first non-percent/non-fraction quantity binding, which can select a final remainder as the original whole.
- target grounding handles narrow “how many/how much” objects; other question forms remain unresolved.

The builder is acceptable as a diagnostic scaffold, but ADR-0207 does not license its grammar regexes as the basis of positive capability. New affordances should consume substrate facts and reviewed constructions, not enlarge this local grammar.

### Contract assessment

`generate/problem_frame_contracts.py` implements one material assessment: `percent_partition`. `nested_fraction_remainder_total` and `temporal_tariff` assessments are skeletons over relation types the builder never emits.

The percent assessment currently treats partition or consumption process-frame presence as enough to emit a candidate. Runnable status checks a subgroup/whole link, a percent/subgroup surface match, target grounding, and limited hazards. It does not prove:

- a numeric whole quantity rather than an object label;
- the expected partition topology;
- coverage and distinctness of subgroup roles;
- target operator and direction;
- forward aggregation rather than inverse reconstruction or remaining-state recovery;
- relation anchoring to the relevant events;
- that all percentages belong to the same partition.

This is a readiness-soundness defect, not merely a coverage gap.

### Serving path

`generate/math_candidate_graph.py::parse_and_solve` (line 589) invokes a sequence of raw-text `resolve_promotable_*` organs. Repository search found `build_problem_frame` only in diagnostics and tests. The existing `fraction_decrease` and `percent_partition` organs each perform their own raw-text recognition and extraction.

The no-new-legacy guard currently allowlists 31 derivation files. Representative regex counts include 47 in `math_candidate_parser`, 18 in `r1_reconstruction`, and 13 in `temporal_tariff`. The guard is valuable containment, but containment is not migration.

### Local recognizer inventory

| File/function | Recognizes | Classification | Evidence | Recommendation |
|---|---|---|---|---|
| `language_packs/scalar_equivalence.py` and numerics loader | exact numeric surfaces and values | allowed lexical normalization | pack-backed entries, exact `Fraction`, spans | retain; extend only through reviewed lexical data |
| `language_packs/unit_dimensions.py` | exact unit aliases/dimensions | allowed lexical normalization | pack lookup with deterministic result | retain; improve lexical coverage without sentence grammar |
| `language_packs/ambiguity_hazards.py` | known ambiguous surfaces | allowed corrective scaffold | centralized deterministic registry | retain and connect hazards to construction/contract blocking |
| `generate/problem_frame_builder.py::_extract_process_frame_candidates` | process families from trigger surfaces | diagnostic scaffold; duplicate semantic source | scans Python `ProcessFrame.trigger_surfaces`; no pack/CGA lookup | replace incrementally with pack-backed construction proposals |
| builder entity/question/actor regexes | local mentions, bindings, question object | diagnostic scaffold / foundation risk | grammar-bearing regexes at lines 280–298 | freeze; replace family-by-family through construction binding |
| builder `_TRANSFER_RE` / `_bound_relations` | one transfer form and generic fraction/percent links | diagnostic scaffold / legacy parser risk | fixed clause shape and positional whole selection | use only as migration evidence; do not broaden |
| `generate/process_frames.py` declarations | process surfaces, roles, hazards | duplicate semantic source | Python taxonomy while math pack `frames.jsonl` is empty | consolidate into reviewed checksummed construction data |
| `generate/problem_frame_contracts.py` | percent readiness and skeletal missing-role reports | substrate-backed readiness gate, incomplete | consumes structured frame rather than raw prose | preserve boundary; strengthen obligations and add family contracts |
| `scripts/gsm8k_substrate_morphology.py` | gap labels and migration recommendations | contract-first diagnostic with loose-trigger fallback | assessments are preferred; raw substring/regex fallbacks remain | report contract gap codes; label fallback recommendations as heuristic |
| `generate/derivation/fraction_decrease.py` | decrease-to-fraction word problems | legacy parser risk | local regex/quantity/question extraction from raw text | migrate only after a closed frame contract exists, then delete parser |
| `generate/derivation/percent_partition.py` | equal partition plus percentages | legacy parser risk | local percent regex and phrase scan | keep serving unchanged until contract soundness and parity are proven |
| other `generate/derivation/*` resolvers | organ-specific prose shapes | legacy parser risk | repeated raw-text recognizers in serving chain | retire one-for-one; do not create a generic replacement parser |
| `recognition/anti_unifier.py` | taught token-shape constructions with typed slots | substrate-aligned binder precedent | deterministic slot/span construction | reuse its proof discipline, not its graph type, for math |

The scalar/unit recognizers are acceptable because they map lexical forms to exact typed facts without asserting sentence relations. Grammar-bearing recognizers become foundation risks when they directly license process roles, target direction, or organ readiness.

### Morphology recommendation audit

The morphology script is strongest when it derives recommendations from `ContractAssessment.missing_obligations`. Its raw surface fallbacks are diagnostically convenient but can repeat the same overbroad-trigger problem as process-frame discovery. A future report should distinguish `contract_gap` from `surface_heuristic` provenance and should never count the latter as readiness evidence.

### Graph boundaries

- `ProblemFrame`: diagnostic mathematical facts, bindings, process candidates, targets, hazards, and readiness inputs.
- `EpistemicGraph`: recognition assertions and provenance for a cognitive turn.
- `MathProblemGraph`: solver-specific candidate graph used by the serving math lane.
- `PropositionGraph`: articulation planning, not comprehension or solving.

No current mega-IR drift was found. The risk is prospective: using `PropositionGraph` as a math representation or expanding `EpistemicGraph` into a solver graph would collapse distinct invariants. The selected design instead projects a closed construction binding into each consumer through a narrow typed adapter.

## Diagnostic evidence

### Serving baseline

| Split | Correct | Refused | Wrong | Wrong IDs |
|---|---:|---:|---:|---|
| Train sample | 30 | 20 | 0 | `[]` |
| Holdout | 5 | 495 | 0 | `[]` |

This is the governing safety posture: extremely sparse coverage with no known wrong answers.

### `ProblemFrame` adequacy

| Split | Frames | Scalars | Units | Entity bindings | Quantity bindings | Process relations | Bound targets | Contract candidates | Runnable |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Train sample (50) | 50 | 47 | 21 | 50 | 46 | 16 | 42 | 42 | 1 |
| Holdout (500) | 500 | 470 | 202 | 494 | 452 | 124 | 402 | 423 | 1 |

High scalar/entity/target presence is not contract readiness. The large candidate-to-runnable collapse is appropriate when obligations are missing, but candidate emission is also too broad.

Top observed missing obligations/hazards:

| Gap | Train sample | Holdout |
|---|---:|---:|
| percent link | 24 | 240 |
| whole | 15 | 180 |
| partition subgroup | 14 | 167 |
| worker / rate / duration (each) | 10 | 128 |
| container / content / count-per (each) | 7 | 54 |
| target | 6 | 34 |
| unbound-base hazard | 15 | 180 |
| percent-ambiguity hazard | 2 | 19 |

These counts are diagnostic occurrences, not independent cases or projected serving gains.

Contract candidate counts:

| Split | Percent partition | Temporal tariff | Nested fraction | Runnable |
|---|---:|---:|---:|---:|
| Train sample | 25 | 10 | 7 | 1 |
| Holdout | 241 | 128 | 54 | 1 |

The dominant missing roles are percent-link/whole/subgroup, worker-rate-duration, and container-content-count-per bindings. These are construction-binding gaps, not missing arithmetic operators.

### Runnable truth audit

Train case `0046` is the intended percent-partition slice: 100 students, two halves, percentages within subgroups, aggregate target. The current frame is sufficient to solve it, though its contract proof is weaker than the example itself.

Holdout case `0393` is a false runnable. It describes chocolates, two halves, consumption percentages, a final remainder of 28, and asks for the original count. The builder:

- selects the final `28 chocolates` binding as the “whole”;
- binds fraction entities to local verbs such as “have” and “do”;
- links percent and subgroup surfaces through the generic word “ones”;
- grounds the target as `remaining`;
- declares a forward percent-partition contract runnable even though the problem requires inverse reconstruction.

The serving system correctly refuses this case. Contract readiness must be tightened before any diagnostic promotion.

### Representative affordance probes

| Family | Current diagnostic behavior | Structural gap |
|---|---|---|
| Acquisition | Detects transaction/comparison; may bind `3` to “more”; no process relation | event roles, same-entity continuity, additive direction |
| Loss/remainder | “left” can trigger consumption/partition and a false percent candidate | event state transition, remainder target direction |
| Transfer | One fixed regex binds agent, patient, quantity, object | construction generality, pronouns, tense/voice variants |
| Proportional decrease | Scalars and unit may be present; no process relation or grounded delta target | base/final state, scale, delta target construction |
| Rate/labor | Labor candidate only; worker/rate/duration remain unbound | dimensional rate construction and monetary target |
| Comparison | Comparison candidate only; `3 more` may bind as an entity | comparator, difference, direction, referent continuity |
| Container | Container candidate only | container/content/count-per/cardinality roles |
| Partition | Percent/fraction links are surface-local and topology-poor | whole/subgroup topology, coverage, aggregation target |

## Hidden geometry and intrinsic representation

The intrinsic space is a typed relational field over source spans, semantic entities, quantities, events, and question operators. Its invariants are:

1. every asserted role has source or reviewed-reconstruction provenance;
2. semantic-neighborhood retrieval can propose but cannot assert;
3. each construction has a dual: positive obligations and corrective hazards/confusers;
4. target direction is part of the construction, not punctuation trivia;
5. numerical execution occurs only after role closure;
6. graph projections preserve their consumer-specific invariants;
7. refusal is the correct reconstruction when closure is absent.

The distortion in the current system comes from projecting this relational field too early into flat text patterns. The correction is not a larger regex. It is an explicit construction-binding boundary.

## Foundation risk register

| Severity label | Evidence | Consequence | Recommendation | PR needed? |
|---|---|---|---|---|
| `FOUNDATION_BLOCKER` | no math construction catalog; no neighborhood-to-construction path; no typed organ adapter | substrate cannot become the source of problem-solving behavior | establish reviewed construction declarations and proposal/proof boundary | yes, PRs 2–3 and first migration |
| `READINESS_FALSE_POSITIVE` | holdout `0393` is declared runnable by a forward percent contract | future promotion could admit an unsupported answer | strengthen target/topology/whole obligations before promotion | yes, immediate PR |
| `LEGACY_BYPASS_RISK` | serving reparses raw text in each `resolve_promotable_*` organ | semantic fixes duplicate and can disagree by organ | migrate one closed contract at a time and delete the parser | yes, staged |
| `DUPLICATE_SEMANTICS` | pack lexicon, Python process frames, builder triggers, morphology triggers, and organ patterns encode overlapping meaning | aliases, roles, and hazards drift | make reviewed pack construction bytes authoritative | yes, PR 2 |
| `MISSING_AFFORDANCE` | acquisition, loss, comparison, rate, container, and proportional roles remain unbound | many cases have facts but no closed relational topology | add bounded construction families in priority order | yes, PRs 1, 4, 5 |
| `DOC_GOVERNANCE_DRIFT` | ADR-0207 forbids grammar regex as positive capability while current diagnostics can be described as substrate-backed | implementation status can be overstated and legacy patterns copied | label local grammar as diagnostic scaffold and require parser retirement evidence | docs now; tests later |
| `DEFERRED_RESEARCH` | exact CGA proposal thresholds/precision for construction families are unmeasured | premature retrieval could create noisy candidates or hot-path cost | prototype only after catalog; measure confusers and deterministic cost | later research PR |

Confirmed facts in this register come from repository code, manifests, diagnostics, and tests. The proposed construction type names, exact catalog schema, and likely performance characteristics are architectural hypotheses that require implementation evidence; they are not claimed as existing behavior.

## Build decision: construction proposal and proof

The selected architecture should use three narrowly scoped types or equivalent structural contracts; names are illustrative, not an implementation mandate:

1. **Construction declaration** — reviewed, pack-backed family identity; admissible lexical/domain anchors; required and optional roles; target operators; hazards; and declared projections.
2. **Construction candidate** — candidate family, exact retrieval evidence, source spans, and provenance. It is epistemically `possible`, never runnable.
3. **Construction binding** — exact role-to-fact bindings, unresolved obligations, triggered hazards, and a deterministic proof record. Only a closed binding projects bound relations into `ProblemFrame`.

This makes illegal states unrepresentable: a candidate cannot masquerade as a binding, and a binding with missing obligations cannot masquerade as a runnable contract.

The exact semantic-neighborhood layer should remain bounded:

- query only reviewed, mounted pack state;
- use exact CGA scans and deterministic ordering;
- return family proposals, not inferred facts;
- preserve matched lexical evidence and spans;
- require a deterministic construction matcher to close roles;
- reject ambiguous or conflicting bindings through explicit hazards;
- never retrieve answers, benchmark labels, or executable organ names from unreviewed text.

## Recommended implementation sequence

### PR 1 — proportional closure and readiness soundness

Proposed branch: `codex/problemframe-proportional-change-closure`

Proposed title: `feat(kernel): close proportional-decrease contracts and make readiness obligation-sound`

Scope:

- represent a `decrease_to_fraction` construction over existing `KernelFacts`/`ProblemFrame` concepts;
- bind base state, final fractional state, unit/entity continuity, scale, and requested delta with exact spans;
- add a contract assessment whose runnable state proves those obligations;
- strengthen `percent_partition` assessment so inverse/remainder target `0393` is not runnable;
- add positive, confuser, target-direction, ambiguity, and deterministic-order tests;
- keep serving behavior unchanged.

Expected diagnostic movement, to be verified rather than hard-coded:

- train runnable: `1 -> 2` (`0005`, `0046`);
- holdout runnable: `1 -> 0` by removing false runnable `0393`;
- serving wrong IDs remain `[]`.

Non-goals: organ migration, answer production, new serving dispatch, broad grammar, benchmark mutation, and CGA construction retrieval.

Decision: **yes, this remains the immediate engineering PR**. It is the smallest slice that both adds a missing substrate relation and removes a false readiness state. The acceptance criteria are the expected case movements above, explicit positive/corrective obligations, exact spans/provenance, deterministic output, focused tests, smoke, and unchanged serving `wrong_ids == []`.

### PR 2 — pack-backed construction catalog

Proposed branch: `codex/math-construction-catalog`

Proposed title: `refactor(kernel): compile reviewed math constructions from language packs`

Move process-family declarations, role obligations, hazards, and stable aliases into a checksummed reviewed pack artifact. Compile them into typed immutable runtime declarations. Keep a compatibility adapter to `ProcessFrame`; do not add a universal graph.

Non-goals: serving use, fuzzy role binding, and automatic pack mutation.

### PR 3 — exact semantic-neighborhood proposal seam

Proposed branch: `codex/math-construction-neighborhoods`

Proposed title: `feat(kernel): propose math constructions from exact semantic neighborhoods`

Use mounted pack manifolds and exact CGA scans to propose construction families with evidence. Measure precision on curated confusers. Candidate proposals must not affect readiness until deterministic role binding closes.

Non-goals: approximate retrieval, learned thresholds, organ selection, or answer retrieval.

### PR 4 — constructional transaction and state-change bindings

Proposed branch: `codex/problemframe-state-change-constructions`

Proposed title: `feat(kernel): bind acquisition, loss, and transfer state changes`

Replace the fixed transfer shape and loose transaction triggers with catalog-backed constructions for acquisition, loss, and transfer, including entity continuity and target direction. Emit only bound `ProblemFrame` relations.

Non-goals: serving migration and unconstrained coreference.

### PR 5 — rate, comparison, container, and partition topology

Proposed branch: `codex/problemframe-relational-constructions`

Proposed title: `feat(kernel): close relational word-problem construction families`

Add typed bindings and obligation-complete assessments for labor/rate, comparison, container/count-per, and partition topology. Each family requires positive and adversarial morphology evidence.

### PR 6 — first contract-backed organ migration

Proposed branch: `codex/contract-backed-fraction-decrease`

Proposed title: `refactor(math): serve fraction decrease from closed ProblemFrame contracts`

Only after diagnostics demonstrate precision should one organ accept a typed closed contract instead of raw text. Compare serving reports and remove the corresponding legacy parser in the same PR.

Non-goals: multi-organ migration, fallback to the legacy parser after a failed contract, or changes to sealed evidence.

## Work allocation

Top-tier architectural work:

- construction type and proof-state design;
- obligation semantics and target-direction modeling;
- exact CGA proposal boundary and calibration policy;
- graph adapter boundaries;
- first serving migration and deletion of legacy parsing.

Lower-cost, mechanically checkable work suitable for narrower agents after the design is fixed:

- moving reviewed declarations to a pack and regenerating byte-derived checksums;
- adding table-driven positive/confuser fixtures;
- producing adequacy/morphology report diffs;
- adding deterministic ordering and serialization tests;
- shrinking the no-new-legacy allowlist when a parser is removed;
- documentation and audit-map updates.

## Safety gates for every PR

1. smallest relevant targeted tests pass;
2. smoke and cognition lanes remain green;
3. train and holdout serving reports retain `wrong_ids == []`;
4. adequacy report lists every newly runnable case and every removed false runnable;
5. deterministic reruns produce identical frames, assessments, and trace hashes;
6. construction candidates cannot become runnable without closed obligations;
7. exact spans and provenance exist for every bound role;
8. ambiguity hazards have adversarial tests and block readiness where relevant;
9. no normalization appears outside an allowed construction/algebra boundary;
10. no approximate retrieval, stochastic fallback, hidden answer path, or unreviewed mutation is introduced;
11. graph-boundary tests prevent `PropositionGraph` or `EpistemicGraph` from becoming solver IRs;
12. any serving migration deletes or deprecates the corresponding local parser and updates the legacy audit.

## Bounded handoff prompts

### Prompt for the next top-tier engineering agent

> Implement `feat(kernel): close proportional-decrease contracts and make readiness obligation-sound` on branch `codex/problemframe-proportional-change-closure`. Read `AGENTS.md`, your agent supplement, `docs/runtime_contracts.md`, ADR-0207/0218/0222/0223, and the three 2026-06-20 audit artifacts before editing. Map existing scalar, entity, unit, target, relation, and contract call sites first. Add a diagnostic-only proportional-decrease construction for train case `0005` using `KernelFacts`/`ProblemFrame` facts with exact spans and provenance. Its contract must prove base state, final fractional scale, entity/unit continuity, and delta target direction. Strengthen percent-partition obligations so train `0046` remains runnable and holdout `0393` becomes non-runnable. Do not change serving, derivation organs, benchmark/report/sealed files, or add raw-text fallback/generic parsing. Add positive, inverse, remainder, ambiguity, entity-mismatch, unit-mismatch, and deterministic-order tests. Run focused ProblemFrame/contract tests, adequacy on both splits, serving reports with `wrong_ids == []`, no-new-legacy, and smoke. Report exact runnable case changes; treat false-runnable removal as success.

### Prompt for a lower-cost mechanical agent after PR 1 design is fixed

> Add table-driven diagnostic fixtures and report assertions for the approved proportional-decrease and strengthened percent-partition contracts. Work only from the contract obligations specified in the parent design; do not invent surfaces, roles, parsing, or readiness policy. Cover deterministic ordering, exact spans/provenance, inverse/remainder refusal, entity and unit mismatch, and the expected `0005`/`0046`/`0393` classifications. Do not touch serving, derivation organs, pack data, benchmark cases, reports, or sealed artifacts. Run the focused test list and return the exact commands/results.

## Justification

The selected design follows the substrate's actual geometry. Semantic neighborhoods provide resonance; construction matching supplies the conjugate correction; contract obligations establish closure. Candidate retrieval and corrective proof are dual operations. Refusal is not a missing feature but the stable state reached when the field cannot close without inventing facts.

This is also mechanically sympathetic. Exact neighborhood scans operate over compact reviewed packs, immutable construction declarations can be compiled once, and deterministic role binding avoids repeatedly rebuilding ad hoc parser state in every organ. Typed projections keep each graph small and purpose-specific.

Most importantly, the design makes the desired direction measurable. CORE stops accumulating parsers when a newly supported family first appears as a closed substrate construction, then feeds a derivation organ through a typed contract, and finally permits deletion of the local raw-text parser. Coverage without parser retirement is not architectural progress.

## Answer to the governing question

The next most important thing CORE should do is implement the proportional-decrease slice as the first obligation-sound substrate construction—while removing the false percent-partition readiness of holdout `0393`—and use that slice to establish the reviewed construction-binding interface. Do not add another raw-text solver. The decisive milestone is a derivation organ receiving a closed, provenance-bearing `ProblemFrame` contract and deleting its local parser.
