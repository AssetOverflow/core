# ASK Serving Integration Scoping — ask_serving_enabled, QUESTION_NEEDED, and Carve-Out Retirement

## 1. Current State

Currently, the ASK capability exists strictly off-serving.

- **Residue Capture (Q1-B):** The `core/epistemic_disclosure/limitation.py` module captures `LimitationAssessment` with typed ASK residue including `MissingSlot` and `grounded_terms`. Specifically, `missing_total_count` and `missing_weighted_total` are classified as ask-oriented inside the disclosure layer.
- **Carve-Out Safety (Q1-B):** The transitional carve-out constant `Q1B_ASK_CARVE_OUT` is defined in `core/epistemic_disclosure/limitation.py`. The registry in `core/comprehension_attempt/failure_family.py` preserves `proposal_allowed=True` for these carve-out families. This guarantees that the proposal-pile signal remains active and uninterrupted until served ASK is fully wired and verified.
- **Grounded Rendering (Q1-C):** The `core/epistemic_questions/render.py` module safely renders `EpistemicQuestion` structures. It enforces structural rendering, ensuring no ungrounded problem-entity names or internal `snake_case` tokens escape to the user. Multi-slot, unmapped, or unsafe cases fall back to `question_unrenderable`.
- **Off-serving Delivery (Q1-D):** The delivery infrastructure in `core/epistemic_questions/delivery.py` defines `DeliveredQuestion` and ships the `Terminal.QUESTION_NEEDED` tenant. The resulting off-serving artifacts are written directly to the `teaching/questions/` sink. No served/user-facing surfaces are exposed.
- **Default-Dark Gate (Helper):** The helper function `ask_serving_enabled` is implemented in `core/epistemic_questions/serving_gate.py`. It operates in a fail-closed, default-dark manner. If the config field `ask_serving_enabled` is absent, it returns `False`. An explicit, truthy configuration is required to allow served ASK.
- **Integration gaps:** Currently, `generate/contemplation/pass_manager.py` does not emit served ASK, `chat/runtime.py` does not expose ASK, and the `Q1B_ASK_CARVE_OUT` remains active (unretired).

## 2. Non-Negotiable Boundary

Before ASK can be delivered to any user-facing surface, the following boundaries must be strictly enforced:

- **Strict Gate Guard:** No served question may be shown without an explicit, active `ask_serving_enabled` configuration check.
- **Fail-Closed Default:** The `ask_serving_enabled` helper must default to `False`. A missing or `None` config attribute must evaluate to `False`.
- **Prose Encapsulation:** The serving layer must not construct or mutate question prose directly. It may only consume pre-rendered `EpistemicQuestion` / `DeliveredQuestion` structures produced by Q1-C/Q1-D.
- **No Contentless Delivery:** An unrenderable ASK must never be promoted to `QUESTION_NEEDED`. Contentless `QUESTION_NEEDED` outcomes are strictly forbidden.
- **Carve-Out Preservation:** The `Q1B_ASK_CARVE_OUT` must remain active and unchanged until served ASK is fully verified. No proposal signal may be lost before a served `QUESTION_NEEDED` is verified live.
- **Sink Distinction:** The `question_only` (teaching/questions) sink must remain logically and physically distinct from the `proposal_only` (teaching/proposals) sink.
- **Zero Impact on Claims:** No benchmark, `CLAIMS.md`, or performance metrics may be modified by this scoping documentation.

## 3. Proposed Served Gate: ask_serving_enabled

The serving gate helper exists under `core/epistemic_questions/serving_gate.py`. This document scoping defines how future served-surface code must interact with the gate:

- **Helper Invariant:** Future code in the served-surface layer (e.g., `chat/runtime.py`) must verify `ask_serving_enabled(config)` before delivering any `QUESTION_NEEDED` response to a user.
- **Off-Serving Isolation:** The gate controls served (user-visible) output only. It must not disable or interfere with off-serving artifacts written to the `teaching/questions/` directory.

### Serving Gate Policy

| Config State | ask_serving_enabled(...) | Served ASK Allowed? |
| --- | --- | --- |
| Missing field | `False` | No |
| `None` / Default config | `False` | No |
| Explicit `False` | `False` | No |
| Explicit `True` | `True` | Only if rendering and delivery obligations pass |

## 4. pass_manager Integration Boundary

This section defines the future integration interface for `generate/contemplation/pass_manager.py`. This is scoping only; no execution is performed here.

1. **Evaluation:** The refusal/comprehension flow yields a `ComprehensionAttempt`.
2. **Assessment:** A `LimitationAssessment` is derived from the attempt.
3. **Resolution Action:** If `resolution_action == "ask_question"`:
   - The pipeline invokes `deliver_ask(assessment)`.
   - `deliver_ask` calls `render_question` exactly once.
   - If the question is renderable, the final `DeliveryOutcome` terminal becomes `QUESTION_NEEDED`.
   - If the question is unrenderable, the outcome falls back to the standing disposition (e.g., proposal or refusal).
4. **Gate Enforced downstream:** `generate/contemplation/pass_manager.py` may produce/record ASK delivery outcomes later, but user-visible exposure remains gated downstream by `ask_serving_enabled` (e.g., in `chat/runtime.py`).

- **Constraints:**
  - `pass_manager` must not contain prose templates or formatting rules.
  - `pass_manager` must not construct `DeliveredQuestion` manually (it must delegate to `deliver_ask`).
  - `pass_manager` must never bypass `deliver_ask`.
  - `pass_manager` must never emit a contentless `QUESTION_NEEDED`.

