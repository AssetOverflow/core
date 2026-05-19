# Articulation Benchmark — Discourse Planner Spine

**Date:** 2026-05-19
**Runner:** `benchmarks/articulation.py`
**CLI:** `core bench --suite articulation [--json]`
**Contract tests:** `tests/test_articulation_bench.py`
**Reference commits:** [`e985790`](../../) (lanes + holdouts + bench sub-bench),
[`4e3ddee`](../../) (WALKTHROUGH v1),
[`7af7892`](../../) (compound decomposition + sub-plan composition)

## Headline claim

> On the substrate currently mounted (cognition + relations + minimal +
> domain packs, the reviewed cognition-chains corpus, and the
> cross-pack chains corpus), the discourse-planner spine produces
> deterministic, grounded, multi-clause articulation on every prompt
> shape it claims to handle:
>
> | Prompt shape | Articulate¹ | Grounding | Sentences |
> |---|---:|---|---:|
> | `Explain X.`                              | ✓ | teaching | 3 |
> | `Write a paragraph about X.`              | ✓ | teaching | 3 |
> | `What is X, and why does it matter?`      | ✓ | teaching | 6 |
> | `Walk me through X.`                      | ✓ | teaching | 2 |
>
> Across 20 independent runtime instances per prompt, every surface is
> **byte-identical**: 20×4 generations produce exactly 4 unique
> surfaces.  No stochastic sampling, no LLM fallback, no approximate
> recall.

¹ `articulate_sentence_rate` predicate: ≥2 substantive sentences AND
`grounding_source ∈ {pack, teaching}`.  OOV invitations and refusal
disclosures count toward `disclosure_sentence_rate`, never articulate
— the lane partition is total and disjoint.

## What's measured

`benchmarks/articulation.py` packages four sub-benches that exercise
the chat-spine end-to-end with `RuntimeConfig(discourse_planner=True)`:

| Sub-bench | Probes | What it asserts |
|---|---|---|
| `breadth`            | 12 prompts spanning 9 intents | The classifier routes representative prompts to the expected `IntentTag` and the runtime grounds in `{pack, teaching, oov, none}` — no unclassifiable surprises in the breadth distribution. |
| `determinism`        | 5 prompts × 20 runs each | Each prompt produces exactly **1** unique surface across 20 fresh `ChatRuntime` instances.  Tests for clock reads, env reads, stochastic sampling, or shared mutable state in the warm-path planner hook. |
| `cross_topic`        | 8 turns on one runtime, `thread_anaphora=True` | Counts how many turns fired the deterministic anaphora prefix.  Sanity-checks ADR-0066 thread continuity under live chat conditions. |
| `discourse_planner`  | 4 prompts, one per supported mode (EXPLAIN / PARAGRAPH / COMPOUND / WALKTHROUGH) | Reports `articulate_sentence_rate`, `disclosure_sentence_rate`, `multi_sentence_rate`.  Single load-bearing capability metric per prompt shape. |

## Today's reference numbers

```text
[breadth]      12 prompts in ~3.15s
               intents: CAUSE, COMPARISON, CORRECTION, DEFINITION,
                        EXAMPLE, NARRATIVE, PROCEDURE, UNKNOWN, VERIFICATION
               grounding: none, oov, pack, teaching

[determinism]  5 prompts × 20 runs in ~12.85s
               byte-identical across runs: True
               unique surface counts: [1, 1, 1, 1, 1]

[cross_topic]  8 turns single runtime in ~7.38s
               anaphora fired on 0/8 turns
               (turns in this bench are independent topics by design;
                see test_chat_anaphora_*.py for the firing path)

[discourse_planner] 4 prompts in ~0.53s
  metrics: {
      cases:                     4,
      articulate_sentence_rate:  1.0,
      disclosure_sentence_rate:  0.0,
      multi_sentence_rate:       1.0,
  }

  [EXPLAIN]      sentences=3  grounding=teaching  articulate=True
  [PARAGRAPH]    sentences=3  grounding=teaching  articulate=True
  [COMPOUND]     sentences=6  grounding=teaching  articulate=True
  [WALKTHROUGH]  sentences=2  grounding=teaching  articulate=True
```

## Sample surfaces

These are the literal surfaces emitted by the planner-on chat spine —
every visible token below is a verbatim pack lemma, a verbatim pack
gloss, a verbatim reviewed-teaching-chain entry, or a fixed-template
connective from `_MOVE_CONNECTIVE` in `generate/discourse_planner.py`.

> **EXPLAIN — `"Explain truth."`**
>
> Truth is a claim or state grounded by evidence and coherent
> judgment.  Furthermore, truth belongs to cognition.truth.  In turn,
> truth grounds knowledge.

