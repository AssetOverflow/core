# `gsm8k_parser_dev` — Curated Dev Set for the ADR-0115 Math Problem Parser

**Status:** ADR-0115 Phase 1.1 (initial seed). 5 of 50 target cases authored.
**Schema source of truth:** `generate/math_problem_graph.py` (typed dataclasses).
**Format:** JSONL — one case per line.

## Why this dev set is **not** drawn from GSM8K

The eventual GSM8K eval lane (ADR-0119) treats the actual GSM8K corpus as
sealed test material. To preserve that integrity we author this dev set
independently in the **same style** as GSM8K (grade-school word problems
with integer answers and 1-8 reasoning steps) but with no overlap.

The dev set measures the **parser**, not the difficulty of the problem.
A correctly-parsed problem is one whose `parser(problem.text) ==
problem.ground_truth_graph` byte-equal.

## Case schema

Each line is one JSON object:

```json
{
  "id": "gpd-NNN",
  "problem": "<the natural-language word problem>",
  "expected_answer": <integer or float>,
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

- **`id`** — `gpd-NNN` zero-padded to 3 digits, sequential across the file.
- **`problem`** — one or more complete English sentences ending in a question.
  Use Title-Cased proper names for entities ("Sam", "Anna's Toy Box"). Be
  consistent: the same entity always spelled the same way in `problem` and
  `ground_truth_graph.entities`.
- **`expected_answer`** — the integer (or float) answer to the question.
- **`expected_unit`** — the unit string the answer is in. Must match
  `ground_truth_graph.unknown.unit` byte-for-byte.
- **`ground_truth_graph.entities`** — tuple in **order of first introduction
  in the problem text**. Not alphabetical. No duplicates.
- **`ground_truth_graph.initial_state`** — every entity that starts the
  problem with a known quantity. Empty list is legal if no initial
  possessions are asserted (rare).
- **`ground_truth_graph.operations`** — in **source-text order**. Empty list
  is legal (e.g. multi-entity sum questions with no mutations).
- **`ground_truth_graph.unknown.entity`** — set to the entity the question
  asks about, or `null` if the question asks for a total across all entities
  ("How many ... in total?"; "How many do they have altogether?").
- **`patterns`** — tag list naming the constructions used. See [Pattern
  registry](#pattern-registry) below.
- **`notes`** — author-supplied one-sentence rationale. Read by future
  reviewers when the parser fails this case.

### Canonicalization rules

- **Units** — lowercase, plural form ("apples", "candies", "dollars",
  "hours"). Use "dollars" for "$" quantities; the parser is expected to
  rewrite the "$" surface to the canonical unit.
- **Entities** — preserve capitalization as written. Do not lowercase.
- **Numbers** — integers when the text shows integers. Use floats only
  if the problem text mentions fractional units explicitly (rare in
  grade-school problems).
- **Operation kinds** — exactly one of `add`, `subtract`, `transfer`,
  `multiply`, `divide`. Choose the one closest to the verb in the text:
  - "buys / gets / receives / earns / finds / adds" → `add`
  - "eats / loses / sells / spends / drops / uses / removes" → `subtract`
  - "gives / sends / hands / passes / mails / transfers" → `transfer`
    (and set `target`)
  - "doubles / triples / Nx as many" → `multiply`
  - "splits evenly into N / N% of / shares equally with N people" → `divide`

### What this dev set does NOT cover (Phase 1.1 scope)

The parser landing under ADR-0115 will handle the following patterns and
no others. Cases violating these constraints belong to a later phase
and should not appear in this file:

- **Time-modal / conditional phrasing** ("If Sam had 5 apples, ...") —
  out of scope for Phase 1.1. Use direct declarative phrasing only.
- **Rate/per-unit pricing requiring inference** ("Each apple costs $2.
  Sam buys 4. How much does he spend?") — out of scope. A simpler
  variant ("Sam spends $8 on apples. How much does he have left?") IS
  in scope.
- **Multi-clause / compound-question problems** ("How many does Sam
  have, and how many does Tom have?") — out of scope. One unknown
  per case.
- **Implicit-entity / generic plural** ("There are 5 boys. Each has 2
  apples.") — out of scope. Use named entities.
- **Comparative phrasing without explicit numbers** ("Sam has twice as
  many as Tom") — out of scope. Use numeric multipliers only
  ("Sam has 2 times 3 apples").

These exclusions are not permanent — Phase 1.2+ will lift them under
their own ADRs.

## Pattern registry

When tagging a case under `patterns`, draw from this list. Add new tags
only when authoring a case that uses a construction not yet covered;
update the parser's pattern table at the same time.

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

## How to author a new case (Codex contract)

For each case:

1. **Draft the natural-language problem** in the style of the seed cases.
   Use the patterns listed above. Stay within Phase 1.1 scope.
2. **Solve it by hand** to determine `expected_answer` and `expected_unit`.
3. **Walk the problem sentence by sentence**, emitting:
   - First introduction of an entity → add to `entities`.
   - "X has N <unit>" → `initial_state` entry.
   - Any state-mutating verb → `operations` entry. Choose the right `kind`
     from the registry. For `transfer`, set `target`.
   - The question sentence → `unknown` field.
4. **Set `patterns`** to the tags used.
5. **Set `notes`** to one sentence explaining the construction or any
   gotcha (anaphora resolution, sequence marker, etc.).
6. **Verify**: load the case via `graph_from_dict`. The constructor will
   raise `MathGraphError` on schema violations. Use:

```python
import json
from generate.math_problem_graph import graph_from_dict
case = json.loads(line)
graph = graph_from_dict(case["ground_truth_graph"])
# canonicalize: parser output is compared against graph.canonical_bytes()
```

7. **Re-solve the graph by hand** using the operation semantics:
   - `add`/`subtract` on the actor's quantity of that unit
   - `transfer` = subtract from actor + add to target (same unit)
   - `multiply`/`divide` on the actor's quantity (scalar operand)
   - For `Unknown.entity=null`: sum across every entity holding `unit`
   - For `Unknown.entity="X"`: look up X's final quantity of `unit`

   The result must equal `expected_answer`. If it doesn't, the graph is wrong.

## Determinism check

```bash
python3 -c "
import json
from generate.math_problem_graph import graph_from_dict
with open('evals/gsm8k_parser_dev/cases.jsonl') as f:
    for line in f:
        c = json.loads(line)
        g = graph_from_dict(c['ground_truth_graph'])
        print(c['id'], 'OK', g.canonical_bytes().hex()[:16])
"
```

Every case should print `OK` plus a deterministic 16-hex-char prefix.

## Authoring target

50 cases by case-id `gpd-050`. Distribution target:

- 30 single-entity cases (`gpd-001` … `gpd-030`)
- 12 two-entity transfer cases (`gpd-031` … `gpd-042`)
- 8 multi-entity sum/no-op cases (`gpd-043` … `gpd-050`)

Within each tranche, vary which `operation_*` pattern is used so the
parser is exercised across the registry.

The parser landing under ADR-0115 will be measured against this file.
Exit criterion: **parse correctness ≥ 0.90** (45 of 50 cases'
ground-truth graphs reproduce byte-equal from the parser's output).
