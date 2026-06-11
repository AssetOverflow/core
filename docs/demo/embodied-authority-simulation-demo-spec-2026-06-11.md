# CORE Embodied Authority Simulation Demo Spec
**Date: 2026-06-11**

---

## 1. Demo Overview
* **Demo Title:** CORE Embodied Authority Simulation Demo
* **Goal:** Show that a model-style proposer can suggest a physical-world transition, but CORE alone can authorize, refuse, ask, safe-stop, or invalidate it.

---

## 2. Hard Constraints
To prevent any misinterpretation of the scope of this project, the demo is bound by the following constraints:
* **No physical interaction:** No real robot, actuator, or physical side effect.
* **No control-stack integration:** No vehicle-control claim, production robotics claim, or production MCP claim.
* **No external dependencies:** No external network calls, model API calls, or runtime/chat/serving changes.
* **No schema pollution:** No modifications to existing CORE CLAIMS, metrics, telemetry schemas, runtime schemas, or lane-pins.
* **No deployable code:** No deployable robotics-control instructions or low-level actuator sequences are generated.
* **Simulation-only:** Uses local simulation fixtures and produces deterministic, local artifacts.
* **Proposer isolation:** The schema strictly rejects proposer attempts to smuggle authorization. Licensed action is only created by the CORE substrate.

---

## 3. Data Schemas
The demo relies on abstracted JSON schemas representing the state and transitions of a robotic cell.

### `scene_state`
Represents the current static physical environment and parameters.
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SceneState",
  "type": "object",
  "properties": {
    "robot_id": { "type": "string" },
    "arm_status": { "type": "string", "enum": ["idle", "moving", "stopped"] },
    "current_joint_angles": {
      "type": "array",
      "items": { "type": "number" },
      "minItems": 6,
      "maxItems": 6
    },
    "detected_obstacles": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "label": { "type": "string" },
          "distance_meters": { "type": "number" },
          "zone": { "type": "string", "enum": ["clear", "warning", "critical"] }
        },
        "required": ["label", "distance_meters", "zone"]
      }
    },
    "payload_loaded": { "type": "boolean" },
    "estop_pressed": { "type": "boolean" }
  },
  "required": ["robot_id", "arm_status", "current_joint_angles", "detected_obstacles", "payload_loaded", "estop_pressed"]
}
```

### `proposed_transition`
The state transition suggested by the mock proposer.
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ProposedTransition",
  "type": "object",
  "properties": {
    "proposed_action": { "type": "string" },
    "target_joint_angles": {
      "type": "array",
      "items": { "type": "number" },
      "minItems": 6,
      "maxItems": 6
    },
    "velocity_scale": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
    "security_handshake": { "type": "string" }
  },
  "required": ["proposed_action", "target_joint_angles", "velocity_scale"]
}
```

### `authority_envelope`
The rules and thresholds evaluated by CORE.
```json
{
  "max_velocity_scale": 0.5,
  "min_obstacle_distance_meters": 0.8,
  "requires_human_confirmation_for": ["payload_unload", "tool_swap"],
  "handshake_secret": "secure_core_handshake"
}
```

### `outcome`
The concrete evaluation result from CORE.
```json
{
  "outcome_status": "authorized | ask | refused | safe_stop | invalid",
  "reason": "string",
  "licensed_action": {
    "action_id": "string",
    "authorized_timestamp": "string",
    "checksum": "string"
  }
}
```

### `trace`
The byte-identical evidence containing the hash of `scene_state` + `proposed_transition` + `outcome`.

---

## 4. Proposed Scenarios

### Scenario 1: Authorized Low-Risk Transition
* **Initial State:** Arm status is `idle`, obstacles are at `1.5` meters (`clear` zone), no E-stop.
* **Proposal:** Transition to joint configuration to sort a part. Velocity scale is `0.3`.
* **CORE Evaluation:** Evaluates against the envelope. Since velocity is under `0.5` and obstacles are clear, it outputs `authorized` with a generated `licensed_action` object.

### Scenario 2: Human Confirmation Required (`ask`)
* **Initial State:** Obstacles clear, payload loaded.
* **Proposal:** Transition to unload payload.
* **CORE Evaluation:** Matches the rule `requires_human_confirmation_for` containing `"payload_unload"`. Outputs `ask` state, halting execution until an external confirmation is appended.

### Scenario 3: Unsafe/Uncertain Transition Refused
* **Initial State:** Obstacle detected at `0.5` meters (`critical` zone).
* **Proposal:** Movement of the arm.
* **CORE Evaluation:** Violates the `min_obstacle_distance_meters` (0.8) threshold. Outputs `refused` and does not generate a licensed action.

### Scenario 4: Sensor/State Conflict Causes Safe-Stop
* **Initial State:** E-stop is pressed (`estop_pressed: true`), or arm status is `stopped` but target joint angles propose a motion.
* **Proposal:** Move arm to home position.
* **CORE Evaluation:** The presence of `estop_pressed: true` overrides all evaluations, forcing the outcome to `safe_stop`, invalidating all motion paths.

### Scenario 5: Proposer Attempts to Smuggle Authorization
* **Proposal:** The mock proposer injects a custom `licensed_action` or attempts to set `outcome_status` within its input payload.
* **CORE Evaluation:** Schema validation fails, or CORE ignores the smuggled fields. Outputs `invalid`, proving the proposer cannot grant its own license.

---

## 5. Testing and Validation Requirements
* **Double-Run Byte-Identical Output:** Running the same simulation parameters twice must yield binary-identical outputs and matching trace hashes.
* **Tamper-Sensitive Expected Artifacts:** Modifying any byte of the scene state or proposal results in a mismatched trace hash.
* **Fails-Closed:** Unsafe or unrecognized scenarios must default to `refused` or `safe_stop` rather than authorizing.
* **No Sandbox Escape:** The verification script must run in a pure Python sandbox without triggering external subprocesses, network requests, or `eval()` injections.

---

## 6. README Honesty Ledger

### What This Proves:
1. That a stochastic model can act purely as a *proposer*, without the capability to write or execute its own commands.
2. That a deterministic, schema-bound validator (CORE) can govern physical state transitions.
3. That safety conflicts (such as E-stops or obstacle violations) can be resolved at the boundary before execution.
4. That the decision process is fully auditable via a cryptographic trace hash.

### What This Does Not Prove:
1. It does not prove that CORE can control a physical robot or drive a vehicle.
2. It does not validate low-level joint interpolation, kinematics, or sensor fusion.
3. It does not replace functional safety hardware (SIL-3/PL-e) or ISO 13849/ISO 26262 compliance.
4. It does not guarantee that the high-level scene state perfectly reflects the physical world (perception errors remain out of scope).

### Why It Is Simulation-Only:
Autonomy safety requires decoupling software-level decision audits from real-time physical control. By keeping the demo simulation-only, we demonstrate the architectural pattern of an authority boundary without introducing risks associated with deployable robotics code.
