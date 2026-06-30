# ADR-0205 — modus_ponens + the Disagreement Rule (proof_chain's first inference rule)

**Status:** Accepted (proof_chain phase 2.3 — the first inference rule + the wrong=0 mechanism)
**Date:** 2026-06-02
**Relates to:** ADR-0204 (proof-graph builder — the proof-step shape this rule consumes),
ADR-0201/0201.1/0202 (canonicalizer + contract), ADR-0203 (acyclicity guard),
`generate.derivation.verify.select_self_verified` (the arithmetic twin of the disagreement rule).
**Deferred to:** ADR-0206 (atom→carrier grounding).

---

## Context

proof_chain has a DAG substrate (ADR-0204) and a canonical form (ADR-0201). Phase
2.3 adds the first **inference rule** (`modus_ponens`) and the **wrong=0 mechanism
for proofs** (the disagreement/uniqueness rule). GPT-5.5 authored an independent
adversarial corpus (`modus_ponens_cases.json`, 24 cases: 6 valid / 8 invalid / 10
disagreement) against the ADR-0202 grammar, with the proof-step shape left
`[PENDING ADR-0204 SHAPE]` and the disagreement cases `[CONFIRM WITH OPUS]` — the
contract-first handshake.

## Decision

### 1. The MP-rule contract (committed before the rule)

- **Proof-step shape** = the already-landed ADR-0204 `Proof`/`ProofNode`
  (`proof_from_premises` desugars premises→premise-nodes, conclusion→mp-node). The
  `[PENDING ADR-0204 SHAPE]` placeholders resolve to this; the rule also accepts a
  bare `(premises, conclusion)` for corpus cross-check.
- **Closed typed-reason set** (`generate/proof_chain/rules.py::MP_REASONS`):
  `unique_canonical_conclusion` (admit); `missing_implication`,
  `unestablished_antecedent`, `conclusion_mismatch`, `conclusion_disagreement` (refuse).

### 2. `evaluate_modus_ponens` — ROBDD-exact, bypassing unit-resolution

In `generate/proof_chain/rules.py` (the proof-layer dispatch, ADR-0205 Option B):
operates on proposition **formulas** via the canonicalizer; **never** calls
`check_admissibility` / `_resolve_dep_units` (proofs have no units — the named 2.2
constraint, satisfied by construction). An implication `A→B` fires iff `key(A)` is
an established premise key; the consequent `B` is recovered syntactically
(`logic_canonical.parse_top_implication`) because the ROBDD form does not preserve
which side is antecedent (`P→Q` and `¬P∨Q` share one diagram).

### 3. The disagreement / uniqueness rule (the wrong=0 mechanism)

The literal twin of `select_self_verified`: **pool ALL admissible single-step MP
derivations the premise set supports**, collect their canonical conclusion keys, and
admit iff they collapse to exactly one key equal to the declared conclusion;
≥2 distinct keys → refuse (`conclusion_disagreement`); one key ≠ declared →
`conclusion_mismatch`; no admissible derivation → `missing_implication` /
`unestablished_antecedent`.

**Pooling over the premise set — NOT filtering to the declared conclusion first —
is the soundness mechanism.** Filter-first would admit-by-assertion when the same
premises admit a different key (the `20/5 == 4` class one level up): e.g. a premise
set that MP-derives both an unrelated tautology and the declared atom, or both the
declared atom and a strictly stronger one. Collapse-vs-conflict is judged by **exact
canonical key**, never surface — equivalent paths (`P∧Q`/`Q∧P`, `Q→R`/`¬Q∨R`,
`Q`/`Q∧(R∨¬R)`) collapse and admit; subtly-different ones (`P∧Q`/`P∨Q`, `P→Q`/`Q→P`,
`Q`/`Q∧R`) refuse.

### 4. Reason-set consolidation (the reconciliation finding)

