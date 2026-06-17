# CORE Agent Instructions for Grok 4.3

Read this file in full before touching any file in this repository.
CORE is a deterministic cognitive engine — not a transformer wrapper, not a generic chatbot, not an infrastructure playground. The rules here are architectural invariants, not suggestions.

> **You are stateless.** You have no memory of prior sessions.
> Complete the [Session Start Checklist](#session-start-checklist) before any edits. Do not skip it.

---

## Phase-Specific Prompt Library

For detailed, phase-oriented guardrails that are tightly coupled to CORE’s architecture, invariants, ADRs, and epistemic model, see:

**`docs/core-rd-base-prompts.md`**

These prompts are designed to be used as standing prefixes **in addition to** this file. The "Session Entry / Context Load" prompt is especially recommended at the start of most sessions. The "Standing Loop Axiom Check" is highly effective as a final self-audit before committing.

---

## Session Start Checklist

Run these steps in order, using your tool-call chains, before writing a single line of code:

1. **Read this file in full.**
2. **Read `AGENTS.md` in full.**
3. **Read `docs/runtime_contracts.md` in full.**
4. **Run the smoke suite and report pass/fail:**
   ```bash
   core test --suite smoke -q
   ```
5. **Check for a recent handoff doc** — if a `HANDOFF-*.md` file exists dated within the last 3 days, read it. It contains state you would otherwise have no way to recover.
6. **State your task scope** — before editing, write one sentence naming the module(s) you intend to change and the invariant you will prove was not violated.

Do not treat conversation history as a substitute for steps 1–5. History does not survive context resets. Ground yourself in the repo.

---

## Reasoning Effort Requirement

You must operate at **high reasoning effort** for all tasks that touch:

- `algebra/`
- `field/`
- `generate/realizer.py`, `generate/graph_planner.py`, `generate/intent.py`
- `vault/store.py`
- `calibration/`
- `core/cognition/`
- `teaching/`

If you were invoked at default or low effort and the task touches any of these modules, **stop and request re-invocation at high effort.** Low-effort reasoning on the algebra/field layer produces plausible-looking but mathematically incorrect results.

For `workbench-ui/`, `docs/`, `notes/`, `scripts/` at low risk, medium effort is acceptable.

---

## Versor Coherence Guardian Protocol

Before proposing or executing **any** change that could affect versor closure, field propagation, or exact CGA recall:

1. Explicitly confirm that the core invariant holds: `||F * reverse(F) - 1||_F < 1e-6` for the affected `FieldState`.
2. Verify that `versor_apply(V, F)` and `cga_inner(X, Y)` paths remain exact and untouched except through the allowed modules (`algebra/versor.py` and permitted callers).
3. Re-run the relevant invariant checks from `tests/test_versor_closure.py` (or current equivalent) on the modified paths.
4. Only after the above may you proceed with edits or proposals.

This protocol is mandatory for any work in `algebra/`, `field/`, `vault/`, or `generate/`.

---

## NON-NEGOTIABLE INVARIANTS

These are **hard architectural constraints enforced by construction**. Violating any one of them is a bug that must be reverted before merge.

**Versor & CGA Level (Exact Algebraic Coherence)**
- `||F * reverse(F) - 1||_F < 1e-6` must hold identically for **every** runtime `FieldState` and every application of `versor_apply(V, F)`.
- All state is represented as versors. All transitions are exact versor products. No exceptions, no approximations.
- Multivector representation in `algebra/` uses fixed `(32,)` float32 arrays for Cl(4,1). No dynamic resizing or external library types in the hot path.
- `cga_inner(X, Y) = -d²/2` is the sole exact recall primitive. It must remain exact and deterministic.

**Normalization & Approximation Boundaries**
- Normalization is allowed **ONLY** at the explicitly listed locations:
  - `ingest/gate.py`
  - `language_packs/compiler.py`
  - `algebra/versor.py`
  - `sensorium/*/canonical.py` (signal canonicalization, pinned only)
  - `session/context.py` (semantic anchoring)
- Forbidden everywhere else, including `generate/stream.py`, `field/propagate.py`, `vault/store.py`, and all logging/telemetry paths.

**No Approximate or Stochastic Mechanisms**
- No cosine similarity, HNSW, ANN indexes, embedding-based recall, or any approximate nearest-neighbor mechanism anywhere in the deterministic cognitive path.
- Vault recall is **exact** `cga_inner` only.
- No stochastic generation, sampling, opaque LLM fallbacks, or probabilistic mechanisms in the core deterministic reasoning, teaching, recognition, or realization pipelines.

**Claim Schema & Epistemic Rigor**
- Claim status transitions (SPECULATIVE → COHERENT → CONTESTED → FALSIFIED) may only occur through the defined review-gated TeachingChainProposal mechanism.
- A claim may not move to COHERENT without passing all applicable review gates and producing a reproducible evidence bundle.
- No direct mutation of epistemic status. Only `vault/store.py` may transition status (INV-29).
- User-facing `vault.recall` must enforce `min_status=COHERENT` (INV-24).

**Safety & Identity Packs**
- Safety packs (`packs/safety/`) are **unmodifiable at runtime**. They are fail-closed and reviewer-signed.
- Identity packs are swappable only via the defined PersonaMotor + proposal mechanism. Runtime mutation is forbidden.
- Any attempt to relax or bypass a safety axis must be rejected and logged as a protocol violation.

If you believe one of these must change for correctness or performance reasons, **STOP**. Write a proposal in `notes/` or `docs/decisions/` and do not implement the change. CORE’s architecture is not negotiated inside a coding session.

---

## Pre-Edit Sweep Protocol

Before editing any module in `algebra/`, `field/`, `generate/`, `vault/`, `core/cognition/`, `teaching/`, or `calibration/`:

1. Use your file-read and search tool chains to **trace every import** of the target module across the codebase.
2. Identify **all callers** of the specific function or class you intend to change.
3. Check `calibration/` and `evals/` for tests that exercise the changed path.
4. Only then propose edits.

Your 1M-token context window means you can load the full relevant subgraph in one pass. Do this. Do not guess at call sites.

---

## Agentic Tool-Call Discipline

Grok 4.3's multi-step tool-call chains are an asset here. Use them to:
- Load the full affected module graph before proposing changes.
- Run CLI validation lanes and report actual output, not assumed output.
- Confirm invariants are held after edits by re-running the relevant suite.

Do not use tool chains to:
- Probe for statistical or ML-based workarounds to exact CGA constraints.
- Discover "alternative" normalization sites not listed above.
- Chain edits across multiple modules before verifying the first one.

---

## Arena / Parallel Subagent Mode

If running in Arena mode (parallel subagents):

- Each subagent **receives its own copy of this file and AGENTS.md**.
- Each subagent must **independently satisfy** `||F * reverse(F) - 1||_F < 1e-6` before reporting results.
- Do not share mutable runtime state between subagents.
- Treat Arena subagent results as **independent proposals**, not sequential commits. Reconcile them before any merge.
- No subagent output becomes another subagent's unchecked input.

---

## End-of-Session Handoff Requirement

At the end of every session, write a handoff document to the repo using the template at `docs/handoff_template.md`. Name it:

```
HANDOFF-grok43-YYYY-MM-DD.md
```

This is not optional. It is the only continuity mechanism across your stateless sessions. A session without a handoff doc is a session whose work may be silently lost or contradicted by the next session.

---

## Architecture Summary

Raw input becomes a closed versor field once; thought evolves through exact versor transitions and CGA recall; cognition is structured as intent, proposition graph, articulation target, deterministic realization, reviewed memory, eval/calibration replay, and traceable evidence.

```text
CognitiveTurnPipeline
  -> tokenize / OOV policy / inject
  -> intent classification
  -> PropositionGraph
  -> ArticulationTarget
  -> deterministic realizer / articulation surface
  -> generation walk telemetry
  -> identity + energy telemetry
  -> reviewed teaching capture (when correction intent appears)
  -> deterministic trace hash
```

Key modules:
- `core/cognition/pipeline.py` — cognitive turn spine
- `core/cognition/result.py` — canonical turn result shape
- `core/cognition/trace.py` — deterministic trace hashing
- `generate/intent.py` — deterministic intent classification
- `generate/graph_planner.py` — proposition graph and articulation target
- `generate/realizer.py` / `generate/templates.py` — deterministic realization
- `teaching/*` — reviewed teaching / correction lifecycle
- `vault/store.py` — epistemic store with INV-21/22/23/24/29 guards
- `evals/*` — deterministic eval harness
- `calibration/*` — bounded replay-based calibration
- `docs/runtime_contracts.md` — runtime response, memory, identity, and testing

---

## PR Checklist

Before opening or merging, answer:

```text
What capability, performance property, or security boundary did this add/protect?
Which invariant proves the field remains valid?
Which CLI suite/eval proves the lane?
Did this avoid hidden normalization, stochastic fallback, approximate recall, and unreviewed mutation?
If it touches user input, files, dynamic imports, or logs, what trust boundary was enforced?
Was the smoke suite green before and after?
```

Prefer small, load-bearing PRs.

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

Run the smallest relevant suite first, then `full` before merge.