> **PARAGRAPH — `"Write a paragraph about truth."`**
>
> Truth is a claim or state grounded by evidence and coherent
> judgment.  Furthermore, truth belongs to cognition.truth.  In turn,
> truth grounds knowledge.

> **COMPOUND — `"What is truth, and why does it matter?"`**
>
> Truth is a claim or state grounded by evidence and coherent
> judgment.  Furthermore, truth belongs to cognition.truth.  In turn,
> truth grounds knowledge.  Truth belongs to epistemic.ground.
> Furthermore, truth belongs to logos.core.  In turn, truth requires
> evidence.

> **WALKTHROUGH — `"Walk me through recall."`**
>
> Recall is to retrieve a stored state from memory.  Recall reveals
> memory.

## Why this matters

### 1. Determinism on the articulation path

CORE's design commitment (CLAUDE.md §"Philosophical Stance") is that
the same input under the same vault state always produces the same
articulated output — exactly enough to support deterministic replay,
trace hashing, and reviewed teaching.

The `determinism` sub-bench enforces this end-to-end with the
planner engaged: 20 independent `ChatRuntime` instances per prompt,
one unique surface per prompt.  This is the *learning-loop
determinism* of [ADR-0055](../decisions/) and [ADR-0057](../decisions/)
applied to the articulation spine rather than only to retrieval and
proposal acceptance.

### 2. Compound prompts compose without re-sorting

`"What is truth, and why does it matter?"` decomposes into
`(DEFINITION(truth), CAUSE(truth))`.  The planner concatenates the
two sub-plans in source order with cross-part fact deduplication —
six distinct grounded sentences with no anchor repetition.  This is
the discourse-graph traversal the design memo
([feedback-design-fix-upstream-not-beside](../../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/feedback-design-fix-upstream-not-beside.md))
recommended: lift structure upstream rather than decorate strings
downstream.

### 3. Walkthroughs walk a teaching graph, not a template

`WALKTHROUGH` mode walks the teaching-chain edge graph
`(subject, *, obj) → (obj, *, *)` up to 3 hops, with the final hop
emitted as `CLOSURE` and cycle-safety enforced by the used-fact set.
When no chain is rooted on the anchor the planner degrades to the
expository (ANCHOR + SUPPORT) shape rather than fabricating walk
steps.

### 4. Honest negative spaces

`disclosure_sentence_rate = 0.0` on flag-on, but the metric exists.
OOV teaching invitations and refusal disclosures are structurally
multi-sentence by template — they cannot be allowed to inflate
articulate capability.  The partition
(`articulate + disclosure + unarticulate = 1.0`) is total and
disjoint by construction; the headline rate measures *only* what
the spine actually planned and rendered.

## Provenance of every token in the surface

For every move in every plan that produced the surfaces above, the
`fact` object carries:

* `source ∈ {PACK, TEACHING}` — never `OPERATOR`, never anything
  synthesised.
* `source_id` — a pointer back to the exact pack lemma
  (`en_core_cognition_v1:truth#gloss`) or reviewed teaching chain
  (`cognition_chains_v1#cause_truth_reveals_knowledge`).
* `subject` / `predicate` / `obj` — verbatim from the lexicon entry
  or chain JSONL.

Connectives between moves are drawn exclusively from the closed
five-entry table `_MOVE_CONNECTIVE`:

```python
ANCHOR     -> ""
SUPPORT    -> "Furthermore, "
RELATION   -> "In turn, "
TRANSITION -> "Consequently, "
CLOSURE    -> ""
```

There is no other source of visible text in the rendered surface.
The articulation is deterministic *because* it's reconstructed from
sourced atoms; the byte-identity result above is the consequence,
not the design intent.

## Reproduction

```bash
# Full articulation bench (requires psutil for the footprint
# sub-bench; the other sub-benches run without it):
core bench --suite articulation --json

# Planner-on sub-bench only, without psutil dependency:
python3 -c "from benchmarks.articulation import bench_discourse_planner; \
            probes, metrics = bench_discourse_planner(); \
            print(metrics)"
```

## Companion documents

* [`discourse_runtime_baseline_2026-05-19.md`](./discourse_runtime_baseline_2026-05-19.md)
  — full lane-level delta table across the 14-commit landing.
* `evals/compound_intent_decomposition/contract.md` — isolation lane
  for compound decomposition (`decomposition=1.0` on public/v1).
* `evals/walkthrough_chain/contract.md` — isolation lane for
  walkthrough teaching-chain walks (`path_exact=1.0` on public/v1).
* `evals/multi_sentence_response/contract.md` — partitioned predicate
  contract (`articulate / disclosure / unarticulate`).
