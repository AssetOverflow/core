# VERIFIED Serving Wiring Scoping — verified_serving_enabled and Gold-Free Independence

## 1. Current State

Currently, the VERIFIED verification pipeline exists off-serving only. No served [verified] surface exists, no serving-time config or gate exists, and no `verify.py` serving wiring is implemented.

The existing off-serving spine consists of:
- **P1-A**: Defines the contract in `core/epistemic_disclosure/verified_contract.py`. This contract includes:
  - `VerificationProof` (the data structure containing digests and lineages)
  - `VerificationObligation` (the strict checklist of obligations)
  - `evaluate_verification` (the pure-logic evaluation function enforcing the contract)
  - `disclosure_for_verification` (the single sanctioned route to transition a result to the verified state)
  - Defines the meaning of **VERIFIED**: two independent reads must converge on a single canonical structure. This requires:
    - Independent reads (`primary_reader_lineage` must not equal `independent_reader_lineage`)
    - Convergent canonical read digests (`primary_read_digest` must equal `independent_read_digest`)
    - `derivation_digest` present
    - `bound_slots_digest` present
    - `back_substitution_digest` present
    - `boundary_clear` is `True`
    - `contradiction_clear` is `True`
    - `limitation` is `None`
- **P1-B**: Adds an off-serving R2 verification producer in `evals/constraint_oracle/verified_producer.py`:
  - Extracts the primary read from the problem text via `read_constraint_problem(text)`.
  - Obtains the independent read from a hand-authored gold setup (`gold_setup`).
  - The gold answer itself never enters the verification process (the gold structure setup signature is matched, not the answer).
  - The producer is strictly for evaluation and runs off-serving only.
- **P1-C**: Introduces `bound_slots_digest` as a distinct, separable proof obligation to ensure the answer binds only to the stated slots (asked unknowns) and not phantom slots.
- **Serving Isolation**:
  - No served VERIFIED surface exists.
  - No `verified_serving_enabled` gate exists.
  - No `verify.py` serving integration exists.

## 2. Hard Non-Claim

The gold-setup-backed producer implemented in `evals/constraint_oracle/verified_producer.py` **cannot** be used for serving.

What P1-B proves:
- The VERIFIED contract logic is sound and functional.
- The verification producer can successfully assemble valid `VerificationProof` objects.
- Wrong reader structures diverge and correctly fail the independent verification check.
- The actual gold answer is not required to verify the canonical structural solve.

What P1-B does **NOT** prove:
- Serving-time independence (since gold setups do not exist for runtime user requests).
- Gold-free verification.
- User-visible served `[verified]` status.
- Benchmark or `CLAIMS.md` movement.
- AGI capabilities.

Any served `[verified]` status requires a gold-free independent read source at serving time.

## 3. Proposed Served Gate: verified_serving_enabled

To control the rollout of serving-time verification, a future configuration gate must be defined:

- The configuration field `verified_serving_enabled` does not exist yet.
- This document does not add or implement this configuration gate.
- The future gate must be default-false and fail-closed: if the config field is missing or malformed, it must evaluate to `False`.
- The gate must only control the served/user-visible `[verified]` surface.
- The gate must never affect off-serving evaluation proof generation or off-serving validation runs.
- The gate must strictly prohibit eval-gold-backed verification pipelines from touching serving code.
- Enabling the gate is necessary but not sufficient: even if `verified_serving_enabled` is `True`, a served VERIFIED verdict is only allowed if all contract proof obligations successfully pass.

| Config State | verified_serving_enabled | Served VERIFIED Allowed? |
| --- | --- | --- |
| missing field | False | No |
| default config | False | No |
| explicit false | False | No |
| explicit true | True | Only if gold-free proof obligations pass |

## 4. Gold-Free Independent Read Requirement

Before any served `[verified]` surface can exist, a serving proof must use a gold-free independent read source. 

A served proof must adhere to the following:
- Primary reader lineage is recorded.
- Independent reader lineage is recorded.
- The lineages must use distinct lineage identifiers.
- The primary read digest and independent read digest must converge.
- No gold setup is used.
- No gold answer is used.
- No benchmark fixture is used.
- No eval-lane imports are performed.
- Same reader twice (invoking the exact same reader lineage twice on the same text) is strictly rejected.
- Second solver over one read (running two solvers over the same read signature) is strictly rejected.

### Comparison

*   **Invalid (Pseudo-Independence):**
    ```text
    primary read ──> solver A
               └───> solver B ──> same answer ──> VERIFIED (INVALID)
    ```
*   **Valid (True Independence):**
    ```text
    primary read lineage ───────────> canonical digest C ──┐
                                                           ├──> convergent digests ──> VERIFIED (VALID)
    gold-free independent lineage ──> canonical digest C ──┘
    ```

The valid workflow requires:
- Primary read lineage converges to canonical digest `C`.
- Gold-free independent read lineage converges to canonical digest `C`.
- Derivation is computed from stated quantities.
- Bound slots are present.
- Back-substitution succeeds.
- No boundary has fired.
- No contradiction is present.
- No unresolved limitation exists.

The primary unsolved technical milestone is designing and implementing a gold-free independent reader/verifier source.

## 5. Serving Eligibility Criteria

For any response to be eligible for served `[verified]` status, all of the following conditions must be met:

- `source_problem_digest` is present.
- `primary_reader_lineage` is present.
- `independent_reader_lineage` is present.
- `primary_reader_lineage` and `independent_reader_lineage` are distinct.
- `primary_read_digest` is present.
- `independent_read_digest` is present.
- `primary_read_digest` and `independent_read_digest` are identical (converge).
- `derivation_digest` is present.
- `bound_slots_digest` is present.
- `back_substitution_digest` is present.
- `boundary_clear` is `True`.
- `contradiction_clear` is `True`.
- `limitation` is `None`.
- `evaluate_verification(...)` evaluates to `VerificationVerdict.VERIFIED`.
- `disclosure_for_verification(...)` is the only functional pathway used to transition the result to `(EpistemicState.VERIFIED, DisclosureClaim.VERIFIED)`.
- `verified_serving_enabled` is explicitly configured to `True`.
- The proof producer is gold-free and serving-eligible.

## 6. Holdout and Kill-Switch Gates

Before any served `[verified]` behavior can be wired to production, the serving-time verifier must clear a set of holdout and kill-switch gates:
- **Sealed Holdout Lane**: A dedicated evaluation run on a sealed, off-distribution holdout dataset.
- **Wrong=0 Requirement**: Zero incorrect answers are permitted for any result designated as VERIFIED.
- **Poison Fixtures**: Comprehensive verification tests using poison test cases to prove that:
  - Wrong-read structures diverge and fail.
  - Same-reader-twice reads fail verification.
  - Answer matches gold, but missing proof fails verification.
  - Absence of refusal alone without proof fails verification.
  - Missing `bound_slots_digest` fails verification.
  - Triggered boundaries fail verification.
  - Contradictions present fail verification.
  - Unresolved limitations fail verification.
- **Deterministic Replay Digest**: The verification trace must be replayable, yielding identical digests.
- **Kill-Switch**: Default off / fail-closed behavior must be validated.
- **Gate Disabled Test**: A test must verify that disabling `verified_serving_enabled` suppresses the served `[verified]` label even when a fully valid proof is present.
- **Gate Enabled Test**: A test must verify that enabling `verified_serving_enabled` still requires all proof obligations to pass before serving.

## 7. verify.py Boundary

The transition of the verification verdict to serving must enforce strict boundaries at the `verify.py` layer:
- `verify.py` may eventually consume a verified verdict from the contract.
- `verify.py` must not define or redefine the semantic meaning of VERIFIED.
- The formal meaning of VERIFIED remains exclusively defined in `core/epistemic_disclosure/verified_contract.py`.
- `verify.py` must never attempt to repair failed proofs.
- `verify.py` must not treat raw answer correctness (matching gold) as verification.
- `verify.py` must not import or use eval-lane gold datasets.
- No hot-path repair or silent corrections may occur in `verify.py`.

## 8. Served Behavior Matrix

| Proof / Gate State | Served Behavior |
| --- | --- |
| Valid off-serving eval-gold proof | Never served |
| Valid gold-free proof + gate disabled | No served `[verified]` |
| Valid gold-free proof + gate enabled | Served `[verified]` may be allowed |
| Wrong read divergence | No served `[verified]` |
| Same reader twice | No served `[verified]` |
| Answer matches gold but proof missing | No served `[verified]` |
| No refusal but no proof | No served `[verified]` |
| Boundary fired | No served `[verified]` |
| Contradiction present | No served `[verified]` |
| Unresolved limitation | No served `[verified]` |

## 9. Required Future Tests Before Wiring

The following test suite must be implemented and pass before any serving-time code can land:
- `verified_serving_enabled` defaults to `False`.
- A missing config field for `verified_serving_enabled` resolves to `False`.
- Explicit `True` configuration is required to serve `[verified]`.
- A disabled gate suppresses served `[verified]` even when a valid proof exists.
- An enabled gate still enforces and requires all proof obligations to pass.
- Eval-gold verification producers cannot be imported or accessed by serving modules (AST / dependency check).
- Eval-gold-backed proofs are rejected from being served.
- Same reader twice fails verification.
- Running a second solver over one reading fails verification.
- Answer-gold match without verification proof does not serve `[verified]`.
- Absence of refusal alone does not serve `[verified]`.
- Direct construction of `EpistemicState.VERIFIED` is blocked outside of `disclosure_for_verification`.
- Poison wrong-read inputs do not serve `[verified]`.
- Missing `bound_slots_digest` does not serve `[verified]`.
- Triggered boundary does not serve `[verified]`.
- Contradiction present does not serve `[verified]`.
- Unresolved limitation does not serve `[verified]`.
- `verify.py` consumes the contract outcome but does not define its rules.

## 10. Non-Claims

This scoping document establishes architectural boundaries only. 

- This document does not implement served VERIFIED.
- This document does not add the `verified_serving_enabled` config gate.
- This document does not wire `verify.py` to serving.
- This document does not move the evaluation producer (`verified_producer.py`) into the core serving layer.
- This document does not make gold-backed verification serving-safe.
- This document does not change benchmark metrics.
- This document does not update `CLAIMS.md`.
- This document does not solve the design of the gold-free independent reader.
- This document does not claim AGI progress.

## 11. Recommended Next Slices

The implementation of serving-time verification should proceed in isolated, review-gated slices:

### Slice 1: Configuration Gate
- Add default-dark `verified_serving_enabled` helper only.
- No runtime wiring, no `verify.py` wiring.
- Strict import checks preventing eval producer imports.
- Tests demonstrating default-dark behavior and config defaults.

### Slice 2: Gold-Free Independent Reader
- Design and prototype a gold-free independent reader/verifier source.
- Maintain off-serving isolation.
- Generate independent reader lineage and canonical digests.
- No integration with the served path.

### Slice 3: Verification Harness & Poison Fixtures
- Implement a holdout-gated verification harness.
- Integrate poison fixtures and test cases.
- Validate deterministic replay digests.
- Do not expose any served surface.

### Slice 4: verify.py Consumption
- Only after all prior slices are approved and pass tests, scope the consumption of the verified verdict within `verify.py`.
- No implementation without separate architectural review.
