# Session 2026-06-19 — Semantic substrate affordances, contract readiness, and the foundation audit pivot

**Status:** recorded for continuation. **Headline:** After #829–#831 made `ProblemFrame` operational and measurable, the session clarified that the next foundation problem is not another local parser or premature organ migration. The core design target is a **semantic-substrate affordance loop**: words and chunks probe the substrate, surface nearby constructional meanings and relation families, bind roles to exact evidence spans, and only then allow `ContractAssessment` / organs to determine or refuse.

`Docs-only record. No runtime, serving, eval report, pack, corpus, policy, identity, or sealed artifact changes are made by this session note.`

---

## TL;DR

1. **#831 changed the truth metric.** The project moved from surface/schema recognition to measurable contract readiness: typed mentions, bindings, bound relations, bound question targets, and pure `ContractAssessment` diagnostics. #831's merged evidence recorded `candidate contracts = 42/423`, `runnable contracts = 1/1`, serving still `train 30/20/0`, `holdout 5/495/0`, with `wrong_ids=[]`.
2. **GPT-5.5 Thinking XHIGH rejected premature `percent_partition` migration.** The decision memo concluded that readiness was still obligation-loose: broadening extraction or migrating `percent_partition` would preserve or amplify false readiness. The recommended next implementation is proportional-change contract closure: bind `decrease_to_fraction`, delta targets, and organ-specific blockers while correcting the false runnable holdout.
3. **The constitutional program was refined, not adopted monolithically.** The correct split is three layers: a small constitutional kernel (`ADR-0223` later), a mutable critical-program roadmap, and versioned evidence profiles. The canonical spine must use semantic roles, not force `PropositionGraph` into a universal reasoning carrier; ADR-0144 distinguishes articulation `PropositionGraph`, epistemic `EpistemicGraph`, and math problem state.
4. **The operator's design correction became the key doctrine.** Dead giveaways are not isolated trigger words. They are **constructional affordances**. A chunk such as `buys 3 more apples` should probe the substrate and surface acquisition / transaction / positive possession-delta affordances, then bind actor, quantity, item, prior state, optional cost, and target.
5. **CGA semantic nearness remains essential but not sufficient.** Substrate proximity should propose candidate nodes and relation families (`buy ≈ purchase ≈ acquire ≈ gain`), while exact span bindings and contracts determine whether anything can be asserted. The governing rule: **closeness proposes; bindings ground; contracts determine.**
6. **A foundation audit is required before broad substrate work.** The current risk is accumulating local recognizers and false contract candidates instead of building the intended semantic substrate. A new ADR is required to mandate a deep, repository-wide substrate-alignment audit before agents make broad foundational changes.

---

## Context entering the session

The active stack after the latest merged work:

| PR | Meaning |
|---|---|
| #829 | Kernel Substrate Tranche 1: scalar equivalence, unit dimensions, ambiguity hazards, process-frame schemas, `ProblemFrame` skeleton, morphology foundations. |
| #830 | `ProblemFrame` operationalization and legacy-deprecation guardrails. |
| #831 | Span-grounded mentions/bindings/relations, bound question targets, `ContractAssessment`, adequacy reporting, and contract-gap morphology recommendations. |

#831's evidence established that readiness must be measured by **runnable contracts**, not by recognized schema presence. The merged PR body recorded:

```text
Train 50:
  entity mention present: 50
  quantity binding present: 46
  bound process relation present: 16
  bound question target present: 42
  candidate contracts: 42
  runnable contracts: 1

Holdout 500:
  entity mention present: 494
  quantity binding present: 452
  bound process relation present: 124
  bound question target present: 402
  candidate contracts: 423
  runnable contracts: 1
```

This means CORE now has a measurable bridge from text into typed readiness, but the bridge is thin. It proves the method, not broad serving readiness.

---

## The XHIGH decision memo

The next-decision prompt asked GPT-5.5 Thinking XHIGH to choose the highest-leverage PR after #829–#831. The decision memo recommended:

```text
feat(kernel): close proportional-decrease contracts and make readiness obligation-sound
branch: codex/problemframe-proportional-change-closure
```

The reasons:

- Current readiness blockers are not yet sufficiently precise.
- `percent_partition` readiness is too loose: candidates can arise from broad `partition`/`consumption` recognition rather than full topology and target-direction proof.
- The existing false runnable holdout is an inverse-reconstruction case outside the forward `percent_partition` contract.
- `fraction_decrease` has mature confusers and a clear train case (`0005`) that can prove a second genuine ProblemFrame-runnable contract without serving migration.

Expected diagnostic movement:

```text
Train runnable contracts: 1 → 2
  - 0005: fraction_decrease
  - 0046: percent_partition

Holdout runnable contracts: 1 → 0
  - remove the false positive; this is a truthfulness improvement, not a regression.
```

Hard boundary: no serving integration, no derivation-organ migration, no `math_candidate_graph.py` change, no `report.json`, no sealed mutation, and no raw-text fallback behind a `ProblemFrame` call.

---

## The constitutional-program correction

A broader AGI-capable constitutional plan was discussed. The useful direction was kept, but two important corrections were made:

### 1. Split constitution, roadmap, and evidence profiles

The correct structure is:

```text
1. Small constitutional ADR kernel.
2. Mutable critical-program roadmap.
3. Versioned evidence profiles with frozen benchmarks/thresholds.
```

This keeps benchmark churn and implementation sequencing from rewriting the constitution. A future claim such as `agi-capable-v1` should be reproducible against a frozen evidence profile, not embedded forever in the constitutional core.

### 2. Do not make `PropositionGraph` universal

The first constitutional spine over-named `PropositionGraph`. ADR-0144 already separates:

