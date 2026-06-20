# ADR-0223: Semantic Substrate Affordance Audit and Foundation Alignment

**Status:** Proposed for architect ratification. This ADR is docs-only until ratified and until any resulting implementation PRs are separately authorized.

**Date:** 2026-06-19

**Domains:** `language_packs/`, `generate/kernel_facts.py`, `generate/problem_frame.py`, `generate/problem_frame_builder.py`, `generate/problem_frame_contracts.py`, `scripts/gsm8k_problem_frame_adequacy.py`, `scripts/gsm8k_substrate_morphology.py`, `generate/derivation/`, `generate/math_candidate_graph.py`, `recognition/`, `generate/graph_planner.py`, `vault/`, `field/`, `algebra/`, `docs/decisions/`, `docs/analysis/`, and related tests.

**Depends on:** #829 Kernel Substrate Tranche 1, #830 ProblemFrame operationalization / legacy-deprecation guardrails, #831 ProblemFrame bindings and contract-readiness diagnostics, ADR-0144 (graph/carrier separation), ADR-0207 (typed adapters / anti-universal-IR posture), ADR-0218 (proof-carrying promotion), INV-25 (independent gold), INV-30 (open-world determination never asserts False), and existing wrong-zero serving discipline.

**Authors:** drafted from the 2026-06-19 architect/operator session after the #831 contract-readiness merge and the substrate-affordance design discussion.

---

## 1. Context

PRs #829–#831 established the current math-comprehension path:

```text
text
→ KernelFacts
→ ProblemFrame
→ span-grounded mentions / bindings / relations
→ ContractAssessment
→ contract-backed derivation organ, once justified
→ independent verification
→ existing admission and articulation path
```

#831 made the first honest readiness metric available: `contract_runnable_count`. It also showed that recognizable schema presence is not sufficient. The project can now distinguish candidate contracts from contracts that are runnable from bound `ProblemFrame` evidence alone.

The next implementation PR has been selected narrowly:

```text
feat(kernel): close proportional-decrease contracts and make readiness obligation-sound
```

That PR should close `decrease_to_fraction` readiness and correct false runnable evidence without changing serving.

However, the session identified a deeper foundation risk: CORE must not drift into a pile of local recognizers that behave like brittle parsers while wearing the names of `ProblemFrame` and substrate. The intended design requires semantic substrate mediation.

---

## 2. Problem

CORE's intended substrate is not merely a vocabulary table or a set of regex triggers. Words and chunks must act as probes into a semantic/constructional field.

For example, the surface chunk:

```text
buys 3 more apples
```

should not be interpreted as:

```text
if "buys" then add nearest number
```

It should surface a semantic/constructional neighborhood:

```text
buy / purchase / acquire / gain / receive
→ acquisition
→ transaction
→ possession change
→ positive object delta
→ optional money/cost delta
```

and bind roles:

```text
buyer
acquired_quantity
acquired_entity
same_entity_continuation
optional price
optional seller
question target
```

Likewise:

```text
decrease to 3/4 of 84 degrees
```

should surface a proportional state-change construction and bind:

```text
base quantity
target scale
state
question target = delta decrease, if the question asks "how much did it decrease by"
```

If the codebase treats such cues as isolated keywords, every subsequent capability becomes harder to make safe. If it treats them as constructional affordances grounded in exact spans and checked by contracts, CORE can grow a reusable problem-solving foundation.

---

## 3. Decision

Before broad substrate expansion, organ migration, or constitutional capability claims, CORE requires a deep semantic-substrate affordance audit.

The audit must determine whether the current codebase supports the intended design:

```text
surface word/chunk
→ substrate-neighborhood retrieval
→ constructional affordance
→ role obligations
→ span-grounded bindings
→ bound relation candidate
→ organ-specific ContractAssessment
→ verified derivation or refusal
```

Canonical rule:

```text
closeness proposes;
bindings ground;
contracts determine.
```

