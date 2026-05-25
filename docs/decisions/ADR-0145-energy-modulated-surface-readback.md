# ADR-0145: Energy-Modulated Vault Surface Readback

**Status:** Proposed
**Date:** 2026-05-25
**Related:** ADR-0006 (field energy operator), ADR-0004 (vault), W-004 (rethaw)

---

## Context

Under the current architecture:
- Vault recall re-thaws to energy class `E2` (defined in W-004).
- The realized output surface currently ignores the energy class of the grounded turn.
- ADR-0006 §Integration Points explicitly specifies that surface readback should be modulated by the energy class of the grounding source.

This creates a gap where vault-grounded turns are realized without their appropriate energy-modulated prefix, violating the specification of ADR-0006.

---

## Decision

To align surface readback with the energy-modulation requirements of ADR-0006:

1. **Energy Modulation Function:**
   Implement `energy_modulated_surface(base: str, energy_class: EnergyClass | str | None) -> str` in [realizer.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/adr-w005-surface-readback/generate/realizer.py). This function will prepend the appropriate prefix based on the energy class:

   | Energy Class | Prefix | Example Output |
   |---|---|---|
   | `E0` | `"From memory: "` | `"From memory: {surface}"` |
   | `E1` | `"I seem to recall: "` | `"I seem to recall: {surface}"` |
   | `E2` | `"I recall: "` | `"I recall: {surface}"` |
   | `E3`, `E4` | *None* | `"{surface}"` |

   If the base string is empty, the returned value remains empty.

2. **Threading the Energy Class:**
   - Add `recall_energy_class: str | None` to `CognitiveTurnResult` in [result.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/adr-w005-surface-readback/core/cognition/result.py).
   - Thread the `recall_energy_class` from the pipeline to `ChatResponse` in [runtime.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/adr-w005-surface-readback/chat/runtime.py).

3. **Modulation Application:**
   Apply the modulation explicitly in [runtime.py](file:///Users/kaizenpro/.gemini/antigravity/worktrees/core/adr-w005-surface-readback/chat/runtime.py) on grounding pathways where `grounding_source == "vault"`.

---

## What is NOT done

- **E3/E4 Vault Modulation:** While the prefix table handles `E3` and `E4` by prepending nothing, no current vault recall pathways produce energy states reaching `E3` or `E4`.
- **Readback from Intent:** Rules relating to `readback_from_intent` in `runtime_rules.py` are deferred to W-006 scope.

---

## Consequences

- Surfaces retrieved from the vault (which default to `E2` on re-thaw) will now be prefixed with `"I recall: "`.
- Pack-grounded and teaching-grounded surfaces remain unaffected and will not receive energy modulation prefixes.
- `recall_energy_class` is exposed as an inspectable property on `ChatResponse` and `CognitiveTurnResult`.

---

## References

- **ADR-0006**: Field Energy Operator
- **ADR-0004**: Vault Design
- **W-004**: Vault Re-thaw