- `generate.graph_planner.PropositionGraph` — articulation planner.
- `recognition.carrier.EpistemicGraph` — epistemic/provenance carrier.
- `MathProblemGraph` / math state — mathematical reasoning state.

The corrected constitutional spine uses semantic roles:

```text
observation
→ grounded evidence
→ domain frame
→ admissible domain model
→ verified derivation/proof
→ epistemic standing
→ articulation plan or authorized action
```

For the current math path, the realization is narrower:

```text
text
→ KernelFacts
→ ProblemFrame
→ ContractAssessment
→ contract-backed derivation organ
→ independently verified resolution
→ existing admission and articulation path
```

This preserves ADR-0207's anti-universal-IR posture: use typed adapters between domain structures; do not introduce another universal reader/graph by accident.

---

## The operator's substrate doctrine correction

The operator challenged a simplified explanation that treated `buys` as a generic cue for addition. The corrected doctrine is:

```text
Dead giveaways are constructional affordances, not isolated trigger words.
```

A word such as `buys` does not merely mean `add`. It probes a semantic neighborhood:

```text
buy / bought / purchase / acquire / get / gain / receive
→ acquisition
→ transaction
→ possession change
→ positive object delta
→ optional money/cost delta
```

But the meaningful unit is often the chunk:

```text
buys 3 more apples
```

That chunk should surface:

```text
surface chunk: "buys 3 more apples"
semantic neighborhood: buy, purchase, acquire, gain possession, transaction
construction: actor buys quantity more entity
roles:
  buyer
  acquired_quantity = 3
  acquired_entity = apples
  same_entity_continuation = true
  object_delta = positive
optional roles:
  price
  seller
  money_delta
operator candidates:
  add_to_inventory
  compute_cost
  compute_remaining_money, if money target is present
hazards:
  entity mismatch
  target mismatch
  negation
  comparison rather than acquisition
```

The same principle applies to proportional change:

```text
decrease to 3/4 of 84 degrees
```

should surface:

```text
semantic affordance: proportional state change
construction: state decreases to fraction of base
roles:
  base quantity = 84 degrees
  target scale = 3/4
  relation = decrease_to_fraction
question target:
  delta decrease, if asked "how much did it decrease by"
blocked cases:
  final-value question
  affine-more-than fraction
  multiple fractions
  ambiguous base
```

---

## Working model: substrate-mediated cognition loop

The intended loop is:

```text
chunk enters the field
→ nearby semantic / constructional affordances resonate
→ candidate nodes and relation families surface
→ roles bind to exact evidence spans
→ organ-specific contracts assess obligations
→ determination, refusal, articulation, or action follows
```

Or shorter:

```text
chunk
→ semantic neighborhood
→ constructional affordance
→ role obligations
→ bound relation candidate
→ contract assessment
```

This is the bridge between the CGA substrate and the typed problem-solving stack.

The CGA inner product / substrate should provide **semantic gravity**: related meanings and constructions become easy to retrieve. But closeness does not license truth. Truth promotion requires grounded bindings and contracts.

Canonical rule:

```text
closeness proposes;
bindings ground;
contracts determine.
```

---

## Foundation risk identified

The operator's warning was accepted: if the project builds a pile of local recognizers, it will become harder each sprint. Every later capability will fight earlier shortcuts.

The dangerous path:

```text
surface keyword
→ local regex
→ one-off organ behavior
→ patch more confusers forever
```

The intended path:

```text
surface chunk
→ substrate affordance retrieval
→ constructional role binding
→ ProblemFrame relation
→ ContractAssessment obligations
→ verified derivation or refusal
```

Therefore, before broad foundation changes, CORE needs a deep audit of how the current codebase aligns or misaligns with the intended substrate-mediated cognition loop.

---

## New ADR required

This session produced the requirement for a new ADR:

```text
ADR-0223: Semantic Substrate Affordance Audit and Foundation Alignment
```

The ADR must require a deep-dive research pass over small and large details that may be blocking the intended design, including but not limited to:

- lexical vs constructional affordances;
- local regex recognizers vs substrate-backed constructional retrieval;
- ProblemFrame binding quality;
- false runnable contracts;
- relation topology and question-target direction;
- graph/carrier boundaries (`ProblemFrame`, `EpistemicGraph`, `PropositionGraph`, math state);
- legacy parser bypasses;
- substrate pack coverage;
- morphology/planner recommendation evidence;
- proof/admission boundaries;
- exact recall / CGA-neighborhood usage;
- places where the code's foundation makes later correctness harder.

The ADR should authorize research and recommendations, not immediate destructive edits. Any proposed removal, replacement, or consolidation must return as evidence-backed proposals and separate implementation PRs.

---

## Immediate plan of record

1. Continue with the already-selected implementation PR:

```text
feat(kernel): close proportional-decrease contracts and make readiness obligation-sound
branch: codex/problemframe-proportional-change-closure
```

2. Record this session and ADR as docs-only work.
3. Keep `percent_partition` deferred until its topology, target direction, and heterogeneous positive evidence are sufficient for ProblemFrame-only migration.
4. Use the new ADR to guide a high-skill research/audit effort, not to authorize unreviewed rewrites.

---

## Open / next

- Run or commission the substrate-affordance audit required by ADR-0223.
- Ensure the proportional-decrease PR interprets `decrease to <fraction> of <state>` as a constructional affordance, not as keyword matching.
- Update future constitutional documents to use semantic roles rather than concrete universal graph classes.
- Consider adding the doctrine below to architecture docs after ADR-0223 is ratified:

```text
Words and chunks are probes into the semantic substrate.
They surface candidate affordances and relation families.
Only grounded bindings and contracts can promote those affordances into determinations.
```
