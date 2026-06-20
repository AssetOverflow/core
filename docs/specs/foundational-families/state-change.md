# Foundational Family Specification: State Change

Status: Proposed (gating specification)
Related ADRs: ADR-0223, ADR-0224
Domains: Mathematics (Arithmetic/Proportional), Physical Science, Life Science, Reading Comprehension, Procedural Reasoning
Summary:
This family represents the transition of an entity or system from an initial state to a final state, triggered by an event, action, or process. It captures the initial value/condition, the mechanism or scale of change, and the resulting final value/condition. State change reasoning is vital for modeling deltas, proportional scaling, temporal sequences, and physical/biological processes.

Surface / chunk patterns:
- `<verb-change> to <value>` (e.g., "decreased to 3/4", "heated to 100 degrees")
- `<verb-change> by <value>` (e.g., "increased by 5", "grew by 2 inches")
- "originally <value>, now <value>" (e.g., "was 12, now is 8")
- "after <event>, <actor> has <value>" (e.g., "after giving away 3, she had 5")

Semantic neighborhood:
- `possession_change`
- `proportional_scaling`
- `temperature_transition`
- `growth_stage`
- `procedural_step`

Construction signatures:
```text
Signature: state_change
Organ: state_change_adapter
Relation Type: state_change
```

Required roles:
- `entity`: The actor, object, or system undergoing the change.
- `initial_state`: The condition or quantity before the transition event.
- `transition_event`: The trigger or action causing the transition (e.g., "gives", "heats", "loses").
- `final_state`: The condition or quantity after the transition event.

Optional roles:
- `scale`: The ratio or scale factor of change (e.g., "3/4 of").
- `delta`: The absolute difference/change quantity (e.g., "by 5").

Hazards / confusers:
- `PF-BD-004 positional_binding`: Selecting the wrong quantity as the base/initial state due to sentence ordering (e.g., "Shelly now has 8 apples. She started with some and lost 2" -> incorrectly binding 8 as initial).
- `PF-TG-004 target_direction_unknown`: Confusing a request for the final value with a request for the difference/delta, or vice versa (e.g., "How much did it decrease by?" vs "What is the new temperature?").
- `PF-TP-006 state_transition_open`: The transition lacks clear initial, delta, or final state constraints, leading to under-constrained mathematical systems.
- `PF-HZ-003 hazard_ignored_by_contract`: Failing to block on "decreased by" vs "decreased to", which completely changes the arithmetic operator and target mapping.

ProblemFrame / domain-frame representation:
```python
# Typed representation of state transition relations
from dataclasses import dataclass

@dataclass(frozen=True)
class RelationRole:
    role: str  # "entity" | "initial_state" | "final_state" | "delta" | "scale" | "transition"
    target_id: str  # Mentions ID of the bound GroundedMention

@dataclass(frozen=True)
class BoundRelation:
    relation_id: str
    relation_type: str  # "state_change" | "decrease_to_fraction"
    roles: tuple[RelationRole, ...]
    evidence_spans: tuple[SourceSpan, ...]
```

ContractAssessment readiness criteria:
A state change candidate reaches `RUNNABLE` status if and only if:
1. The `entity` undergoing the transition is bound and verified to have entity continuity across the event span (`PF-EN-004` resolved).
2. The transition direction (increase vs decrease) is explicitly resolved from the trigger verb/surface (`PF-BD-007` resolved).
3. The target question asks for a mathematically valid and closed variable (e.g., if initial and final are known, target must be delta; if initial and delta are known, target must be final) (`PF-TG-004` resolved).
4. No unresolved directional ambiguity (such as "decreased by" vs "decreased to") is present in the active hazard categories (`PF-HZ-003` resolved).

Verification style:
- State equation validation: `final_state = initial_state +/- delta` or `final_state = scale * initial_state`.
- Adverse confuser checks: Changing the trigger from "decreased to 3/4" to "decreased by 3/4" must fail the contract unless the delta role is re-bound and re-verified.

Refusal conditions:
- Missing event order or temporal ambiguity (e.g., "she lost 3 apples and bought 5, ending with 8" without temporal indicators to order the events).
- Incomplete/open state transitions where neither initial, delta, nor final values can be grounded to spans.

Cross-domain evidence:
1. **Physical Science (Temperature Change):**
   - *Example:* "Water originally at 20 degrees Celsius is heated to 80 degrees Celsius."
   - *Bindings:*
     ```python
     BoundRelation(
         relation_id="rel-0001",
         relation_type="state_change",
         roles=(
             RelationRole(role="entity", target_id="m-water"),
             RelationRole(role="initial_state", target_id="m-temp-init"),
             RelationRole(role="transition", target_id="m-heated"),
             RelationRole(role="final_state", target_id="m-temp-final")
         ),
         evidence_spans=(...)
     )
     ```
2. **Life Science (Growth Change):**
   - *Example:* "The plant grew from 5 inches tall to 9 inches tall over the summer."
   - *Bindings:*
     ```python
     BoundRelation(
         relation_id="rel-0001",
         relation_type="state_change",
         roles=(
             RelationRole(role="entity", target_id="m-plant"),
             RelationRole(role="initial_state", target_id="m-height-init"),
             RelationRole(role="transition", target_id="m-grew"),
             RelationRole(role="final_state", target_id="m-height-final")
         ),
         evidence_spans=(...)
     )
     ```
3. **Reading Comprehension (Event Transition):**
   - *Example:* "Before the storm, the streets were dry. After the storm, the streets were flooded."
   - *Bindings:*
     ```python
     BoundRelation(
         relation_id="rel-0001",
         relation_type="state_change",
         roles=(
             RelationRole(role="entity", target_id="m-streets"),
             RelationRole(role="initial_state", target_id="m-dry"),
             RelationRole(role="transition", target_id="m-storm"),
             RelationRole(role="final_state", target_id="m-flooded")
         ),
         evidence_spans=(...)
     )
     ```
4. **Procedural Reasoning (Step Changes):**
   - *Example:* "Step 1: Set X to 10. Step 2: Decrement X by 2."
   - *Bindings:*
     ```python
     BoundRelation(
         relation_id="rel-0002",
         relation_type="state_change",
         roles=(
             RelationRole(role="entity", target_id="m-x"),
             RelationRole(role="initial_state", target_id="m-x-val1"),
             RelationRole(role="transition", target_id="m-decrement"),
             RelationRole(role="delta", target_id="m-two")
         ),
         evidence_spans=(...)
     )
     ```
5. **Arithmetic / GSM-style Proportional Decrease Pressure Lane:**
   - *Example:* "A group of 84 students decreases to 3/4 of its size."
   - *Bindings:*
     ```python
     BoundRelation(
         relation_id="rel-0001",
         relation_type="decrease_to_fraction",
         roles=(
             RelationRole(role="entity", target_id="m-students"),
             RelationRole(role="initial_state", target_id="m-init-count"),
             RelationRole(role="transition", target_id="m-decreases"),
             RelationRole(role="scale", target_id="m-fraction")
         ),
         evidence_spans=(...)
     )
     ```

Serving status: Not implemented / not serving.
Current state features assessment-backed proposal traces for selected math constructions (`proportional_change.decrease_to_fraction` in diagnostics). General state-change adapter and non-math domain frames are absent from live serving pathways.

Implementation authorization:
**NOT AUTHORIZED.** This is a constitutional specification file only. Implementation requires a separate, evidence-backed implementation plan and PR.