This ADR does **not** authorize immediate code removal, broad rewrites, serving migration, or unreviewed learning. It authorizes and requires a research/audit phase that may recommend consolidation, replacement, or retirement of misaligned pieces, but each material change must return through a separate evidence-backed implementation PR.

---

## 4. Required audit scope

The audit must inspect both small and large blockers to the intended design.

### 4.1 Lexical and constructional affordances

For core problem-solving words/chunks, classify whether the current system understands them as:

- isolated trigger words;
- lexical families;
- constructional affordances;
- role-binding patterns;
- substrate nodes / relation families;
- contract obligations.

Initial families include:

| Family | Example surfaces | Intended affordance |
|---|---|---|
| Acquisition / transaction | buy, buys, bought, purchase, get, acquire, receive, gain | positive object possession delta; optional money/cost delta |
| Loss / consumption | spend, use, eat, lose, give away, remove | negative possession / inventory delta |
| Transfer | give, send, receive, sell, trade | actor-to-actor movement of object/value |
| Proportional change | decrease to, reduced to, increased to, fraction of | state scale relation; delta or final target depends on question |
| Rate / frequency | per, each, every, daily, hourly, every other | rate relation or schedule/frequency relation |
| Comparison | more than, fewer than, difference, how many more | comparative/delta relation |
| Remainder / final state | left, remain, after, still has | final-state/remainder target |
| Container / part-whole | box, bag, pan, group, half of, percent of | containment, grouping, partition, or part-whole relation |

### 4.2 ProblemFrame binding quality

Inspect whether `ProblemFrame` construction is producing:

- exact source spans;
- stable mention identities;
- quantity-to-entity bindings;
- quantity-to-unit bindings;
- actor/object bindings;
- relation roles linked to mentions/facts;
- bound question targets;
- unresolved hazards instead of silent defaults.

### 4.3 Contract readiness and false positives

Measure and inspect:

- candidate contracts;
- runnable contracts;
- false runnable cases;
- missing obligations by organ;
- blocker combinations;
- target-direction errors;
- topology errors;
- hazardous ambiguity.

The audit must treat a reduction in false runnable contracts as progress when it improves truthfulness.

### 4.4 Local recognizer and legacy parser inventory

Inventory local regex/phrase recognizers and classify each as:

- allowed low-level lexical normalization;
- temporary diagnostic scaffold;
- organ-local legacy parser;
- substrate-backed constructional binder;
- candidate for consolidation;
- candidate for replacement after an evidence-backed plan.

No local recognizer may be silently promoted into a serving fact producer by wrapping it in `ProblemFrame` terminology.

### 4.5 Graph and carrier boundaries

The audit must preserve existing graph responsibility boundaries.

ADR-0144 separates:

- `generate.graph_planner.PropositionGraph` — articulation planner;
- `recognition.carrier.EpistemicGraph` — epistemic/provenance carrier;
- math-specific problem state / `ProblemFrame` / `ContractAssessment` — mathematical reasoning readiness.

The audit must not introduce a new universal IR or collapse these roles. Constitutional or architecture docs should use semantic roles, not concrete graph class names, unless a file-specific implementation is being discussed.

### 4.6 CGA substrate and exact recall alignment

Inspect whether the current system actually uses or prepares for the intended CGA/versor substrate in the relevant path:

- exact recall via approved mechanisms;
- no embeddings, ANN, HNSW, cosine substitution, or approximate recall;
- no hidden normalization;
- no stochastic fallback;
- no unreviewed semantic mutation;
- clear distinction between semantic nearness and proof/determination.

The audit should identify where semantic neighborhood retrieval is missing, duplicated, or simulated by brittle local code.

### 4.7 Evidence, promotion, and mutation boundaries

Confirm that any future foundation changes respect:

- reviewer-gated learning;
- proof-carrying promotion;
- replay and revocation;
- no `Unknown → False`;
- no `answer=False` through open-world determination;
- no sealed/corpus/report mutation outside authorized paths;
- no case-ID logic;
- no answer mining.

