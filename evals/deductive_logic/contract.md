<!-- CANONICAL | evals/deductive_logic/contract.md | 2026-06-04 | deductive-logic lane | what CORE's propositional entailment operator decides, and its honesty boundary | verified: holdout 500/500 correct wrong=0, 8000-case engine-vs-oracle fuzz 0 disagreements -->

# deductive-logic eval lane (ADR-0206)

## What it measures — and why it is honest

CORE's **deterministic propositional entailment operator**
(`generate.proof_chain.entail.evaluate_entailment`): given premise formulas and a
query formula, does the premise set **entail**, **refute**, or **leave undetermined**
the query — or is the input outside the decidable regime?

This is the inference operator `evals/symbolic_logic/gaps.md` asked for ("no operator
that takes A→B, B→C and returns A→C") and ADR-0205 deferred. It is built directly on
the ADR-0201 ROBDD canonicalizer, so it is **sound and complete** for propositional
logic, not single-step:

> premises ⊨ query  iff  `(⋀ premises) → query` is a tautology (an exact ROBDD check).

Unlike the GSM8K lanes, capability here can show **real correct numbers** because the
answer is *checkable*: this is the terrain CORE was built for (exact, verifiable,
deterministic), not the multi-step natural-language arithmetic GSM8K is engineered to
make stochastic.

## The numbers (2026-06-04)

| Set | n | correct | wrong | of which non-trivial (entailed + refuted) |
|---|---:|---:|---:|---:|
| dev | 200 | 200 | **0** | 74 |
| **holdout v1** | 500 | **500** | **0** | **227** (117 entailed + 110 refuted) |
| fuzz (fresh random, engine vs oracle) | 7,340 | 7,340 | **0** | 3,360 |

**100% correct with `wrong = 0`**, and the correct answers include hundreds of
non-trivial multi-hop entailments and refutations — not just `unknown` pass-throughs.

## Why the gold is trustworthy (the GSM8K lesson applied)

The gold is **not** computed by the engine under test. It comes from an *independent*
truth-table decision procedure (`oracle.py`): a separate parser + brute-force model
enumeration over all 2^k assignments, sharing **no code** with the ROBDD engine. Two
independently-coded sound procedures agreeing on **8,000** fresh random problems with
**zero disagreements** is real soundness evidence — exactly the property the GSM8K
composer could never establish (it could not tell its 2 right answers from its 87
wrong ones). A single engine/oracle disagreement fails the test suite.

## Honesty boundary (load-bearing — do not overclaim)

- **Propositional only.** Atoms are opaque Boolean variables. Quantified / predicate
  input (`forall x. P(x)`, `rough(x)`) is **out of regime** and refuses (typed,
  by design — ADR-0201.1), never guessed. A finite-entity problem *grounded* to
  per-(entity,predicate) atoms is propositional and in scope; an ungrounded
  first-order rule is not.
- **This is given formulas, not natural language.** The operator decides logic; it
  does not yet *read* English word-problems into logic. NL→formula grounding is a
  separate, later layer (and the place the GSM8K rake lives — kept out of scope here
  deliberately).
- **`wrong = 0` is the floor, not a bragging point.** It is structural (an exact
  tautology check refuses rather than approximates). The capability claim is the
  *coverage with* `wrong=0`: hundreds of correct non-trivial deductions on held-out
  data, independently verified.

## Outcomes (closed vocabulary)

| outcome | meaning |
|---|---|
| `entailed` | `(⋀P) → Q` is a tautology — Q holds in every model of the premises |
| `refuted` | `(⋀P) → ¬Q` is a tautology — Q fails in every model |
| `unknown` | neither — Q is true in some premise-models and false in others |
| `refused` | premises inconsistent (no model) **or** malformed / out-of-regime |

## Run

```bash
PYTHONPATH=. .venv/bin/python -m evals.deductive_logic.runner    # dev + holdout, exits 1 if wrong>0
PYTHONPATH=. .venv/bin/python -m evals.deductive_logic.generate  # regenerate committed cases (deterministic)
PYTHONPATH=. .venv/bin/python -m pytest tests/test_deductive_logic_entail.py -q
```

## Data layout

```
evals/deductive_logic/
  contract.md
  oracle.py            # independent truth-table gold (no shared code with the engine)
  generate.py          # deterministic, seeded; gold from oracle
  runner.py            # engine vs gold; correct/wrong/refused + class breakdown
  dev/cases.jsonl      # seed 20260604, 200 cases
  holdout/v1/cases.jsonl  # seed 70260604, 500 cases (disjoint)
```
