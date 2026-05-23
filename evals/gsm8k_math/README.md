# `gsm8k_math` — Curated Eval Split for the GSM8K Evaluation Lane

**Status:** ADR-0119.2. 200 cases authored.
**Schema source of truth:** `generate/math_problem_graph.py` (typed dataclasses).
**Format:** JSONL — one case per line.

## Why this set is not drawn from GSM8K

The GSM8K eval lane (ADR-0119) treats the actual GSM8K corpus as a sealed holdout test set. To preserve that integrity, we author this dataset independently in the **same style** as GSM8K (grade-school word problems with integer answers and 1-8 reasoning steps) but using our own vocabulary and grammar, ensuring zero overlap with the sealed holdout.

The dataset measures the solver pipeline (parser → solver → verifier → realizer). A correctly-parsed and solved problem is one whose parser output matches the ground-truth graph byte-for-byte and solves to the expected answer and unit.

## Case schema

Each line is one JSON object:

```json
{
  "id": "gma-NNN",
  "problem": "<the natural-language word problem>",
  "expected_answer": <integer>,
  "expected_unit": "<unit string>",
  "ground_truth_graph": {
    "entities": ["<entity_1>", "<entity_2>", ...],
    "initial_state": [
      {"entity": "<entity>", "quantity": {"unit": "<unit>", "value": <number>}},
      ...
    ],
    "operations": [
      {"actor": "<entity>", "kind": "<add|subtract|transfer|multiply|divide>",
       "operand": {"unit": "<unit>", "value": <number>},
       "target": "<entity>"  /* required when kind=transfer; omitted otherwise */},
      ...
    ],
    "unknown": {"entity": "<entity>" | null, "unit": "<unit>"}
  },
  "patterns": ["<pattern_tag_1>", "<pattern_tag_2>", ...],
  "notes": "<authoring rationale>"
}
```

### Field rules

- **`id`** — `gma-NNN` where:
  - `gma-001` ... `gma-050` are for the `dev` split.
  - `gma-101` ... `gma-250` are for the `public` split.
- **`problem`** — one or more complete English sentences ending in a question. Use Title-Cased proper names for entities ("Sam", "Anna's Toy Box"). Be consistent: the same entity always spelled the same way in `problem` and `ground_truth_graph.entities`.
- **`expected_answer`** — the integer answer to the question.
- **`expected_unit`** — the unit string the answer is in. Must match `ground_truth_graph.unknown.unit` byte-for-byte.
- **`ground_truth_graph.entities`** — tuple in **order of first introduction in the problem text**. Not alphabetical. No duplicates.
- **`ground_truth_graph.initial_state`** — every entity that starts the problem with a known quantity. Empty list is legal if no initial possessions are asserted (rare).
- **`ground_truth_graph.operations`** — in **source-text order**. Empty list is legal (e.g. multi-entity sum questions with no mutations).
- **`ground_truth_graph.unknown.entity`** — set to the entity the question asks about, or `null` if the question asks for a total across all entities ("How many ... in total?"; "How many do they have altogether?").
- **`patterns`** — tag list naming the constructions used. See [Pattern registry](#pattern-registry) below.
- **`notes`** — author-supplied one-sentence rationale. Read by future reviewers when the parser fails this case.

### Canonicalization rules

- **Units** — lowercase, plural form ("apples", "candies", "dollars", "hours"). Use "dollars" for "$" quantities; the parser is expected to rewrite the "$" surface to the canonical unit.
- **Entities** — preserve capitalization as written. Do not lowercase.
- **Numbers** — integers when the text shows integers.
- **Operation kinds** — exactly one of `add`, `subtract`, `transfer`, `multiply`, `divide`. Choose the one closest to the verb in the text:
  - "buys / gets / receives / earns / finds / adds" → `add`
  - "eats / loses / sells / spends / drops / uses / removes" → `subtract`
  - "gives / sends / hands / passes / mails / transfers" → `transfer` (and set `target`)
  - "doubles / triples / Nx as many" → `multiply`
  - "splits evenly into N / N% of / shares equally with N people" → `divide`

## Scope limits (ADR-0119.2)

The parser and solver handle the following patterns and no others. Cases violating these constraints are out of scope:

- **NO Time-modal / conditional phrasing** ("If Sam had 5 apples, ...") — out of scope. Use direct declarative phrasing only.
- **NO Rate/per-unit pricing requiring inference** ("Each apple costs $2. Sam buys 4. How much does he spend?") — out of scope. A simpler variant ("Sam spends $8 on apples. How much does he have left?") IS in scope.
- **NO Multi-clause / compound-question problems** ("How many does Sam have, and how many does Tom have?") — out of scope. One unknown per case.
- **NO Implicit-entity / generic plural** ("There are 5 boys. Each has 2 apples.") — out of scope. Use named entities.
- **NO Comparative phrasing without explicit numbers** ("Sam has twice as many as Tom") — out of scope. Use numeric multipliers only ("Sam has 2 times 3 apples").
- **NO metaphor or mixed units within one entity** — out of scope. Keep units consistent.
- **NO numeric magnitude beyond integer scope** — out of scope. Only use integers.

## Pattern registry

When tagging a case under `patterns`, draw from this list.

| Pattern tag | Construction | Example |
|---|---|---|
| `initial_has` | "<Entity> has <N> <unit>." | "Sam has 5 apples." |
| `initial_there_are` | "There are <N> <unit>." (no entity; rare) | "There are 12 candies on the table." |
| `operation_buy_more` | "<Entity> buys <N> more." | "He buys 3 more." |
| `operation_get_more` | "<Entity> gets <N> more <unit>." | "She gets 4 more pencils." |
| `operation_find_adds` | "<Entity> finds <N>." | "Sam finds 2 apples on the path." |
| `operation_eat_loses` | "<Entity> eats <N>." | "Tom eats 4 candies." |
| `operation_lose_loses` | "<Entity> loses <N>." | "Anna loses 3 marbles." |
| `operation_sell_loses` | "<Entity> sells <N>." | "Lisa sells 2 books." |
| `operation_donate_loses` | "<Entity> donates <N>." | "Lisa donates 3 books." |
| `operation_use_loses` | "<Entity> uses <N>." | "He uses 2 sheets of paper." |
| `operation_give_transfer` | "<Entity> gives <N> to <Entity2>." | "Anna gives 3 marbles to Ben." |
| `operation_send_transfer` | "<Entity> sends <N> to <Entity2>." | "Tom sends 4 letters to Sara." |
| `operation_double` | "<Entity> doubles ..." | "Sam doubles his savings." |
| `operation_triple` | "<Entity> triples ..." | "Sam triples his stickers." |
| `operation_split_divide` | "splits/shares evenly" | "They split 12 candies evenly." |
| `question_how_many_entity` | "How many <unit> does <E> have?" | "How many apples does Sam have?" |
| `question_how_many_left` | "How many <unit> ... left?" | "How many candies does Tom have left?" |
| `question_how_many_total` | "How many <unit> ... in total?" / "altogether" | "How many stickers do they have in total?" |
| `question_how_many_now` | "How many <unit> ... now?" | "How many marbles does Anna have now?" |
