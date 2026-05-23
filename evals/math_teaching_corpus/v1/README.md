# Math Teaching Corpus Benchmark v1 (ADR-0131.2)

The second of three benchmarks for the `mathematics_logic` expert promotion under ADR-0131. Tests whether the *teaching/replay loop itself* can carry math content end-to-end (propose → ratify → replay-equivalent) on a small math teaching corpus.

## Scope (v1, intentionally narrow)

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

`cases.jsonl` contains 30 hand-curated mathematical logic cases, mirroring the chains in `teaching/math_corpora/math_teaching_v1.jsonl`:

| Intent | Connective | Subject Count | Object Count | Example |
|---|---|---|---|---|
| cause | requires | 12 | 12 | `theorem requires proof` |
| cause | grounds | 9 | 9 | `proof grounds theorem` |
| cause | reveals | 1 | 1 | `contradiction reveals negation` |
| verification | requires | 3 | 3 | `theorem requires proof` |
| verification | grounds | 5 | 5 | `proof grounds theorem` |

Total: 30 cases. All expected to be `replay_equivalent`.

## Exit criterion (per ADR-0131 Benchmark 2)

```
correct_rate == 1.0 (100.0%)
wrong        == 0
```

`wrong` is incremented if a case fails to propose, fails the replay-equivalence gate, fails ratification, or raises an unexpected error.

## Running the lane

```bash
python -m evals.math_teaching_corpus.v1.runner
# exits 0 if exit criterion passes, 1 otherwise
# writes report.json with counts + per-case status
```

## v1 result (baseline at landing)

```
correct = 30 / 30   (100.0%)
wrong   =  0 / 30   (wrong == 0 invariant satisfied)
refused =  0 / 30   (no cases refused)
exit:   PASSED
```

## Future expansion (ADR-0131.2.B and beyond)

- Multi-hop composed math teaching chains.
- Arithmetic operation and units teaching chains (using `en_arithmetic_v1` and `en_units_v1`).
- Multi-pack dependency teaching validation.
