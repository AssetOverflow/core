# ADR-0017 — Agency Scope: Responsive-with-Axiology

**Status:** Accepted
**Date:** 2026-05-16
**Authors:** Joshua Shay
**Supersedes:** Open Scope Decisions row "Agency (responsive vs. goal-directed)"
in `docs/PROGRESS.md`.

## Context

The capability roadmap (ADR-0016) flagged *agency* as an open scope
decision required before Phase 3 engineering begins.  Two extreme
positions are available:

- **Pure responsive.**  The system processes one input per turn and
  produces one output.  No internal aims, no autonomous initiative.
  This is what `CognitiveTurnPipeline.run(text)` is today.
- **Pure agentic.**  The system maintains internal goals, plans
  trajectories that pursue those goals across many turns, and may
  initiate actions outside of user-triggered input.  Each goal-step
  can in principle invoke the system without external prompting.

A choice between these endpoints shapes how Phase 3 reasoning-depth
work is structured.  The transitive-walk and path-recall operators
the inference-closure lane requires can be implemented either way,
but their semantics differ: the agentic reading makes them part of
an internal planner that runs across turns; the responsive reading
makes them per-turn deterministic functions invoked by the
articulator.

## Decision

CORE is **responsive-with-axiology**:

1. **Responsive turn boundary preserved.**  Every cognitive turn is
   triggered by an external input: a user utterance, a CLI invocation,
   or an explicit replay command.  The system never initiates a turn
   autonomously.  No background agent loop runs between turns.

2. **Axiology is first-class within the turn.**  The
   `IdentityManifold` and its `ValueAxis` set are not decorative
   identity-decoration; they are the value gradient against which
   the articulator chooses among candidate articulation surfaces.
   When the proposition-graph planner produces multiple valid
   completions, the choice is the one that scores highest against
   the manifold's value axes.  This is goal-directedness *within* a
   single responsive turn, not across turns.

3. **No autonomous initiative.**  The system has no `loop()` or
   `pursue(goal)` entry point.  Anything that looks like long-horizon
   pursuit is a sequence of responsive turns chained by the calling
   layer, not an internal process.

4. **Replay determinism is the load-bearing constraint.**  The
   responsive-with-axiology shape is preserved partly because pure
   agentic loops break deterministic replay: the trace_hash contract
   in `core/cognition/trace.py` assumes a turn is a deterministic
   function of (input, prior-state).  Adding non-input-triggered
   internal actions would put state changes between turns that
   replay cannot reconstruct.

## Consequences

- **Phase 3 v2 engineering shape.**  The transitive-walk and path-
  recall operators (Gap 1 and Gap 2 in
  `evals/inference_closure/gaps.md`) are **per-turn deterministic
  functions**, not background processes.  They are invoked
  synchronously by the articulator during a single turn.  No turn-
  spanning planner is required to close the Phase 3 inference-depth
  lanes.

- **IdentityManifold axes become load-bearing.**  Today the axes are
  partially decorative (the empirical investigation in commit
  `86ef117` showed `identity_score.alignment = 1.0` universally
  because no candidate-selection step actually consults them).
  Under this ADR, the next refinement of articulator candidate
  selection should consult the axes.  This is also the
  load-bearing path to making fix #3 of the adversarial-identity
  defense work geometrically.

- **No goal-stack data structure.**  CORE will not gain a
  `Goal`, `Plan`, or `Pursuit` typed object as part of Phase 3.
  Anything that looks like a multi-step goal is the user explicitly
  asking for multiple responsive turns.

- **Self-explanation remains responsive.**  The forthcoming
  `core/cognition/explain.py` module (Gap 3 in
  `evals/introspection/gaps.md`) is invoked on a turn-id; it does
  not introspect autonomously.

- **Persona / character work is axiology-side, not agency-side.**
  `persona/motor.py` shapes articulation output within the
  responsive turn.  It does not run between turns.

## Rejected alternatives

- **Pure responsive (no axiology).**  Rejected because the
  `IdentityManifold` already exists as an architectural commitment
  (ADR-0010) and the adversarial-identity defense work explicitly
  depends on axes being able to *shape* behaviour, not just be
  measured.  Pure responsive would relegate identity to read-only
  evidence, which conflicts with ADR-0010's "identity is
  inalienable" claim.

- **Pure agentic.**  Rejected because it breaks the deterministic
  replay contract.  CORE's value proposition over frontier models is
  partly that any turn can be replayed bit-for-bit; an autonomous
  inter-turn process makes that contract unenforceable.  Also
  rejected on philosophical grounds: agency as autonomous pursuit
  is not what CORE claims to be.  CORE is a deterministic cognitive
  engine, not an autonomous agent.

## Verification

- Phase 3 v2 work on Gaps 1+2 is scoped as per-turn deterministic
  operators (see ADR-0018).
- No new turn-spanning processes are introduced in Phase 3.
- Replay determinism contracts in `tests/test_determinism_proofs.py`
  continue to pass for all multi-turn scenarios.
