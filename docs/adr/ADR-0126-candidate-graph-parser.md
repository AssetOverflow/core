# ADR-0126 — Candidate-Graph Parser with Round-Trip Verifier-Filter

**Status:** Proposed
**Date:** 2026-05-23
**Author:** CORE agents + reviewers
**Depends on:**
- ADR-0115 (parser substrate),
- ADR-0116 (deterministic solver),
- ADR-0117 (`SolutionTrace` verifier),
- ADR-0118 (stepped realizer),
- ADR-0119 (+ all 8 sub-phases — GSM8K-math lane substrate),
- ADR-0119.7 (sealed GSM8K test),
- ADR-0120 (expert promotion contract),
- ADR-0121 (math expert promotion DEFERRED with named blocker
  `correct_rate = 0/1319` on sealed holdout).
**Supersedes:** ADR-0123b (`feat/adr-0123b-upstream-shape-gaps`,
commit `8c4070e`, never opened as PR). Substrate of ADR-0122 /
ADR-0123 / ADR-0123a remains in main and is consumed by this ADR.

---

## Context

ADR-0121 deferred the `mathematics_logic` → `expert` promotion with
the named blocker `correct_rate = 0/1319 on sealed GSM8K holdout`
and proposed a parser-expansion arc of 4–8 construction classes.
Three ADRs of that arc landed (ADR-0122 rate / per-unit, ADR-0123
comparison-phrasing, ADR-0123a comparison-shape-expansion) and a
fourth was prepared (ADR-0123b upstream-shape-gaps). All four:

- preserved every invariant (`wrong == 0`, byte-equal trace,
  pack-binding, replay determinism),
- passed their author-drafted dev-set exit criteria,
- **measured 0/1319 sealed-holdout lift** (Gemini Tasks 6 and 8).

Two independent external assessments (Kimi K2.6, Grok 4.2) and an
internal review converged on the same diagnosis:

1. **The dev set is hermetically sealed from the real GSM8K
   distribution.** It was authored by the people who authored the
   parser, against the parser's grammar. Dev-set success is
   uncorrelated (in expectation, anti-correlated) with sealed-holdout
   lift.

2. **Per-axis vocabulary expansion is structurally optimistic.**
   Each sealed case lives in the *intersection* of grammar gaps
   (verb × number-word × question-shape × ellipsis × multi-step),
   not the union. If each gap has independent coverage `p`, joint
   pass rate is `p^k`. Adding one verb raises `p` infinitesimally;
   joint pass rate barely moves.

3. **The current parser fails hard at the first unmatched
   construction.** A single brittle regex (e.g., an ambiguous verb
   match that steals the slot from a correct one) refuses an entire
   problem with `ParseError`. This makes vocabulary expansion
   adversarial against itself — adding new patterns can *lose*
   coverage on already-passing problems.

The architectural error is the *topology* of failure, not the
*size* of vocabulary. Four zero-lift ADRs are the empirical
evidence that more grammar in the same shape will not move the
sealed-holdout score.

---

## Decision

Replace the **first-match-wins, single-graph, fail-hard** parser
topology with a **candidate-graph + verifier-filter** topology
that preserves every existing invariant while converting
compound-gap failure from multiplicative (`p^k`) to parallel
(`1 - (1-p)^k`).

### Pipeline change

```
OLD: surface → ONE graph → solve → verify(trace_replay)
NEW: surface → [graph_1, graph_2, … graph_n] → solve each
              → round-trip filter → admissibility filter → decision rule
```

### Per-sentence change

Each sentence emits `list[CandidateOperation]` (possibly empty)
instead of one `Operation` or `ParseError`. Multiple matching
patterns no longer race for a single slot; they all emit
candidates and the verifier filters wrong ones downstream.

Hard bound: `MAX_CANDIDATES_PER_SENTENCE = 4`. Exceeding raises
`ParseError` (preserves determinism cost ceiling).

### Graph assembly

Cartesian product of per-sentence candidate lists, enumerated
depth-first in canonical pattern-priority order
(most-specific-first). Hard bound: `MAX_TOTAL_BRANCHES = 64`.
Exceeding refuses the entire problem (preserves runtime ceiling).

### Round-trip filter (load-bearing new invariant)

A candidate operation is *round-trip admissible* iff
reconstructing the source sentence from its parsed slots produces
a string byte-equal to the original sentence under normalization
N (lowercase + collapse whitespace + strip terminal punctuation).

Formally, for source sentence `s` and candidate operation `op`:

```
admissible(op, s) ⟺ N(reconstruct(op)) == N(s)
```

This is the **wrong-answer firewall**. A regex that misreads
"gives" as `subtract` instead of `transfer` will reconstruct a
sentence that doesn't byte-equal the source; the candidate is
rejected before it can produce a wrong number.

### Decision rule (final emit)

For the set `A` of admissible candidate graphs:

| `|A|` | answer distribution | decision |
|-------|--------------------|----------|
| 0     | —                  | **refuse** (preserves `wrong == 0`) |
| 1     | —                  | **emit** the single answer |
| ≥2    | all identical      | **emit** the common answer |
| ≥2    | non-identical      | **refuse** (genuine ambiguity) |

### Invariant preservation

