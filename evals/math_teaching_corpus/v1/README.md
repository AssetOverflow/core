# Math Teaching Corpus Benchmark v1.B (ADR-0131.2.B)

The second of three benchmarks for the `mathematics_logic` expert promotion under ADR-0131. Tests whether the *teaching/replay loop itself* can carry math content end-to-end (propose → ratify → replay-equivalent) on a small math teaching corpus.

## Scope (v1.B, load-bearing enrichment)

- **Domain**: Mathematical logic (`axiom`, `theorem`, `lemma`, `proof`, `premise`, `conclusion`, `implication`, `equivalence`, `contradiction`, `negation`, `set`, `function`, `domain`, `range`, `identity`, `composition`).
- **Language Pack**: `en_mathematics_logic_v1` (ratified and compiled).
- **Intents**: `cause` and `verification` (cold-start teaching grounding whitelisted intents).
- **Connectives**: `requires`, `grounds`, `reveals`.
- **No GSM8K-style word problems.** This is not a parser-shape or symbolic-equivalence benchmark.

## Teaching Loop

The runner exercises the complete teaching proposals loop end-to-end for each math teaching chain:

```
proposed_chain -> DiscoveryCandidate -> propose_from_candidate -> TeachingChainProposal
                       |
                       v
         run_replay_equivalence (cognition public split)
                       |
                       v
            replay_equivalent == True? -> accept_proposal -> append to math corpus
```

Each chain starts as a candidate, is proposed to a transient proposal log, undergoes replay-equivalence validation against the public cognition split, and is ratified (accepted) into a transient math teaching corpus file.

## Dataset

`cases.jsonl` contains 40 hand-curated mathematical logic cases, split into three expected classes:

| Class | Expected Verdict | Case Count | Description |
|---|---|---|---|
| `replay_equivalent` | `replay_equivalent` | 30 | Valid mathematical logic chains citing honest lemma refs. |
| `not_equivalent` | `not_equivalent` | 5 | Chains rejected due to cycles, redundancy, or pack-residency violations. |
| `refused` | `refused` | 5 | Chains refused by the eligibility check due to empty fields, undetermined polarity, or missing evidence. |

Total: 40 cases.

## Exit criterion (per ADR-0131.2.B)

```
correct_rate == 1.0 (100.0%)
wrong        == 0
```

`wrong` is incremented if any case actual outcome disagrees with the expected class, or if it raises an unexpected error.

## Running the lane

```bash
python -m evals.math_teaching_corpus.v1.runner
# exits 0 if exit criterion passes, 1 otherwise
# writes report.json with counts + per-case status
```

## v1.B result (load-bearing baseline)

```
correct = 40 / 40   (100.0%)
wrong   =  0 / 40   (wrong == 0 invariant satisfied)
refused =  0 / 40   (no unexpected refusals)
exit:   PASSED
```

## Future expansion

- Multi-hop composed math teaching chains.
- Arithmetic operation and units teaching chains (using `en_arithmetic_v1` and `en_units_v1`).
- Multi-pack dependency teaching validation.
