# zero-code-domain-acquisition eval lane

## What it measures

Whether a domain author can bring CORE to >=80% articulation accuracy on a
novel domain using *only* pack authoring (vocabulary, predicates, teaching
examples) — no Python edits allowed. Every Python edit required is logged as
an "engineering gap."

This measures the system's extensibility contract: if CORE is well-designed,
new domains should be acquirable through data alone.

## Surprise domains

Three domains chosen because they were never touched during core development:

| ID | Domain | Core proposition type |
|----|--------|----------------------|
| D1 | Kinship relations | relational (X is_parent_of Y) |
| D2 | Calendar relations | temporal ordering (Monday precedes Tuesday) |
| D3 | Color taxonomy | hierarchical/property (red is_warmer_than blue) |

## Pack-only authoring kit (per domain)

Each domain provides:

1. **Vocabulary** — lexicon entries (nouns, verbs, relations) in JSONL format
2. **Relation predicates** — semantic predicates specific to the domain
3. **Axiom list** — ground-truth propositions that define the domain
4. **Teaching examples** (~20) — reviewed teaching events exercising the domain
5. **Articulation prompts** (~30) — PropositionGraph inputs to score against

## Scoring rubric

A prompt passes if the realized surface:
1. Is in `accept_surfaces` OR satisfies all `constraints`
2. Contains all words in `must_contain`
3. Respects `word_order` (subsequence check)
4. Does not exceed `max_words`

## Pass thresholds

- v1: >= 80% on public test set per domain, >= 75% on holdout
- Overall: all 3 domains must independently pass

## Engineering gap log

Any Python edit required to pass is logged in `evals/zero_code_domain_acquisition/gaps.md`
with:
- What broke
- Which domain triggered it
- What the fix was
- Whether it was domain-specific or general

An empty gap log at v1 pass means the system's extensibility contract is solid.

## Evaluation protocol

1. Load domain pack into vocabulary manifold
2. Apply teaching examples through teaching loop
3. Run articulation prompts through the realizer pipeline
4. Score against acceptance criteria
5. Log any failures that require Python fixes as engineering gaps