| Invariant | How preserved |
|-----------|---------------|
| `wrong == 0` | Round-trip filter rejects mis-parses; ambiguity refuses. |
| Trace determinism | Candidate enumeration canonical (lexical pattern key); branch order canonical (depth-first by sentence). |
| `trace_hash` byte-equality | Selected graph alone enters `SolutionTrace`; non-selected branches are not hashed. |
| Pack-binding | Candidate generators consume the same pack lemmas as today. |
| Replay equivalence | Replay re-runs candidate enumeration + filter; same input → same selected graph. |
| Adversarial `wrong == 0` | Adversarial suite gate runs unchanged; round-trip filter is *stricter* than today's gates. |

### New invariant added

**Round-trip admissibility:** any operation that emits in a final
`SolutionTrace` must satisfy `N(reconstruct(op)) == N(source_span)`
for the source span it claims to parse. This is a stricter
contract than `trace_hash` byte-equality across runs (which only
guards determinism) — it guards against semantic mis-parse.

---

## Exit criterion

**Inner-loop signal (new):** draw 50 cases from GSM8K *train*
split (deterministic seed, committed unsealed at
`evals/gsm8k_math/train_sample/v1/cases.jsonl`). Run candidate-graph
pipeline. The architecture is validated iff:

```
correct ≥ 10 / 50  (20% absolute)
wrong  == 0
```

This is the first non-synthetic gradient signal in the GSM8K
lane. If the architecture is structurally sound, ≥20% lift on a
random sample is achievable without any new vocabulary work — the
gain comes purely from converting fail-hard to filter-and-pick.

**Path-B trigger:** if 50-case train sample shows `correct < 10`
after the candidate-graph pipeline is integrated, the parser-by-rule
architecture (in any topology) is the wrong abstraction for GSM8K
coverage. ADR-0126 itself is deferred and the work pivots to
benchmark re-selection (see "Alternatives considered → Path B"
below).

**Sealed-holdout protocol unchanged:** if the train-sample gate
passes, the sealed holdout runs exactly once and the number is
frozen in ADR-0126-results. The sealed `.age` ciphertext is never
modified.

---

## Alternatives considered

### Path A.1 — More vocabulary (status-quo continuation)

Continue the ADR-0122/0123/0123a/0123b cadence: catalog refusal
modes, add verbs/numbers/patterns, ship per-axis ADRs.

**Rejected** because four consecutive ADRs in this shape produced
0/1319 lift. The compound-gap math (`p^k`) explains why; no
amount of `p` improvement at the rate we can produce ADRs moves
joint pass rate meaningfully.

### Path B — Benchmark re-selection

Demote GSM8K to a stress test we honestly refuse on; re-target
the math-expert promotion to a benchmark where exact-recall,
determinism, and provenance are the discriminators (formal-math
symbolic equivalence, CORE-native teaching-corpus eval, MATH
symbolic subset).

**Held as fallback** triggered by the Path-B condition above. Not
chosen first because it forecloses the GSM8K target without
having tried the architectural fix that the compound-gap diagnosis
actually implies.

### Path C — Learned (LLM-aided) parser

Replace the rule-based parser with an LLM-assisted candidate
generator.

**Rejected** as a contract violation. ADR-0114a and the
project-wide stance (CLAUDE.md "no opaque LLM fallbacks, no
stochastic sampling, no hidden normalization") forbid this. The
candidate-graph approach in this ADR is the deterministic
analogue: parallel hypotheses with a verifier filter, no
sampling, no learned scoring.

---

## Implementation plan

| Phase | Module | Description |
|-------|--------|-------------|
| P1 | `generate/math_roundtrip.py` (new) | Standalone `roundtrip_matches(op, source) -> bool`. Unit tests over every existing op kind. This is the load-bearing primitive; nothing else matters if it doesn't work. |
| P2 | `generate/math_parser.py` (refactor) | `_process_statement` / `_process_question` return `list[CandidateOperation]`. Verb tables widened permissively. |
| P3 | `generate/math_candidate_graph.py` (new) | Branch enumerator + filter + decision rule. |
| P4 | `evals/gsm8k_math/runner.py` (wire) | Replace single-graph call with candidate-graph call. Preserve all current passing cases. |
| P5 | `evals/gsm8k_math/train_sample/v1/cases.jsonl` (new) | 50-case deterministic train-split sample (unsealed). |
| P6 | `evals/gsm8k_math/train_sample_runner.py` (new) | Run candidate-graph on train sample; emit `correct_rate`, `wrong_count`. |

Regression gates (must remain green at every phase):

- `core test --suite smoke`
- `core test --suite math` (existing 507/507)
- `core test --suite algebra` (82/82)
- 150/150 public split
- 200/200 dev set
- adversarial suite (`wrong == 0`)

---

## PR checklist (when proposing for merge)

```
What capability did this add?
  → Candidate-graph parser topology + round-trip verifier-filter.
What invariant proves the field remains valid?
  → Round-trip admissibility (new); wrong == 0 (preserved);
    trace_hash byte-equality (preserved).
Which CLI suite/eval proves the lane?
  → smoke + math + algebra + 200/200 dev + train_sample_runner.
Did this avoid hidden normalization, stochastic fallback,
approximate recall, unreviewed mutation?
  → Yes. Candidate enumeration is deterministic + bounded.
    Round-trip filter is deterministic byte comparison.
    No learned scoring, no sampling.
If it touches user input, what trust boundary was enforced?
  → No new user-input surfaces. Round-trip reconstruction does
    not echo unvalidated user content into logs.
```
