# ASK Runtime Wiring — The Missing Boundary (Stop-and-Document)

**Date:** 2026-06-10
**Branch:** `feat/ask-runtime-wire`
**Issue:** #680 (final `chat/runtime.py` wiring)
**Status:** STOPPED before wiring. No `chat/runtime.py` edit was made.

## 1. Why this is a stop-and-document, not a wiring PR

The task to wire `chat.ask_runtime.maybe_apply_served_ask` into `chat/runtime.py`
carried an explicit pre-condition:

> If no lawful `ContemplationResult` or provider exists at the boundary, do not
> invent one. Stop and document the exact missing boundary.

That pre-condition is **met**. A `QUESTION_NEEDED` `ContemplationResult` cannot be
obtained at the runtime fallback boundary without either (a) calling the
off-serving contemplation producer — which the task's hard constraints forbid —
or (b) fabricating a result, which the "do not invent one" clause forbids. So the
wiring is stopped here and the gap is documented for review.

## 2. The boundary that wiring would target

The smallest legal fallback boundary in the serving turn is the
**universal-disclosure fallback**: the point where the turn has decided it cannot
ground the input and falls back to the "I don't know" disclosure. That is exactly
the *missing-information* condition a served ASK is meant to convert into a
question.

- Surface constant: `chat/runtime.py:172`
  `_UNKNOWN_DOMAIN_SURFACE = "I don't know — insufficient grounding for that yet."`
- Main-path fallback assignment: `chat/runtime.py:2582`
  (`response_surface = _UNKNOWN_DOMAIN_SURFACE`), `selected_source = "universal_disclosure"` at `:2586`.
- Cold/stub-path fallback assignment: `chat/runtime.py:2060`, `:2295`.
- Final surface finalize (post-governance) before the `TurnEvent` is built:
  `shape_surface(...)` at `chat/runtime.py:2746`, `TurnEvent(...)` at `:2753`.

A wiring would call, at that fallback (post-`shape_surface`, pre-`TurnEvent`):

```python
response_surface = maybe_apply_served_ask(self.config, response_surface, provider=<provider>)
```

Under default config (`ask_serving_enabled` absent/False) this is a pure no-op —
`acquire_served_ask_candidate` never calls the provider while the gate is dark.
The unresolved part is **`<provider>`**: what lawfully produces the candidate.

## 3. Producer / consumer topology (why no lawful provider exists)

```mermaid
graph LR
  subgraph OFF-SERVING (growth organ)
    CT["generate.contemplation.contemplate<br/>(pass_manager.py)"] -->|ContemplationResult<br/>terminal=QUESTION_NEEDED<br/>question_path=teaching/questions/*| ART[(teaching/questions/ artifact)]
    RUN["core/contemplation/runner.py::run_contemplation<br/>(offline loop)"] --> CT
  end
  subgraph SERVING TURN (chat/runtime.py)
    TURN["ChatRuntime.chat()"] --> FB["_UNKNOWN_DOMAIN_SURFACE fallback"]
    FB -. "needs a ContemplationResult here" .-> GAP{{"no in-turn producer<br/>and no carried artifact handle"}}
  end
  ADAPTER["chat.ask_runtime.maybe_apply_served_ask<br/>→ acquire_served_ask_candidate<br/>→ evaluate_served_ask"]
  GAP -. consumes .-> ADAPTER
  ART -. "not carried into the turn" .-> GAP
```

**The consumer side is fully built and merged:**