---

## 5. Required deliverables

The audit must produce at least these docs:

1. `docs/analysis/semantic-substrate-affordance-audit-YYYY-MM-DD.md`
   - inventory, findings, blockers, risks, and recommendations.
2. `docs/analysis/semantic-substrate-affordance-map-YYYY-MM-DD.md`
   - families, surfaces, constructional roles, substrate nodes, and relation obligations.
3. `docs/analysis/problemframe-contract-gap-taxonomy-YYYY-MM-DD.md`
   - organ-specific blockers, false readiness cases, and readiness metrics.
4. Optional handoff(s) for implementation PRs, each bounded and testable.

The audit must also produce a recommendation matrix:

| Finding | Severity | Evidence | Recommendation | Implementation PR needed? |
|---|---|---|---|---|

Severity values:

- `FOUNDATION_BLOCKER`
- `READINESS_FALSE_POSITIVE`
- `LEGACY_BYPASS_RISK`
- `DUPLICATE_SEMANTICS`
- `MISSING_AFFORDANCE`
- `DOC_GOVERNANCE_DRIFT`
- `DEFERRED_RESEARCH`

---

## 6. Non-goals

This ADR does not authorize:

- serving changes;
- organ migration;
- broad parser introduction;
- generic solver introduction;
- deletion or replacement of runtime modules without a separate proposal;
- report/case/sealed artifact mutation;
- unreviewed learning;
- claim promotion;
- physical action;
- hidden background execution;
- stochastic or approximate retrieval.

---

## 7. Acceptance criteria for the audit

The audit is complete when it has:

1. traced the current #829–#831 math path end to end;
2. inventoried all major local recognizers and phrase binders that affect GSM8K / `ProblemFrame` readiness;
3. identified where semantic affordance retrieval exists, is missing, or is simulated locally;
4. identified false runnable and false candidate patterns;
5. mapped at least the initial affordance families in §4.1;
6. proposed a bounded implementation sequence;
7. preserved all serving metrics and `wrong_ids == []` during any validation runs;
8. recommended no destructive change without evidence, tests, and a separate PR;
9. produced a handoff that a high-capability implementation agent can execute without reinterpreting the doctrine.

---

## 8. Engineering gates for any follow-up implementation

Any implementation PR resulting from the audit must include:

- typed contract tests;
- exact span tests;
- constructional affordance tests;
- confusers and metamorphic tests;
- no-new-legacy-parser checks;
- serving comparison with `wrong_ids == []`;
- `git diff --check`;
- no report/case/sealed changes unless explicitly authorized;
- docs explaining how the change moves from local trigger behavior toward substrate-backed constructional binding.

---

## 9. Immediate plan interaction

This ADR does not block the already-selected bounded PR:

```text
feat(kernel): close proportional-decrease contracts and make readiness obligation-sound
```

That PR is itself a proving slice of this ADR's doctrine: `decrease to <fraction> of <state>` must be treated as a constructional affordance with bound roles and organ-specific obligations, not as a generic fraction/decrease parser.

`percent_partition` remains deferred until its topology, target direction, and heterogeneous positive evidence are sufficient for ProblemFrame-only migration.

---

## 10. Consequences

- Future foundation work must be evaluated against semantic-substrate alignment, not only local test pass/fail.
- `contract_runnable_count` remains the honest readiness metric for ProblemFrame-native migration.
- False runnable removal is recognized as progress when it improves truthfulness.
- Agents must not assume that keyword triggers are adequate evidence of relation understanding.
- Substrate design must explicitly support chunk-level constructional affordance retrieval.
- Concrete graph classes keep their existing responsibilities unless separately amended by evidence-backed ADR/PR.

---

## 11. Summary doctrine

```text
Words and chunks are probes into the semantic substrate.
They surface candidate affordances and relation families.
Semantic closeness proposes.
Exact span bindings ground.
Organ-specific contracts determine.
Unsupported or ambiguous cases refuse.
```
