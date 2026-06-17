# HANDOFF — [AGENT] — [YYYY-MM-DD]

<!-- Copy this file, rename to HANDOFF-[agent]-YYYY-MM-DD.md, fill in all
     sections completely. This is the ONLY continuity mechanism for stateless
     agents (Grok 4.3 / Grok Build) across sessions. Do not leave placeholders. -->

## Agent and Session

- **Agent:** <!-- grok43 | gpt55 | claude | other -->
- **Date:** <!-- YYYY-MM-DD -->
- **Reasoning effort used:** <!-- high (mandatory for algebra/field) | medium | low -->
- **Grok Build mode used:** <!-- TUI | Plan Mode | Arena (parallel subagents) | Headless -->
- **Session entry point:** <!-- Exact task handed to this agent -->

---

## Smoke Suite + Bootstrap Status

```
<!-- Paste output of: core test --suite smoke -q -->
<!-- Confirm core-bootstrap skill completed successfully -->
```

---

## Modules Touched

<!-- List every file modified, created, or deleted this session. -->

| File | Change type | Summary |
|---|---|---|
| | | |

---

## Invariants Verified (Versor Coherence Guardian + Core)

<!-- For each relevant invariant, state how it was confirmed. Include Versor Coherence Guardian checks. -->

| Invariant | Check performed | Result | Notes |
|---|---|---|---|
| `||F * reverse(F) - 1||_F < 1e-6` (core closure) | Versor Coherence Guardian + tests/test_versor_closure.py | | |
| versor_apply / cga_inner exactness | Manual trace + re-run of affected paths | | |
| Normalization boundaries respected | Pre-edit sweep + code review | | |
| No approximate recall (ANN/HNSW/cosine) | Full import/call-site sweep | | |
| Claim status transitions via review gates only | Claim-proposal-guardian checks | | |
| Safety/identity pack immutability | Safety-pack-auditor | | |
| INV-21 / INV-24 / INV-29 (Vault & epistemic) | Explicit verification | | |
| Other (name it) | | | |

---

## Subagent / Arena Reconciliation (if applicable)

<!-- If Arena/parallel subagents were used -->
- Number of subagents spawned: 
- Each subagent independently verified versor closure? (Yes/No)
- How were results reconciled before merge?

---

## Tests Run

```bash
# Commands run and their exit status:
```

---

## Open Tasks / Next Session Entry Point

<!-- Be extremely specific. "Continue the work" is not acceptable. -->

1.
2.
3.

---

## Known Hazards / Do Not Touch

<!-- Mid-refactor state, fragile areas, or steps that must complete first. -->

---

## Architectural Decisions Made This Session

<!-- Any decision affecting future sessions (operator choices, boundary calls, ADR interpretations). -->

---

## What Must Not Be Forgotten

<!-- The single most important thing the next agent must know. Write it as if this is the only document they will read. -->

**Prompt Library Reference**: See `docs/core-rd-base-prompts.md` (especially sections #7 Standing Loop Axiom Check, #8 PR Merge-Readiness Audit, and #9 Grok Build Implementation Session). Use them as standing prefixes.

---

## Skills Used This Session

<!-- List which Grok Build skills were invoked (manual or auto-triggered) -->
- core-bootstrap: 
- versor-coherence-guardian: 
- pre-edit-sweep: 
- claim-proposal-guardian: 
- Other: 
