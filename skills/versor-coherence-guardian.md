---
name: versor-coherence-guardian
description: Enforce Versor Coherence Guardian Protocol + exact algebraic closure before any change in algebra/, field/, vault/, or generate/. Auto-triggers on relevant paths.
triggers: ["pre_edit:algebra/", "pre_edit:field/", "pre_edit:vault/", "pre_edit:generate/", "manual"]
auto_invoke: true
---

Before any edit or proposal in the triggered paths, execute the **Versor Coherence Guardian Protocol** from GROK.md:

1. Confirm `||F * reverse(F) - 1||_F < 1e-6` holds for affected FieldState(s).
2. Verify that `versor_apply(V, F)` and `cga_inner(X, Y)` paths remain exact.
3. Re-run relevant checks from `tests/test_versor_closure.py` (or current equivalent).
4. Only proceed if all checks pass. Block or surface any violation immediately.

This skill is non-bypassable for the listed modules. It is the primary enforcement mechanism for CORE's core algebraic invariant.