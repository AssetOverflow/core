# evals/relational_inference/v1 — provenance

Independent gold for the one-hop relational-inference DETERMINE capability
(mastery-v2 Step 3). The gold `(predicate, subject, object)` triples are authored by
reading the relational predicate algebra (inverse/converse + symmetric)
**independently** of `generate/determine/determine.py` and
`generate/meaning_graph/relational.py` (INV-25 / INV-27) — the reader/determiner never
produced them.

## cases.jsonl — positive coverage (13)

Each case: told fact(s) → `determine(query)` should assert the entailed relation.

- **8 INVERSE/converse** — both directions of `less_than`/`greater_than`,
  `parent_of`/`child_of`, `left_of`/`right_of`, `before_event`/`after_event`.
- **5 SYMMETRIC** — `sibling_of`, `spouse_of`, `equal_to`, `distinct_from`,
  `adjacent_to`, each told one direction and queried the other.

A refusal here is a COVERAGE miss (counted `refused`), never a wrong.

## refusals.jsonl — confusers that MUST refuse (8)

Transitive (direct + through-inverse), asymmetric self-converse (`less_than`,
`parent_of`), cross-predicate (`sibling_of` ≠ `parent_of`, `greater_than` ≠
`equal_to`), object mismatch, and ungrounded. A `Determined` on any of these is a
wrong=0 breach — the lane test fails loudly.

## Resolved coverage gap (B3)

`overlaps_event` (symmetric, pack-declared `graph.edge.symmetric`) was previously
**excluded** from the positive gold: the relational reader required a copula
("X is _connective_ Y"), but `overlaps` is a finite verb. The closed finite-verb reader
surface (B3 — `<A> overlaps <B>` / `Does <A> overlap <B>?`, see
`generate/meaning_graph/relational.py::_read_finite_verb_clause`) now reads it, so a
stored overlap and its symmetric converse determine (proven in
`tests/test_relational_finite_verb.py`). The reader-surface coverage lives in
`evals/relational`; adding a symmetric `overlaps_event` case to THIS inference lane is
optional follow-up.
