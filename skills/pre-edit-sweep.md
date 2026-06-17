---
name: pre-edit-sweep
description: Execute full import/call-site + eval/calibration trace before editing sensitive modules. Complements the Versor Coherence Guardian.
triggers: ["pre_edit:algebra/", "pre_edit:field/", "pre_edit:vault/", "pre_edit:generate/", "pre_edit:core/cognition/", "pre_edit:teaching/", "pre_edit:calibration/", "manual"]
auto_invoke: true
---

Before editing any module in the triggered paths:

1. Use file-read and search tool chains to trace **every import** of the target module.
2. Identify **all callers** of the specific function/class being changed.
3. Check `calibration/` and `evals/` for tests exercising the changed path.
4. Only after completing the sweep may you propose or apply edits.

Your 1M context window exists for this. Use it. Do not guess at impact.