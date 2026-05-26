# CORE Workbench — Visualization Doctrine

Workbench visuals must make cognition more legible. They must not become AI
theater.

## Standard

A visualization belongs in CORE Workbench only if it answers at least one of:

- What changed?
- What caused the change?
- What evidence supports the result?
- Can this be replayed?
- Did any trust boundary move?
- Where did the system refuse, accept, reject, or defer?

If a visualization cannot answer one of those questions, it does not belong in
v1.

## Approved visual classes

### 1. Trace Graph

Purpose: show a turn's evidence and surface lineage.

Nodes may include:

- prompt
- proposition surface
- articulation surface
- walk evidence
- replay digest
- proposal reference
- eval result

Edges must represent real references or deterministic derivations. No invented
"thinking graph" edges.

### 2. Replay Comparison

Purpose: show original vs replay equivalence.

Allowed displays:

- original hash vs replay hash
- divergence count
- divergence severity
- surface comparison
- metric comparison

No animation should imply proof. Only digest/metric agreement is proof.

### 3. Eval Sparkline / Metric Trend

Purpose: show eval quality over stored results.

Allowed displays:

- pass rate over time
- failure count over time
- trace-hash stability over time
- contemplation-quality score over time

The chart must link to the underlying result artifact.

### 4. Runtime Physics Visualization

Purpose: expose mechanically grounded runtime dynamics.

Allowed only when backed by real telemetry:

- field magnitude over a turn
- admissibility rejection count
- stabilization/convergence curve
- candidate distance ranking
- salience/inhibition scalar overlays

Forbidden:

- fake neuron animations
- decorative particles
- made-up vector fields
- non-grounded "energy" visuals

### 5. Proposal Lifecycle Timeline

Purpose: make proposal authority boundaries explicit.

Allowed states:

- candidate discovered
- proposal emitted
- replay checked
- pending review
- accepted/rejected/withdrawn
- corpus appended if accepted

The timeline must visually distinguish proposal from ratification.

## Motion rules

Motion is allowed only for:

- panel expansion
- replay comparison transition
- graph node focus
- loading state for a real request

Motion is forbidden for:

- simulated cognition
- fake reasoning streams
- decorative particles
- hidden background work

## Color rules

Color communicates operational state only:

- replay pass/fail
- mutation state
- proposal state
- refusal state
- revision warning
- eval severity

No ornamental color palettes detached from meaning.

## Chart rules

Charts must:

- show source artifact id or digest
- have stable scales when comparing runs
- avoid smoothing unless explicitly labeled
- avoid implying causality from correlation
- keep raw values inspectable

## Futuristic but truthful

The target aesthetic is futuristic because the architecture is inspectable and
replay-native, not because the UI pretends to be alive.

The workbench should feel like a cognition instrument panel:

- elegant
- exact
- responsive
- quiet
- deep

not a sci-fi hallucination screen.
