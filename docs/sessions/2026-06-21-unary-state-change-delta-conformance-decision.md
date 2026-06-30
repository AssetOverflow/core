# Post-#856 Unary-Delta Conformance Decision

**Status:** Accepted decision — Option B authorized
**Date:** 2026-06-21
**Scope:** `state_change.unary_delta`
**Depends on:** PR #855, PR #856, PR #857
**Decision type:** post-merge conformance decision and implementation authorization
**Accepted option:** Option B — authorize narrow correction PR

## 1. Purpose

This document records a precise post-merge conformance lookback following the implementation of the diagnostic `state_change.unary_delta` seam in PR #855 and its subsequent isolation hardening in PR #856. The purpose of this lookback is to identify and document divergences between the merged codebase and the controlling specification, authorization, and preflight documents.

PR #857 introduced this lookback as a proposed decision. This revision records the accepted decision: **Option B — authorize a narrow future correction PR to restore the original spec/preflight shape.**

Recording this accepted decision prevents residual taxonomy, SearchGate, ComputeBudgetPolicy, Workbench trace, or search work from building on top of unresolved architecture drift.

## 2. Current merged state

The diagnostic seam for `state_change.unary_delta` was introduced in PR #855 and hardened in PR #856. The current codebase successfully isolates this event type through:
- Cataloging the family under `state_change.unary_delta` in `generate/foundational_families.py`.
- Generating `ConstructionProposal` records with a static status of `"proposed"`.
- Creating a `BoundRelation` representing the unary delta (attaching action cue, delta quantity, changed object, and direction).
- Assessing the relation in `assess_unary_delta` to yield a `ContractAssessment`.
- Verifying extensive negative controls (such as transfers, containment, and comparisons) in `tests/test_unary_delta_proposal.py`.

However, the merged code deviates from the preflight design in key syntactic areas, such as the candidate organ naming, typed cue structures, quantity disposition boundaries, and proposal generation thresholds.

## 3. Controlling specification and preflight requirements

The design is governed by three controlling documents:
1. **Specification:** `docs/specs/foundational-families/unary-state-change-delta.md`
2. **Authorization:** `docs/sessions/unary-state-change-delta-authorization-2026-06-21.md`
3. **Preflight:** `docs/sessions/unary-state-change-delta-preflight-2026-06-21.md`

These documents specify that:
- The candidate organ name must be `"unary_delta_transition"`.
- A family-local, typed `GroundedUnaryDeltaCue` and a `ProblemFrame.unary_delta_cues` field must be implemented.
- The trigger condition of `QuantityKindDisposition` must remain strictly confined to `binding.quantity_entity` to preserve the isolation boundary established in PR #853.
- Recognition must be a closed lexical scan over exact cues (`gained`/`lost`), producing a proposal even if downstream quantity or object mentions are missing, leaving the incompleteness to refuse downstream during contract assessment.

## 4. Conformance matrix

| Area | Controlling requirement | Merged implementation | Conformance status | Notes |
|---|---|---|---|---|
| **Candidate organ name** | `candidate_organ = "unary_delta_transition"` | `candidate_organ = "unary_delta"` in `generate/construction_affordances.py` and `generate/problem_frame_contracts.py` | `divergent_requires_decision` | The merged codebase uses the shortened organ name. |
| **Cue representation** | Family-local typed `GroundedUnaryDeltaCue` class and `ProblemFrame.unary_delta_cues` field. | Stored as generic `BoundRole` slots in the relation instead of a dedicated typed cue record. | `divergent_requires_decision` | The typed cue record class and field were bypassed. |
| **QuantityKindDisposition boundary** | Do not widen the trigger of `QuantityKindDisposition` beyond the `binding.quantity_entity` proposal. | Modified `_quantity_kind_dispositions` in `generate/problem_frame_builder.py` to trigger from both `binding.quantity_entity` and `state_change.unary_delta` proposals. | `divergent_requires_decision` | Widened the trigger condition, encroaching on the PR #853 isolation boundary. |
| **Recognition strategy** | Closed lexical recognizer over cue inventory (`gained`/`lost`) that proposes even on missing quantity/object. | Uses `_UNARY_DELTA_RE` in `_unary_delta_proposals` in `generate/problem_frame_builder.py` which requires subject, cue, quantity, and object. Does not propose if any of these are missing. | `divergent_requires_decision` | Missing roles cause proposal omission (no proposal is generated) rather than assessment refusal. |
| **Proposal/assessment authority** | `ConstructionProposal` remains status `"proposed"`. `ContractAssessment` is the sole runnable authority. No serving/teaching path changes. | Status is strictly `"proposed"`. No serving, runtime, vault, recall, or teaching mutation paths were added. | `conformant` | Safety boundary of proposal-first structure is fully preserved. |

## 5. Safety baseline preserved by #855/#856

Despite the syntactic divergences, PR #855 and PR #856 successfully maintained the project's security and architecture safety baselines:
1. **No serving impact:** `diagnostic_only=True` and `serving_allowed=False` are enforced on the family registry and catalog entries.
2. **Proposal-first discipline:** Proposals carry no runnable authority. The status remains `"proposed"`.
3. **No authority leak:** No legacy math, semantic-state ledger, or derivation graph is imported. This is locked by a static AST import guard in `tests/test_unary_delta_proposal.py`.
4. **Strong test-hardened isolation:** PR #856 added comprehensive tests proving that the unary-delta path refuses or avoids proposing for transfers, containment movement, comparative phrasing, lists, passive voice, percent/rate context, and negation.

## 6. Divergences requiring decision

The project must reconcile the following points of unratified conformance drift:

