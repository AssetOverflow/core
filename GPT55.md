# CORE Agent Instructions for GPT-5.5 (o3-class)

Read this file in full before touching any file in this repository.
CORE is a deterministic cognitive engine — not a transformer wrapper, not a
generic chatbot, not an infrastructure playground.

> **You are stateless across API sessions.** You have no persistent memory
> of prior conversations.  Complete the
> [Session Start Checklist](#session-start-checklist) before any edits.

---

## Session Start Checklist

1. **Read this file in full.**
2. **Read `AGENTS.md` in full.**
3. **Read `docs/runtime_contracts.md` in full.**
4. **Run the smoke suite:**
   ```bash
   core test --suite smoke -q
   ```
5. **Check for a handoff doc** — read the most recent `HANDOFF-*.md` if one
   exists dated within the last 3 days.
6. **State your task scope** — before editing, name the module(s) and the
   invariant you will prove was not violated.

---

## Reasoning and Tool Use

GPT-5.5 (o3-level) has strong multi-step reasoning.  Use it here by:

- **Reasoning through the full operator chain** before proposing edits to
  algebra or field modules.  Do not shortcut the math.
- **Using tool calls** to sweep import graphs and call sites before editing.
- **Stating your reasoning** about why an edit preserves versor_condition
  before writing the code.

For extended thinking mode: enable it for any task touching `algebra/`,
`field/`, `vault/`, `calibration/`, or `core/cognition/`.

---

## NON-NEGOTIABLE INVARIANTS

```
❌  versor_condition(F) < 1e-6 at every runtime field state.
    Fix the operator/construction boundary; do not weaken the threshold.

❌  Normalization only at:
      ingest/gate.py
      language_packs/compiler.py
      algebra/versor.py
      sensorium/*/canonical.py
      session/context.py  (semantic anchoring only — see CLAUDE.md)
    Forbidden in: generate/stream.py, field/propagate.py, vault/store.py,
    logging/telemetry layers.

❌  No cosine similarity, HNSW, ANN, or approximate recall in runtime.
    Vault recall is exact and deterministic.

❌  No stochastic generation or opaque LLM fallbacks in the cognitive path.

❌  No pack mutation outside the proposal-only reviewed teaching loop.

❌  INV-21/22/23/24/29/30 (see CLAUDE.md for full text).
```

---

## GPT-5.5 Specific Cautions

GPT-5.5's code generation is fluent and fast.  That fluency creates
specific risks for CORE:

- **Do not generate "helpful" utility wrappers** that centralize normalization
  or add intermediate caching layers.  CORE's architecture is already
  explicit about where these belong.
- **Do not add type coercions** in hot-path algebra that silently
  re-normalize field state.
- **Do not suggest async/concurrent refactors** to vault or algebra paths
  without a full trace of the determinism contract.
- **Tool-use completions that look finished may not be** — always run the
  CLI validation suite, do not assume correctness from code inspection alone.

---

## Pre-Edit Sweep Protocol

Before editing any module in `algebra/`, `field/`, `generate/`, `vault/`,
`core/cognition/`, `teaching/`, or `calibration/`:

1. Trace every import of the target module.
2. Identify all callers of the target function/class.
3. Check `evals/` and `calibration/` for tests covering the changed path.
4. Only then propose edits.

---

## End-of-Session Handoff Requirement

At the end of every session, write a handoff document using the template
at `docs/handoff_template.md`.  Name it:

```
HANDOFF-gpt55-YYYY-MM-DD.md
```

---

## Architecture Summary

Raw input becomes a closed versor field once; thought evolves through exact
versor transitions and CGA recall; cognition is structured as intent,
proposition graph, articulation target, deterministic realization, reviewed
memory, eval/calibration replay, and traceable evidence.

See `AGENTS.md` for the full cognitive path, key modules, and PR checklist.

---

## CLI Validation Lanes

```bash
core test --suite smoke -q
core test --suite cognition -q
core test --suite teaching -q
core test --suite packs -q
core test --suite runtime -q
core test --suite algebra -q
core test --suite full -q
core eval cognition
```
