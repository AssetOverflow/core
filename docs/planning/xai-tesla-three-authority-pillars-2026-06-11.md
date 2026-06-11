# The Three Pillars of Authority
**Date: 2026-06-11**

---

This document outlines the three foundational pillars of CORE's authority architecture for high-consequence systems: **Epistemic Authority**, **Tool / Digital Action Authority**, and **Embodied Authority**. 

---

## Pillar 1: Epistemic Authority

### The Core Question
> **What can the model claim as known, evidenced, verified, inferred, contradicted, or undetermined?**

### The CORE Role
In truth-seeking AI architectures, it is vital to distinguish between a model's *rhetorical confidence* and its *epistemic status*. A frontier model may generate highly plausible statements, but it cannot independently audit its own factual alignment against a closed database or logic engine in a deterministic, replayable manner. 

CORE acts as the epistemic verification layer. It receives semantic propositions from the model, evaluates them against defined semantic packs and local logic constraints, and outputs a concrete, replayable epistemic state.

### Relevant Outcomes
*   **`verified`**: The proposition matches explicit truth conditions in the deterministic substrate.
*   **`evidenced`**: The proposition is supported by a documented chain of evidence, though not fully proven.
*   **`inferred`**: The proposition represents a logically valid deduction from verified premises.
*   **`contradicted`**: The proposition directly violates known facts or logical constraints in the substrate.
*   **`undetermined`**: There is insufficient evidence to verify, evidence, or contradict the proposition.
*   **`refused`**: The proposition is rejected due to policy constraints or semantic boundary violations.
*   **`ask`**: The proposition requires human-in-the-loop clarification or external database lookup to resolve.

---

## Pillar 2: Tool / Digital Action Authority

### The Core Question
> **What digital action can the model propose, and what can actually be licensed?**

### The CORE Role
Stochastic models are increasingly integrated with digital APIs, databases, and operating systems. If a model generates a tool call, executing it directly grants the model immediate digital agency, leaving the system vulnerable to prompt injections, hallucinations, and unauthorized executions.

CORE separates the *proposal* of a tool call from its *licensing*. The model suggests an action, but the CORE substrate acts as a deterministic firewall. It validates the proposed parameters against a strict, typed schema, checks user-defined permission envelopes, and determines whether the action is licensed for execution.

### Relevant Outcomes
*   **`authorized`**: The proposed tool call satisfies all safety parameters and permission envelopes, granting a license to execute.
*   **`refused`**: The tool call is rejected because it falls outside permissible bounds.
*   **`ask`**: The tool call is temporarily held pending explicit human approval (e.g., high-risk financial transfers).
*   **`invalid`**: The proposed tool call violates schema typing or parameter constraints.

---

## Pillar 3: Embodied Authority

### The Core Question
> **When AI moves into vehicles, robots, factories, labs, or physical systems, what proposed physical transition is admissible from the current state?**

### The CORE Role
When artificial intelligence interacts with the physical world (e.g., robotics, autonomous vehicles, industrial machinery), the cost of failure is physical harm or destruction. Giving a stochastic model direct control over actuator voltages, motor torque, or steering angles is an unacceptable safety risk.

> [!IMPORTANT]
> **CORE does not drive a car, pilot a rocket, or control a robot.**
> CORE demonstrates an authority-boundary pattern for model-proposed transitions.

CORE operates as a simulation and proof boundary. It does not replace real-time control theory, perception, or hardware-level safety limits. Instead, it evaluates the *semantic state transition* proposed by the model. By modeling the current scene state and checking the proposed transition against safety invariants, CORE determines if the transition is admissible before any action becomes a licensed command.

### Relevant Outcomes
*   **`authorized`**: The proposed physical transition is within the safe operational envelope.
*   **`ask`**: The transition is held, requiring human confirmation before proceeding.
*   **`refused`**: The transition is rejected as unsafe or out-of-envelope.
*   **`safe_stop`**: A state or sensor conflict is detected, forcing the system to execute an immediate, controlled transition to a safe, static configuration.
*   **`invalid`**: The proposed transition is malformed or attempts to bypass the safety envelope.
