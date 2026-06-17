# CORE Agent Instructions

This repository is building a deterministic cognitive engine, not a transformer
wrapper and not a demo chatbot.  Every agent must preserve the geometric
runtime while moving the system toward teachable cognitive chat.

## Agent-Specific Instruction Files

Different agents read a supplementary file alongside this one.  Read yours
before touching any code:

| Agent | Supplementary file | Key differences |
|---|---|---|
| **Claude** | `CLAUDE.md` | Deep context; self-restraining; read for semantic anchoring rule nuance |
| **Grok 4.3 + Grok Build** | `GROK.md` | Stateless; requires high reasoning effort; mandatory workspace hygiene; Arena/parallel subagent rules; Plan Mode preferred; skills system; see also docs/core-rd-base-prompts.md for phase-specific prompts |
| **GPT-5.5 (o3-class)** | `GPT55.md` | Stateless; fluency cautions; extended thinking for algebra/field work |

If you are Grok 4.3 or GPT-5.5, complete the Session Start Checklist in your
file before reading anything else in this file.

## Grok 4.3 / Grok Build Hard Stops (Mastery Level)

These apply to Grok 4.3 and Grok Build in addition to every rule below:

1. **You are stateless.** Read `GROK.md` in full, `docs/runtime_contracts.md`, and the most recent `HANDOFF-*.md` (if dated within 3 days) before any edits.
2. **Workspace hygiene is mandatory.** Before branch movement or edits, confirm cwd/repo root, inspect dirty state, classify loose files, fetch/prune, establish clean current `main`, and use a fresh worktree for non-trivial implementation.
3. **High reasoning effort is mandatory** for all tasks touching `algebra/`, `field/`, `generate/realizer.py`, `generate/graph_planner.py`, `generate/intent.py`, `vault/store.py`, `calibration/`, `core/cognition/`, or `teaching/`.
4. **Use Plan Mode** (Grok Build) for any non-trivial change in the above modules. Direct edits are discouraged.
5. **Skills are the preferred mechanism** for repeated protocols. Use `/core-bootstrap`, `/versor-coherence-guardian`, `/pre-edit-sweep`, and `/claim-proposal-guardian` (or their auto-triggered versions).
6. **Sweep before you edit.** Use tool-call chains to trace imports and call sites.
7. **Write a handoff doc at session end** using `docs/handoff_template.md`.
8. **Arena / parallel subagents:** each subagent independently satisfies `||F * reverse(F) - 1||_F < 1e-6` before reporting. Reconcile results before any merge. No mutable state sharing.

---

## North Star

CORE should become capable of:

```text
listen -> comprehend -> recall -> think -> articulate -> learn from reviewed correction -> replay deterministically
```

The current path is intentionally staged:

1. Maintain algebra/runtime invariants.
2. Use `CognitiveTurnPipeline` as the spine.
3. Classify intent and build proposition graphs.
4. Plan articulation targets and realize them deterministically.
5. Capture reviewed teaching corrections safely.
6. Seed compact semantic packs for cognition vocabulary.
7. Evaluate through CLI lanes, not ad hoc test fragments.
8. Calibrate bounded operators only from replayable evidence.

Do not skip ahead by adding opaque models, stochastic generation, or broad
infrastructure that hides whether CORE itself is improving.

## Philosophical and Architectural Stance

Truth is coherent.  CORE's work is to preserve coherent structure from input to
field state to articulation to memory.  Treat identity, truthfulness, and
replayability as architectural commitments rather than prompt preferences.

The system's intelligence should come from inspectable geometric state,
structured propositions, deterministic recall, reviewed teaching, and bounded
calibration.  Avoid nihilistic or purely statistical framing in code comments,
agent plans, and docs.  Prefer responsibility, provenance, and stable meaning.

## The Hard Field Invariant

Every runtime field state `F` must satisfy:

```text
versor_condition(F) < 1e-6
```

This is checked by `algebra/versor.py::versor_condition()`.

If a propagation path violates this invariant, fix the operator path or the
explicit algebra/construction boundary that owns the transition.  Do not hide
violations by changing tests, silently weakening thresholds, or normalizing in
forbidden places.
