# Deductive entailment authority demo

A model-style proposer submits premises, a claim, and (possibly) a bogus
verdict, confidence, or proof.  CORE recomputes formal propositional
entailment through its pinned deductive substrate, independently
cross-checks the verdict with a code-disjoint oracle, and serves
`entailed` / `refuted` / `unknown` — or refuses.  The proposer's opinion
never touches the decision.

```text
the proposer proposes   — premises + claim + (possibly bogus) verdict / confidence / proof
the engine recomputes   — sound + complete ROBDD entailment (generate.proof_chain.entail)
the oracle re-decides   — independent brute-force truth-table procedure (evals.deductive_logic.oracle)
CORE serves             — entailed / refuted / unknown only when both procedures agree; refused otherwise
the trace proves        — replayable entailment trace + oracle verdict, folded into trace_hash
```

## The four outcomes

| outcome | meaning |
| --- | --- |
| `decided` / `entailed` | the claim holds in **every** model of the premises (`(⋀P) → Q` is a tautology) |
| `decided` / `refuted` | the claim **fails** in every model of the premises (`(⋀P) → ¬Q` is a tautology) |
| `decided` / `unknown` | the premises genuinely underdetermine the claim — true in some models, false in others |
| `refused` / `null` | inconsistent premises (no vacuous entailment from a contradiction), out-of-regime or malformed input, or an engine/oracle disagreement (defensive) |

`refused` is a status, never a decision: refusal serves no entailment verdict.

## Committed scenarios

| scenario | what it proves | status / decision | reason |
| --- | --- | --- | --- |
| `entailed-modus-ponens` | a valid multi-step implication is recomputed and served | `decided` / `entailed` | `tautological_implication` |
| `refuted-negation` | the proposer says "entailed"; CORE **proves the opposite** | `decided` / `refuted` | `tautological_refutation` |
| `unknown-non-sequitur` | affirming the consequent is named as underdetermined, not guessed | `decided` / `unknown` | `undetermined` |
| `refused-inconsistent-premises` | a contradiction entails everything classically — CORE declines to answer instead | `refused` / `null` | `inconsistent_premises` |
| `refused-out-of-regime-formula` | quantified/predicate input refuses **by design**, before grammar errors | `refused` / `null` | `out_of_regime_or_malformed` |
| `proposer-wrong-unknown` | proposer asserts `entailed` with confidence 0.99 and a "proof"; CORE recomputes `unknown` | `decided` / `unknown` | `undetermined` |
| `proposer-wrong-refuted` | proposer asserts `entailed` with confidence 1.0, a forged trace hash, and a forged engine pin; CORE proves the **negation** | `decided` / `refuted` | `tautological_refutation` |

## Why this is hard to fake

* **The decision is recomputed, never echoed.**  The proposer block is
  confined to string fields by a closed schema; the authority reads only the
  field *names* (the `proposer_ignored_fields` ledger).  Byte-invariance
  tests prove the decision-bearing fields are identical with and without the
  garbage — in both directions.
* **Two independent procedures must agree.**  The engine is a hand-rolled
  ROBDD canonicalizer; the oracle is a separate recursive-descent parser plus
  brute-force truth-table enumeration that imports nothing from `generate`.
  Agreement between code-disjoint procedures is evidence; a shared-code
  "oracle" would only prove the engine agrees with itself.  A structural test
  pins the disjointness.
* **The engine identity is pinned.**  `engine_pin` in every artifact is
  `DEDUCTIVE_ENGINE_PIN`, which mirrors the `deductive_logic_v1` lane SHA in
  `scripts/verify_lane_shas.py` (drift between them fails the suite).  The
  same engine behind this demo holds the lane's committed record on its
  sealed holdout.
* **The artifact is replayable.**  `entailment_trace` embeds the canonical
  ROBDD keys for the premises, their conjunction, the claim, and both
  tautology checks; `trace_hash` is recomputed over the whole response body,
  so it folds the entailment trace and the oracle verdict.  Double-run
  byte-identity is asserted on every execution.

## Supported regime

Propositional logic only.  Atoms are **opaque Boolean labels** — the
semantic-looking names in the fixtures (`socrates_is_human`,
`breaker_open`) are for human legibility and carry no meaning to the
engine.  Connectives: `~` `&` `|` `->` `<->` (and word forms).  The demo
bounds payloads to 8 premises, 120 characters per formula, and 12 distinct
atoms — the atom budget honors the brute-force oracle's small-atom
contract, refusing instead of churning on adversarial input.  Quantified or
predicate input (`forall`, `exists`, `p(x)`) refuses with the engine's
typed regime reason.

## What this demo does and does not prove

```text
This demo proves deterministic formal entailment authority inside the supported
propositional regime.
It does not prove open-world natural-language understanding — atoms are opaque
Boolean labels; the fixture names are legibility sugar, not semantics.
It does not prove autonomous learning.
It does not perform proof-carrying promotion (that is demos/proof_carrying_promotion);
no store state exists here and no epistemic status changes.
It does not perform normative/safety clearance.
It does not execute tools or external side effects — no network, no model API,
no subprocess, no eval/exec, no clock, no randomness.
Oracle disagreement is test-only fault injection (a monkeypatched oracle), not a
committed scenario: inside the supported regime the two procedures agree, and a
committed "disagreement" fixture would be staged theater.
```

## Run it

```bash
python demos/deductive_entailment_authority/run_demo.py
```

Every fixture is executed twice and byte-compared against its committed
expected artifact under `expected/`.  Exit code 0 means all 7 scenarios
match.  `--write-expected` (explicit only) regenerates the artifacts;
custom `--out` directories are refused unless they resolve to a safe,
marked location.

Tests: `pytest -q tests/test_deductive_entailment_authority_demo.py`.
