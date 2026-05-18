# ADR-0041: `core chat --show-verdicts` + Sink Fan-Out

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`ADR-0039-audit-completeness.md`](ADR-0039-audit-completeness.md), [`ADR-0040-telemetry-sink.md`](ADR-0040-telemetry-sink.md)

## Context

ADR-0040 landed the machine-facing audit surface: deterministic JSONL
lines on an attached sink.  Two follow-ups were left explicit:

* **Operator-facing readout.**  A human-readable per-turn summary
  printed alongside the chat response so an operator can debug
  refusals/hedges/violations interactively without parsing JSONL.
* **Sink fan-out.**  Today one sink at a time.  Operators often
  want both a durable local file *and* a remote aggregator (or two
  sinks pointing at different log stores) simultaneously.

Both are thin layers on top of the existing surface.  Bundling them
into one ADR keeps the audit story coherent.

## Decision

### `core chat --show-verdicts`

New CLI flag on the `chat` subparser.  When set, after each turn the
REPL prints the verdict bundle summary to **stderr**:

```text
> light is
I don't know — insufficient grounding for that yet.
[identity=- safety=ok ethics=VIOLATED:acknowledge_uncertainty refusal=- hedge=-]
```

Design choices:

* **Summary goes to stderr.**  The chat response goes to stdout
  (unchanged).  Tooling that pipes `core chat` through a filter
  doesn't see verdict noise interleaved with the response; humans
  watching the terminal see both.
* **Format is dense and terse.**  One bracketed line per turn,
  fixed field order: `identity`, `safety`, `ethics`, `refusal`,
  `hedge`.  Designed to skim, not to be machine-parsed (the JSONL
  sink owns that contract).
* **Distinct from the machine-facing JSONL.**  ADR-0040's
  `format_turn_event_jsonl` is for log aggregators; the new
  `format_verdict_summary` is for operators.  Two formatters, one
  underlying bundle — no risk of drift.

### `FanOutSink`

New sink in `chat/telemetry.py`:

```python
@dataclass
class FanOutSink:
    sinks: tuple = ()  # tuple[TurnEventSink, ...]
    def emit(self, line: str) -> None:
        for sink in self.sinks:
            sink.emit(line)
```

* **Fail-fast.**  First sink that raises propagates the exception;
  subsequent sinks are NOT called.  Consistent with ADR-0040's
  single-sink contract: telemetry failures surface visibly, never
  silently drop audit signal.
* **Composable.**  Any combination of sinks (file + buffer,
  multiple files, file + a future remote sink) works.  Order is
  preserved.
* **Stateless.**  No internal buffering; emission is synchronous
  and immediate to each child sink.

A `ResilientSink` wrapper (swallows errors per-sink) is intentionally
**not** included.  Callers who want partial-success semantics wrap
individual sinks in their own error-tolerant shim.  The default
contract should reflect the doctrine "audit failures are visible";
the resilient wrapper is its own future ADR if needed at scale.

### `format_verdict_summary` formatter

New pure function in `chat/telemetry.py`:

```python
def format_verdict_summary(verdicts) -> str: ...
```

* Returns `""` for `None` input.
* Pulls fields off the bundle using `getattr` with safe defaults —
  same boundary discipline as `serialize_turn_event`.
* Renders identity alignment to two decimals (`identity=0.83`) or
  `identity=-` when no score is available (stub turns).
* Safety / ethics: `ok` when no violations, else
  `VIOLATED:<id1>,<id2>` in lex order.
* Remediation flags: `refusal=YES`/`refusal=-` and `hedge=YES`/`hedge=-`.

## Consequences

### Positive

* **Operator path complete.**  The audit story now reads end-to-end
  for both humans and machines:
  - Per-turn TurnVerdicts bundle (ADR-0039)
  - Machine-facing JSONL sink (ADR-0040)
  - Fan-out across multiple sinks (ADR-0041)
  - Operator-facing CLI summary (ADR-0041)
* **No new core runtime surface.**  Both additions are pure layers
  on top of `ChatResponse.verdicts` and the existing sink protocol.
* **Single source of truth.**  Operator and machine formatters share
  the underlying bundle; no risk of one going stale while the other
  evolves.
* **Composable fan-out.**  Tested end-to-end: runtime attaches a
  `FanOutSink` and gets atomic distribution to file + buffer (or any
  N sinks) without changes to the runtime.

### Negative / risks

* **`format_verdict_summary` format is human-stable, not
  machine-stable.**  Callers should not parse it.  The JSONL sink
  remains the only machine-stable wire format.  Documented in code
  comments but not enforced at the type level.
* **Fan-out is synchronous.**  Slow sinks slow the turn loop.
  Acceptable today (the only sinks are in-memory and local file);
  async / queued sinks are deferred to a future ADR alongside
  backpressure.
* **CLI summary is on stderr.**  Tooling reading stderr separately
  works fine; tooling that merges streams sees the summary
  interleaved.  This is the standard Unix split between content
  and metadata — the tradeoff was accepted to keep stdout clean
  for piped consumers.

## Verification

* `tests/test_telemetry_fanout_and_summary.py` — 13 tests covering:
  fan-out forwarding to all sinks, emission-order preservation,
  empty-sinks no-op, fail-fast on first error (downstream sinks NOT
  called), composition with file sink; runtime-with-fan-out
  end-to-end; verdict summary (None → empty, clean turn, safety
  violation, ethics violation, multiple violations lex-sorted, no
  identity score, real ChatResponse formats without error).
* CLI smoke (manual):
  ```text
  $ echo "light is" | core chat --show-verdicts
  > [identity=- safety=ok ethics=VIOLATED:acknowledge_uncertainty refusal=- hedge=-]
  I don't know — insufficient grounding for that yet.
  ```
  Correct: cold-start stub turn has no identity score; ethics
  flags `acknowledge_uncertainty` because alignment_score=0.0
  falls below `hedge_threshold_soft`; default pack opt-in lists are
  empty so no refusal/hedge fires.
* Combined pack-layer + telemetry suite: **212 tests, all green**
  (was 199 after ADR-0040; +13).
* CLI suites unchanged: smoke 67, runtime 19, cognition 121.
* `core eval cognition`: intent 100%, versor_closure 100% — baseline
  preserved.

## Open questions deferred to a future ADR

1. **Resilient (error-tolerant) sink wrapper.**  Wraps any sink and
   swallows emit-time errors with optional callback.  Sibling to
   `FanOutSink`; lands if real deployments need it.
2. **Async / queued sinks.**  Synchronous fan-out becomes a
   bottleneck when one sink is a slow remote aggregator.  A queued
   wrapper with backpressure semantics is the natural next step.
3. **`--show-verdicts` granularity flags.**  Today the summary is
   a single one-liner.  Operators may want `--verdicts-verbose` for
   per-predicate detail or `--verdicts-only-on-violation` for
   high-volume sessions.
4. **Schema versioning on the JSONL wire format.**  Was deferred
   from ADR-0040.  Now that operators have a stable readout, the
   machine wire format can evolve more aggressively if needed.
5. **Sink registry.**  Today sinks are constructed by the caller.
   A registry that resolves sinks from config strings
   (`"file:/var/log/core/audit.jsonl"`, `"buffer"`) would simplify
   declarative deployment configuration.