- `core/epistemic_disclosure/ask_serving.py::evaluate_served_ask` — validates the
  Q1-D `DeliveredQuestion` artifact off a `ContemplationResult` and returns a
  `ServedAskDecision` (#677).
- `core/epistemic_disclosure/ask_acquisition.py::acquire_served_ask_candidate` —
  gate-first seam that accepts either a `contemplation_result` or a
  `ContemplationProvider` callable (#678).
- `chat/ask_runtime.py::maybe_apply_served_ask` — runtime-facing helper that
  returns the served surface or the unchanged fallback (#681).

**The producer side is off-serving by construction:**

- The only code that produces a `ContemplationResult` with
  `terminal == QUESTION_NEEDED` and a `question_path` is
  `generate/contemplation/pass_manager.py` (`contemplate(...)`, ASK delivery at
  `_handle_ask_delivery`, lines ~103–121).
- Its package docstring (`generate/contemplation/__init__.py`) declares it
  explicitly off-serving:
  > "Contemplation v0 (N6) — a single bounded read -> classify -> terminal ->
  > maybe-emit pass. Off-serving growth organ ... **No loops, no daemon, no L10
  > runtime, no self-modification.**"
- Its only non-test caller is the offline loop `core/contemplation/runner.py::run_contemplation` — not the serving turn.

**No plumbing connects the two.** Confirmed by source sweep:

- `chat/runtime.py` has **zero** references to `pass_manager`,
  `ComprehensionAttempt`, `ContemplationResult`, `QUESTION_NEEDED`, `Terminal`,
  `question_path`, `proposal_path`, `deliver_ask`, or `DeliveredQuestion`.
  (Its `contemplation`/`discourse_contemplation` symbols are the unrelated
  `teaching.contemplation` discovery/plan path, producing `ContemplationFinding`,
  not a `QUESTION_NEEDED` `ContemplationResult`.)
- The only ASK reference anywhere under `chat/` is `chat/ask_runtime.py` itself.
- `tests/test_ask_serving_integration.py` states the position in its own header:
  > "These tests intentionally avoid `chat.runtime`. This slice is adapter-only:
  > [it does not] wire runtime acquisition of `ContemplationResult`."

## 4. Why neither escape is lawful under the constraints

| Way to get a candidate at the boundary | Verdict |
| --- | --- |
| Runtime calls `generate.contemplation.contemplate` / `pass_manager` per turn | **Forbidden** — "Do not call pass_manager directly from runtime"; also it is an off-serving organ ("no L10 runtime"), so calling it in the serving turn contradicts its design. |
| Runtime calls `deliver_ask` / `render_question` to build a question in-turn | **Forbidden** — "Do not import/call render_question"; also re-renders prose the serving layer must only consume. |
| Add an instance hook (`self._served_ask_provider = None`) that only a test populates with a `DummyResult` | **Inventing one.** No production code path would ever set it. The required test "runtime returns artifact text" would then prove only that a back-door hook is reachable from a fabricated double — *decoration, not proof* (CLAUDE.md, "Schema-Defined Proof Obligations"). |
| Read an already-written `teaching/questions/` artifact from the turn | **No lawful handle.** `evaluate_served_ask` consumes a `ContemplationResult` object (it reads `question_path` off it); nothing keys an off-serving artifact to the current turn, and scanning the sink would be new, unspecified acquisition logic — not "wiring an existing helper." |

Because every route is either forbidden or an invention, the required test
*"gate enabled + valid QUESTION_NEEDED artifact: runtime path returns artifact
question text"* **cannot be satisfied honestly through the serving turn today.**
That is the precise blocker.

## 5. What is genuinely missing (the lawful next slice)

A real, load-bearing boundary needs an **in-turn acquisition path that does not
call the off-serving producer**. Options, for review:

1. **Carried-handle acquisition (recommended).** Define a serving-safe lookup
   that, given the turn's already-computed limitation/assessment, resolves a
   pre-delivered `teaching/questions/` artifact into a `ContemplationResult`-shaped
   handle — *reading* an existing off-serving artifact, never producing one. This
   gives `maybe_apply_served_ask` a lawful `provider` whose source exists in
   production. It is a new acquisition seam (its own reviewed PR), not a one-line
   runtime hook.
2. **Explicit producer→serving plumbing.** A separate slice that runs the
   off-serving contemplation pass out-of-band and persists a turn-addressable
   handle the serving turn can resolve. Larger; needs its own ADR and trust
   boundary (it bridges the off-serving organ to serving).

Either way, the runtime wiring is a *follow-on* to one of these — not this PR.

## 6. What was (and was not) changed here

- **Changed:** this document only.
- **Not changed:** `chat/runtime.py`, the public `chat(...)` signature,
  `ChatResponse`, `TurnEvent`, telemetry schema, `Q1B_ASK_CARVE_OUT`,
  `proposal_allowed`, VERIFIED serving, `CLAIMS.md`, metrics. No call to
  `pass_manager` or `render_question` was added.
- **Base state:** branch is cut from `main@32f8c2ff`; the focused ASK suite was
  green (434/434) earlier this session at that commit, and no edits were made to
  any code under test.