## 5. Served Behavior Matrix

| Assessment / Rendering | Gate Disabled | Gate Enabled |
| --- | --- | --- |
| Renderable `ask_question` | No served ASK; existing refusal/proposal behavior preserved | Served `QUESTION_NEEDED` is allowed |
| Unrenderable `ask_question` | Standing fallback; no `QUESTION_NEEDED` | Standing fallback; no `QUESTION_NEEDED` |
| Non-ASK limitation | Unaffected | Unaffected |
| `missing_total_count` / `missing_weighted_total` (carve-out) | Proposal signal preserved | Served ASK only after carve-out retirement proof |
| Multi-slot ASK | Unrenderable fallback | Unrenderable fallback |

*Note: Gate enabled is a necessary but not sufficient condition for serving. The renderable checks and delivery invariants must also pass.*

## 6. Q1B_ASK_CARVE_OUT Retirement Conditions

The transitional carve-out constant `Q1B_ASK_CARVE_OUT` can only be retired and removed from `core/epistemic_disclosure/limitation.py` when the following milestones are met and verified:

1. The `ask_serving_enabled` helper is tested and confirmed default-dark.
2. The `pass_manager.py` ASK integration is fully implemented behind the gate.
3. Served `QUESTION_NEEDED` terminal behavior is successfully tested using renderable `EpistemicQuestion` instances.
4. Unrenderable ASK paths are verified to fall back correctly, never emitting `QUESTION_NEEDED`.
5. Carve-out keys `missing_total_count` and `missing_weighted_total` are proven to yield safe renderable questions (or safe standing fallbacks).
6. A dedicated no-question/no-proposal dead-zone validation test is introduced and passes.
7. The registry in `core/comprehension_attempt/failure_family.py` flips `proposal_allowed=False` for the carve-out families without dropping signal.
8. The `teaching/questions/` (`question_only`) sink remains physically distinct from the `teaching/proposals/` (`proposal_only`) sink.
9. Smoke, contemplation, proposal, and disclosure test suites remain fully green.

*Until all 9 conditions are met, the registry's `proposal_allowed=True` setting for these families must remain.*

## 7. No-Dead-Zone Proof Obligation

### The Dead-Zone Hazard
If `proposal_allowed` is flipped to `False` on a failure family before ASK serving is enabled/renderable, an input falling into that family would yield no proposal signal AND no served question. This results in a silent loss of capability (a dead zone), violating the `wrong=0` refusal-first discipline.

### Required Proof Before Retirement
Before the carve-out is retired, tests must prove that for each carve-out family:
- If `proposal_allowed` is removed, either a served `QUESTION_NEEDED` is emitted safely, or the standing fallback preserves an admissible signal.
- The test suite must assert failure if an evaluation result yields neither a proposal nor a valid served question.

### Suggested Test Names
- `test_ask_serving_disabled_preserves_existing_proposal_signal`
- `test_carveout_retirement_has_no_question_no_proposal_dead_zone`
- `test_unrenderable_ask_never_emits_question_needed`
- `test_pass_manager_uses_deliver_ask_not_direct_rendering`
- `test_question_only_not_proposal_only`

## 8. Required Future Tests Before Wiring

The implementation PR must include tests asserting the following behaviors:

- **Gate Default:** `ask_serving_enabled` defaults to `False`.
- **Config Completeness:** A missing config field evaluates to `False`.
- **Opt-in Activation:** An explicit `True` configuration is required to allow served ASK.
- **Gate Override:** If the gate is disabled, no served ASK is emitted even if `deliver_ask` produces a `QUESTION_NEEDED` outcome.
- **Rendering Obligation:** If the gate is enabled, the output still requires a renderable `EpistemicQuestion`.
- **Unrenderable Fallback:** Unrenderable ASK instances are never served.
- **Prose Isolation:** `pass_manager` does not construct prose templates or strings.
- **Delegated Delivery:** `pass_manager` delegates entirely to `deliver_ask` and does not call `render_question` directly.
- **No Empty Terminals:** No contentless `QUESTION_NEEDED` outcomes are permitted.
- **Sink Safety:** The `question_only` artifact is written to the correct, distinct location.
- **Carve-out Lock:** `Q1B_ASK_CARVE_OUT` is preserved until both the gate and the dead-zone proofs are active.
- **Registry Guard:** Flipped registries are blocked until all retirement conditions are met.

## 9. Non-Claims

This scoping document establishes architectural boundaries only:

- **No Implementation:** It does not implement served ASK.
- **No Wiring:** It does not wire `generate/contemplation/pass_manager.py` or `chat/runtime.py`.
- **No Retirement:** It does not retire `Q1B_ASK_CARVE_OUT` or flip any registry `proposal_allowed` flags.
- **No Metric Changes:** It does not alter GSM8K benchmark claims or refusal behaviors.
- **No General Intelligence:** It does not make ASK generally intelligent; it simply bounds the served-surface gate.

## 10. Recommended Next Slice

To safely approach the implementation, the next sequential slices are recommended:

### Slice 1: Configuration Definition (No Wiring)
- Add a concrete configuration field `RuntimeConfig.ask_serving_enabled: bool = False` (if not already present).
- Ensure the helper `ask_serving_enabled(...)` references this configuration.
- Write configuration tests verifying the default and override values.
- Do not wire `pass_manager` or modify runtime loops.

### Slice 2: pass_manager Integration
- Wire `pass_manager` to call `deliver_ask` without constructing prose; any user-visible ASK exposure remains behind `ask_serving_enabled`; preserve `Q1B_ASK_CARVE_OUT`.