1. **Organ naming:** The short name `"unary_delta"` diverges from `"unary_delta_transition"`.
2. **Missing GroundedUnaryDeltaCue:** The lack of a typed cue record deviates from the structural representation intended in the specs, leaving event attributes embedded within generic bound roles.
3. **QuantityKindDisposition trigger widening:** By allowing `state_change.unary_delta` proposals to trigger `QuantityKindDisposition` generation, the boundary established in PR #853 is no longer strictly isolated to `binding.quantity_entity` proposals.
4. **Regex-driven proposal gating:** Rather than proposing immediately upon detecting the cue word and letting downstream missing details fail-closed at assessment, proposal creation itself is gated on the full regex match. Consequently, sentences like `"Tom gained 3."` or `"Tom gained apples."` fail to generate a proposal, bypassing contract assessment instead of yielding a refused assessment.

## 7. Decision options

### Option A — Ratify merged implementation shape

**Meaning:**
The project explicitly accepts the merged representation:
- Shortened candidate organ name (`"unary_delta"`).
- Omission of the typed `GroundedUnaryDeltaCue` (relying on generic roles).
- The widened triggering boundary for `QuantityKindDisposition`.
- The regex-gated proposal logic that suppresses proposal emission for incomplete inputs.
- Relying on PR #856 tests as the effective guardrail.

**Consequences:**
- The spec and preflight documents must be updated in a future docs-only PR or ADR amendment to match the merged code.
- Residual taxonomy and downstream work will target the merged implementation.
- No code correction PR is required.

**Risks:**
- The original specifications become stale unless actively amended.
- Future agents may consult the older documents and construct conflicting code.
- Candidate organ naming remains less semantically precise.

### Option B — Authorize narrow correction PR

**Decision:** Accepted.

**Meaning:**
The project holds the original spec, authorization, and preflight documents as controlling. It authorizes a narrow, future implementation correction PR to align the code with the spec:
- Rename `candidate_organ` to `"unary_delta_transition"`.
- Implement `GroundedUnaryDeltaCue` and `ProblemFrame.unary_delta_cues`.
- Restore the strict `QuantityKindDisposition` boundary (triggering only on `binding.quantity_entity` proposals).
- Transition to a closed lexical cue recognizer that creates a proposal upon detecting `"gained"` or `"lost"` regardless of missing quantity/object details, shifting the completeness checks entirely to `assess_unary_delta`.

**Consequences:**
- Residual taxonomy and downstream integration wait until the correction PR lands.
- The correction PR must preserve all PR #856 isolation tests.
- No behavior widening is permitted.

**Risks:**
- Potential code churn after achieving a stable, green, and test-hardened state.
- Care must be taken to prevent the correction PR from drifting into a broader feature rewrite.

### Option C — Defer residual/search work until decision

**Meaning:**
The project explicitly records the unresolved drift and suspends all downstream work (e.g., residual taxonomy, SearchGate, ComputeBudgetPolicy, or Workbench traces) until a formal decision between Option A and Option B is ratified.

**Disposition:** Superseded by acceptance of Option B. The downstream freeze remains active until the Option B correction PR lands.

## 8. Accepted decision

Accepted: **Option B — Authorize narrow correction PR.**

**Reasoning:**
The controlling specification and preflight documents were explicit, and downstream structures like `ContractResidual` will lock these labels and types into a long-term contract. Reconciling the implementation to match the spec before establishing the contract is safer than ratifying the drift. Widening the `QuantityKindDisposition` trigger also represents unresolved boundary drift from the #853 isolation posture and should be resolved before residual contracts depend on it.

This document now serves as the implementation authorization for exactly one narrow conformance correction PR. That PR may correct the four divergences named above and must preserve the #855/#856 safety baseline.

## 9. Required follow-up

Because Option B is accepted:

1. Open a narrow correction PR titled `fix(kernel): align unary-delta implementation with conformance decision`.
2. Restore the authorized candidate organ, typed cue, quantity-kind boundary, and closed lexical recognizer.
3. Preserve every #856 isolation test and authority-boundary guarantee.
4. Do not widen behavior beyond the original spec/preflight.
5. Do not proceed to residual taxonomy or downstream search/Workbench work until the correction PR lands.

## 10. Residual/SearchGate/Workbench freeze

Until the Option B conformance correction PR merges:
- Do not implement `ContractResidual`.
- Do not implement SearchGate.
- Do not implement ComputeBudgetPolicy.
- Do not implement GeometricSearchRun.
- Do not implement Workbench `ProblemFrame` / `ContractAssessment` traces.
- Do not define residual taxonomy over unary-delta labels.
- Do not treat the current implementation's drift as tacit ratification.

This is a sequencing guard to ensure architectural consistency.

## 11. Non-goals

This accepted decision does not include or permit:
- Modifying any source code files under `generate/` or elsewhere in this docs PR.
- Modifying or adding unit tests under `tests/` in this docs PR.
- Correcting any implementation drift within this docs PR.
- Implementing `ContractResidual` or defining residual taxonomy.
- Implementing SearchGate, ComputeBudgetPolicy, or GeometricSearchRun.
- Modifying or touching the Workbench UI or server logic.
- Altering serving paths or allowing serving for this family.
- Mutating teaching, proposal, evaluation, or report artifacts.
- Changing any package, policy, identity, recall, vault, field, or algebra files.

## 12. Validation

Validation of this docs-only PR consists of verifying workspace integrity:
- Verify that no code or test files are modified:
  ```bash
  git diff --name-only origin/main...HEAD
  ```
- Ensure HEAD matches origin/main except for this document.
- Verify the git workspace contains no uncommitted files:
  ```bash
  git status --short
  ```
