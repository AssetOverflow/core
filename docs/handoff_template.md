# HANDOFF — [AGENT] — [YYYY-MM-DD]

<!-- Copy this file, rename to HANDOFF-[agent]-YYYY-MM-DD.md, fill in all
     sections.  Do not leave placeholders.  This doc is the ONLY continuity
     mechanism for stateless agents (Grok 4.3, GPT-5.5) across sessions. -->

## Agent and Session

- **Agent:** <!-- grok43 | gpt55 | claude | other -->
- **Date:** <!-- YYYY-MM-DD -->
- **Reasoning effort used:** <!-- high | medium | low -->
- **Session entry point:** <!-- What task was handed to this agent? -->

---

## Smoke Suite Status

```
<!-- Paste output of: core test --suite smoke -q -->
```

---

## Modules Touched

<!-- List every file modified, created, or deleted this session. -->

| File | Change type | Summary |
|---|---|---|
| | | |

---

## Invariants Verified

<!-- For each invariant relevant to this session, state how it was confirmed. -->

| Invariant | Check performed | Result |
|---|---|---|
| versor_condition < 1e-6 | | |
| Normalization boundary | | |
| No approximate recall | | |
| INV-21 (VaultStore callers) | | |
| Other (name it) | | |

---

## Tests Run

```bash
# Commands run and their exit status:
```

---

## Open Tasks / Next Session Entry Point

<!--
  Be specific.  "Continue the work" is not acceptable.
  Name the exact module, function, or ADR phase the next session should start on.
-->

1.
2.
3.

---

## Known Hazards / Do Not Touch

<!--
  Anything that is mid-refactor, has a known fragile state, or must not be
  edited until a specific prior step is complete.
-->

---

## Architectural Decisions Made This Session

<!--
  Any decision that affects more than this session's diff — operator choices,
  boundary calls, ADR interpretations.  Future sessions need this context.
-->

---

## What Must Not Be Forgotten

<!--
  The single most important thing the next session agent must know.
  Write it as if this doc is the only thing they will read.
-->
