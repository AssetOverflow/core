# ADR-0145: Energy-Modulated Vault Surface Readback

**Status:** Accepted  
**Date:** 2026-05-25  
**Related:** ADR-0006 (field energy operator), ADR-0004 (vault), W-004 (rethaw), W-005

---

## Context

ADR-0006 §Integration Points specifies that surface readback should be modulated
by the energy class of the grounding source.  W-004 (PR #251) landed vault
re-thaw to E2 — every vault recall result carries
`energy_profile.energy_class = EnergyClass.E2`.

Despite this, the surface realization path was ignoring `energy_profile`
entirely.  The energy class was stamped onto recall results but never reached
the output surface, violating the ADR-0006 specification.

---

## Decision

1. **`energy_modulated_surface(base, energy_class)`** added to
   `generate/realizer.py`.  Prefix table (ADR-0006 §Integration Points):

   | Energy Class | Prefix |
   |---|---|
   | E0 | `"From memory: "` |
   | E1 | `"I seem to recall: "` |
   | E2 | `"I recall: "` |
   | E3, E4 | *(none — pass through)* |

   Empty base string passes through unchanged.

2. **`recall_energy_class: str | None`** added to `CognitiveTurnResult`
   (`core/cognition/result.py`) and to `_ChatState` / `ChatResponse`
   (`chat/runtime.py`).

3. **Wiring in `chat/runtime.py`**: `_recall_energy_class_from_hits()` reads
   the energy class from the top vault hit.  On the vault path
   (`main_grounding_source == "vault"`), `energy_modulated_surface()` is
   applied and the result replaces `response_surface`.

4. **Scope**: modulation applies only on `grounding_source == "vault"`.
   Pack-grounded and teaching-grounded surfaces are not affected.

---

## What is NOT in scope

- E3/E4 vault paths (no current pathway rethaws to these classes).
- `readback_from_intent` rules in `packs/common/runtime_rules.py` — deferred
  to W-006.

---

## Consequences

- Vault-grounded turns (always E2 post-rethaw) are prefixed with `"I recall: "`.
- `recall_energy_class` is inspectable on `ChatResponse` for telemetry and
  testing.
- No change to trace hash or determinism: the prefix is applied after the
  articulation surface is committed for hashing.

---

## References

- **ADR-0006**: Field Energy Operator
- **ADR-0004**: Vault Design
- **W-004** (PR #251): vault re-thaw to E2