The mechanism makes one distinction per axis; the corpus's finer labels collapse onto
the closed set — *the same redundancy confirmed for the disagreement labels applies to
the invalid labels*:

- 6 disagreement refuse-labels (conflicting / contradictory / tautology_vs_substantive
  / distinct_atom / near_miss / stronger) → **`conclusion_disagreement`** (the rule
  knows only: keys agree or they don't).
- 4 antecedent-flavor labels (missing_antecedent / antecedent_mismatch /
  affirming_consequent / implication_direction_mismatch) → **`unestablished_antecedent`**
  (the rule knows only: the available implication's antecedent is or isn't an
  established premise; `affirming_consequent` and `implication_direction_mismatch` are
  the identical pattern `A→B, conclusion≡A, premise≡B` — no mechanical distinction).

This consolidation is conveyed back to GPT-5.5 for the corpus's committed reasons.

## Honesty boundary (load-bearing — exact scope stated)

Through phase 2.3, proof_chain is **sound over its declared atoms**, not grounded in
recognized input (grounding is 2.4). And the disagreement rule's guarantee has a
**precise scope**: it guarantees a unique conclusion among **single-step modus ponens
derivations over the given premises** — **NOT** "uniquely entailed" by all proof
strategies (a stronger, currently-false claim). This must never be read as
"uniquely entailed." Same discipline as propositional-not-FOL.

## Evidence (cross-checked, not asserted)

- **All 24 corpus cases agree on OUTCOME against the real rule** (6 admit / 8 refuse
  / 4 admit / 6 refuse) — no rule bug, no corpus outcome-misread. Reasons: 3 exact,
  21 consolidate onto the closed set as above.
- `tests/test_proof_chain_rules.py` — the 24 cases (transcribed, reproducible) + the
  pooling guards. **Mutation:** a filter-to-declared-conclusion-first variant makes
  MP-DISAGREE-007/010 wrongly admit → `test_pooling_*` fail. Pooling is load-bearing.
- **Drive-by fix (cleanup-as-you-find):** the merged ADR-0204 `ProofNode.__post_init__`
  was dedented to module level, so **all `ProofNode` validation was silently dead**
  (smoke skips the dedicated test file, so the merge missed it — the "smoke ≠ full
  suite" hazard). Re-indented; validation restored;
  `test_self_dependency_refused_at_proof_model` passes.
- Full binding-graph + admissibility surface green; smoke 67. Additive (no math path
  touched).

## Three deferrals — settled

1. **modus_ponens bypasses unit-resolution** — by construction (proof-layer dispatch).
2. **Conclusion typing** — the rule needs the declared conclusion's key + premise
   formulas, both reachable; `conclusion_symbol_id` suffices, **no `BoundUnknown`**.
3. **`semantic_role`** — proofs still not wired into serving; **stays `"unknown"`.**

## Deferred

- **2.4** — atom→ADR-0144 `EpistemicNode` grounding (ADR-0206). Until then, "sound
  over declared atoms," never "reasons over input."
- Multi-step proof composition and a proof *search* (the disagreement rule here is
  over a given premise set, single-step) — later, separately scoped.

## Governance Cross-Reference (ADR-0225)

This late-corpus ADR is governed by [ADR-0225](./ADR-0225-adr-corpus-hygiene.md):

- Safety boundaries: changes must preserve ADR-0027/0028/0029 identity and safety-pack boundaries; no identity, safety, or policy mutation is implied unless explicitly reviewed.
- Versor closure: runtime field paths must preserve `versor_condition(F) < 1e-6`; this ADR does not authorize hidden normalization or hot-path drift repair.
- Reconstruction-over-storage: evidence must remain reconstructive and content-addressed rather than duplicating opaque state.
- Replay-equivalence: serving, teaching, promotion, or checkpoint changes require a named deterministic replay / byte-equivalence gate.
- Mutation standing: any durable corpus, pack, policy, or epistemic-status mutation remains reviewed, proposal-only until accepted, or proof-carrying as applicable.
