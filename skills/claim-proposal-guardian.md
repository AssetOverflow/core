---
name: claim-proposal-guardian
description: Enforce review-gated claim status transitions and epistemic rigor. Prevents direct mutation of SPECULATIVE / COHERENT / CONTESTED / FALSIFIED status.
triggers: ["pre_edit:teaching/", "pre_edit:core/cognition/", "pre_edit:vault/", "manual"]
auto_invoke: true
---

Before any change involving claim status, TeachingChainProposal, or epistemic_status:

1. Confirm the change goes through the defined review-gated proposal mechanism only.
2. Verify no direct mutation of claim status or epistemic_status outside `vault/store.py` (INV-29).
3. Ensure user-facing recall respects `min_status=COHERENT` (INV-24).
4. Block or surface any attempt to bypass review gates.

This skill protects CORE's truth-seeking schema and epistemic integrity.