<!-- CANONICAL | docs/analysis/relational-grounding-extension-2026-06-04.md | 2026-06-04 | capability/grounding-extension | binary relations + multi-variable universal rules by finite propositional grounding, with the honest coverage ceilings | verified: held-out fuzz engine==oracle (0 mismatches), back-compat byte-identical, smoke green -->

# Binary-relation + multi-variable grounding extension

Extends the finite-entity grounding (`evals/deductive_logic/grounding.py`) from **unary
predicates / single-variable rules** to **binary relations + multi-variable universal
rules**, still by **finite propositional grounding** into the regime the ROBDD entailment
operator and the independent truth-table oracle both decide. `wrong == 0` stays structural.
This is the real capability step that makes a RuleTaker/ProofWriter-style mirror cover
anything beyond the trivial unary fragment — the prerequisite the runway doc's PR-3 needs.

## What landed

- **Arity 1–2.** A literal is legacy unary `{predicate, entity|var, polarity}` OR general
  `{predicate, args:[{entity|var: str}, ...], polarity}`. `atom_n` lowers
  `predicate(a, b)` → `predicate__a__b`; arity-1 is byte-identical to the old `atom`, so
  every pre-existing unary problem lowers unchanged (proven).
- **Multi-variable universal rules**, grounded by enumerating every assignment of the
  rule's variables to named entities (`n^k`). The canonical transitive rule
  `∀x,y,z. bigger(x,y) ∧ bigger(y,z) → bigger(x,z)` now grounds and decides correctly.
- **Range-restriction (safety).** A rule whose head contains a variable unbound in the
  body (`p(x) → q(y)`) refuses (`unsafe_rule`) — it grounds soundly but is outside the
  clean regime real benchmarks use. Narrowness is the firewall.
- **Refusals** (typed): arity ≥ 3 / functions (`unsupported_predicate_arity`); explicit
  quantifiers (`unsupported_quantifier`); a variable-free rule (`unsupported_quantifier`);
  and the bounds below (`grounding_bound_exceeded`).

## The honest ceilings (these are real limits, not hidden)

1. **The binding constraint is the independent GOLD, not the grammar.** The INV-25 gold is
   a truth-table oracle — **O(2^atoms)**. Binary relations explode the atom count
   (`n` entities → up to `n²` atoms per binary predicate). So the grounding refuses above
   `MAX_GROUND_ATOMS = 20` (2²⁰ ≈ 1e6 assignments, decidable). **Consequence: binary
   problems cap at ~4 entities per predicate.** That is the true coverage ceiling — bigger
   problems refuse. (A future lift would need a *second* sub-enumeration oracle that is
   still genuinely independent of the ROBDD — non-trivial; not done.)
2. **Open-world only.** The grounding decides classical (monotone, open-world) entailment:
   underivable ⇒ `unknown`, not `false`. RuleTaker / ProofWriter's main splits are
   **closed-world with negation-as-failure** (underivable ⇒ False). Any future benchmark
   adapter **must refuse CWA/NAF cases** — mapping a CWA "False" to "refuted" would be a
   `wrong=0` breach. Only the **OWA** split is honestly mirrorable.
3. **Function-free, arity ≤ 2.** Ternary+ relations and functions refuse.

## Validation (held-out, not hand-authored)

- **Differential fuzz:** 400 randomly-generated binary problems (binary facts + a
  transitive rule), gold computed by the **independent truth-table oracle**, decided by
  the **ROBDD engine** — **0 engine/oracle mismatches** on every in-regime case. This is
  the anti-overfit check: the gold is oracle-derived on data the grammar was not authored
  against, so it is a real `wrong=0` signal, not a 15-case hand-authored echo.
- **Back-compat:** the unary path lowers byte-identically; the committed finite-entity
  gold is still reproduced by the independent oracle (INV-25b green); deductive lane
  `wrong=0` unchanged; smoke green.

## What this unblocks / what it does NOT claim

- Unblocks: a ProofWriter-**OWA**, function-free, ≤2-arity, small-entity adapter (the
  runway's PR-3) that can cover *relational/transitive* cases, not just the unary fragment.
- Does **not** claim any benchmark number: the actual RuleTaker/ProofWriter data is **not
  in the repo**. A real number requires obtaining the dataset (license-checked) and is
  explicitly scoped to "the OWA function-free ≤2-arity small fragment," with everything
  else refused — never "ProofWriter accuracy."
