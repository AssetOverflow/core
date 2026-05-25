# ADR-0152 — Learning-Arc Demo (`core demo learning-arc`)

**Status**: Accepted  
**Implements**: W-019  
**Depends on**: ADR-0150 (W-018 checkpoint contemplation), ADR-0151 (W-017 auto-proposal)

## Context

ADR-0055..0057 ships `core demo learning-loop`, which demonstrates the full cold-turn
→ discovery → operator-authored proposal → accept → grounded surface arc. In that
demo the operator supplies the connective, object, and evidence reference for the
proposed chain.

W-018 and W-017 together enable a new capability: the engine enriches discovery
candidates through autonomous contemplation at checkpoint and can generate proposal
structures without operator-crafted connective or object.

A new demo is needed to make this distinction observable and falsifiable.

## Decision

`core demo learning-arc` (`evals/learning_arc/run_demo.py`) scripts five scenes:

1. **S1 — Cold session**: `ChatRuntime(auto_contemplate=True, engine_state_path=tmpdir)`
   turns with an ungrounded prompt. Checkpoint enriches the emitted candidate via
   `contemplate()` and persists to `engine_state/discovery_candidates.jsonl`.

2. **S2 — Checkpoint enrichment**: Read the persisted candidate. Assert it carries
   `polarity`, `claim_domain`, and `sub_questions` populated by `contemplate()`.
   Assert the engine's `_decompose()` enumerated `(narrative, cause, reveals, meaning)`
   as a candidate chain from existing corpus shapes.

3. **S3 — Engine-authored proposal**: Build the full chain candidate using the
   engine-derived connective (`reveals`) and object (`meaning`) from `_decompose()`
   output. Add the corpus evidence reference (`cause_creation_reveals_meaning`) that
   the engine found as the shape template. `propose_from_candidate` with
   `source.kind="contemplation"`. Replay gate runs.

4. **S4 — Operator ratifies**: `accept_proposal` against a transient corpus. Active
   corpus is byte-identical before and after. Provenance: `adr-0057:discovery_promoted`.

5. **S5 — Session 2 grounded**: Same prompt against transient corpus →
   `grounding_source == "teaching"`, surface contains subject / connective / object.

## The distinction from learning-loop

| | learning-loop | learning-arc |
|---|---|---|
| Connective source | operator | engine (_decompose) |
| Object source | operator | engine (_decompose) |
| Evidence ref | operator | engine (corpus shape match) |
| `source.kind` | `"operator"` | `"contemplation"` |
| Operator action | author + ratify | ratify only |

## Trust boundary

- Writes only to `tempfile.mkdtemp()` directories (engine state, proposal log, transient corpus)
- Active corpus on disk is byte-identical before and after (`active_corpus_byte_identical` asserted)
- No LLM calls, no stochastic sampling, no approximation

## Falsifiable claims

`test_learning_arc_demo.py` (11 tests) pins:

- `learning_arc_closed` — before grounding_source ≠ "teaching", after == "teaching"
- `active_corpus_byte_identical` — no corpus mutation
- `engine_chain_found` in S2 — decomposition found `(narrative, cause, reveals, meaning)`
- `source_kind == "contemplation"` in S3
- `replay_equivalent` in S3 — replay gate passed, no regression
- `transient_lines_after == transient_lines_before + 1` in S4
- `before["surface"] != after["surface"]` — measurable change on same prompt
