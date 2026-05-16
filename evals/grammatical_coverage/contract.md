# grammatical-coverage eval lane

## What it measures

Whether the deterministic realizer (`generate/realizer.py`, `generate/templates.py`,
`generate/semantic_templates.py`, `generate/articulation.py`) can produce grammatical
English surfaces for a defined set of syntactic constructions from PropositionGraph
inputs.

This is the fluency gate: if the realizer cannot produce correct surface forms for
these constructions, the system is not ready for curriculum-era teaching.

## Target constructions (English v1)

| ID | Construction | Example surface family |
|----|---|---|
| C01 | Simple declarative (SVO) | "light reveals truth" |
| C02 | Negation | "light does not obscure truth" |
| C03 | Conjunction (and) | "light and truth ground knowledge" |
| C04 | Disjunction (or) | "light or darkness precedes dawn" |
| C05 | Embedded clause (that-complement) | "knowledge shows that light precedes truth" |
| C06 | Relative clause (who/which/that) | "truth, which grounds knowledge, reveals light" |
| C07 | Universal quantification | "all light reveals truth" |
| C08 | Existential quantification | "some knowledge grounds truth" |
| C09 | Past tense | "light revealed truth" |
| C10 | Present tense | "light reveals truth" |
| C11 | Future tense | "light will reveal truth" |
| C12 | Perfective aspect | "light has revealed truth" |
| C13 | Imperfective aspect | "light is revealing truth" |

## Input format

Each case is a JSONL entry with:

```json
{
  "id": "gram_C01_001",
  "construction": "C01",
  "construction_name": "simple_declarative",
  "proposition_graph": {
    "nodes": [
      {"node_id": "n1", "subject": "light", "predicate": "reveals", "obj": "truth"}
    ],
    "edges": []
  },
  "accept_surfaces": ["light reveals truth"],
  "reject_surfaces": ["truth reveals light"],
  "constraints": {
    "must_contain": ["light", "reveals", "truth"],
    "word_order": ["light", "reveals", "truth"],
    "max_words": 8
  }
}
```

## Scoring rubric

A case passes if the realized surface:
1. Is in `accept_surfaces` OR satisfies all `constraints`
2. Is NOT in `reject_surfaces`
3. Contains all words in `must_contain`
4. Respects `word_order` (subsequence check, not contiguous)
5. Does not exceed `max_words`

## Pass thresholds

- v1: >= 95% on public test set, >= 90% on holdout
- v2 generation triggered on v1 pass

## Baseline

Frontier models are prompted with the PropositionGraph JSON and asked to
produce a grammatical English surface. Expected baseline: near-perfect on v1
constructions (these are trivial for an LLM).

The structural advantage CORE demonstrates here is not accuracy (both should
score high on v1) but determinism: same input always produces the same output,
with provenance to the template/construction that generated it.
