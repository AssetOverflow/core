# relational_transitive / v1 — provenance

Hand-authored gold for the **transitive strict-order relational inference** DETERMINE
capability (mastery-v2 Step-3, Brief B2). Not derived from any corpus; each case is a
minimal, fully-grounded scenario authored to exercise one sound transitive closure (or one
unsound chain that must refuse).

## What this lane measures

`determine()` may close a **declared strict-order predicate** transitively over its OWN
realized edges: `p(a, b) ∧ p(b, c) ⊨ p(a, c)`. The admitted predicates are exactly the
four strict orders in `generate.meaning_graph.relational.TRANSITIVE_PREDICATES`:

- `less_than`, `greater_than` (numeric comparison)
- `before_event`, `after_event` (event precedence)

Closure is **same-predicate only** — it never composes inverse/symmetric/other-predicate
edges (that mixing stays one-hop), and it is open-world (asserts only `answer=True`, never
`answer=False`). Search-then-verify: BFS reachability proposes a chain; the sound+complete
`proof_chain` ROBDD verifies the transitive entailment before any assertion.

## Files

- `cases.jsonl` — positive coverage. Each `{facts, query, edges, query_edge}` must
  `determine()` to `answer=True`, `predicate/subject/object == query_edge`, `rule="transitive"`.
  This is the capability-index coverage (domain `comprehension_relational_transitive`,
  breadth 10→11).
- `refusals.jsonl` — the wrong=0 bite (Brief-C adversarial confusers). Each must REFUSE
  (`Undetermined`); a `Determined` means the transitive rule over-fired. Covers: non-transitive
  predicates (`sibling_of`, `parent_of`), non-admitted spatial predicates (`left_of`),
  mixed-predicate chains, reflexive cycles, disjoint chains, and inverse+transitive
  composition (out of scope for this slice).

## Independent oracle (INV-25 / INV-27)

`evals/relational_transitive/oracle.py::transitively_entails` computes the gold from each
case's **structured `edges`** by its OWN BFS over its OWN declaration of the transitive set
— importing NO engine module. The lane test cross-checks every case: positives must be
oracle-`True`, refusals oracle-`False`. The oracle scopes to the same capability (same-predicate
closure) by design; independence is in the separate authoring, so a divergence (the engine
over- or under-firing relative to the declared capability) surfaces as `wrong > 0` or a
broken cross-check.

## Determinism

No clock, no sampling, no LLM. The entity ids are the reader's canonical lowercased forms
(`Alice → alice`, `the box → box`). The fixture SHAs are pinned in
`tests/test_relational_transitive_lane.py` so the gold cannot drift silently.
