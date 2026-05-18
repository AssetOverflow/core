# ADR-0039: Audit Completeness — `TurnVerdicts` Bundle, Stub-Path `TurnEvent`, `hedge_injected` Signal

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`ADR-0035-turn-loop-verdict-surfacing.md`](ADR-0035-turn-loop-verdict-surfacing.md), [`ADR-0036-safety-refusal-policy.md`](ADR-0036-safety-refusal-policy.md), [`ADR-0037-per-predicate-ethics-refusal.md`](ADR-0037-per-predicate-ethics-refusal.md), [`ADR-0038-hedge-injection.md`](ADR-0038-hedge-injection.md)

## Context

After ADR-0035 → ADR-0038, the runtime emits three verdicts per turn
(identity / safety / ethics) and two possible remediations (typed
refusal, hedge injection).  But auditing it had three rough edges:

1. **Per-field correlation.**  An audit consumer had to read three
   separate fields (`identity_score`, `safety_verdict`,
   `ethics_verdict`) and *infer* the remediation by inspecting the
   surface text (does it start with the refusal prefix?  with the
   hedge phrase?).  Surface-text inference is brittle.
2. **Stub-path TurnEvent gap.**  Stub turns (cold start, unknown
   domain) bypassed `turn_log.append()`.  ADR-0035 already noted
   this as a known limit.  The result: audit consumers reading the
   turn stream couldn't see stub turns at all, even though stub turns
   *did* carry a `ChatResponse.safety_verdict` and
   `ChatResponse.ethics_verdict`.
3. **`hedge_injected` invisibility.**  Whether the runtime actually
   prepended a hedge this turn could only be detected by surface
   inspection (does it start with `preferred_hedge_soft`?).  An
   audit consumer wanting "count hedged turns this hour" had to
   re-implement runtime decision logic.

The three rough edges share a root cause: the runtime knew the
answers but didn't *surface* them in a form callers could read.

## Decision

Three changes land together.  Each is small; together they close the
audit gap.

### 1. `TurnVerdicts` bundle type

A new frozen dataclass in `chat/verdicts.py`:

```python
@dataclass(frozen=True, slots=True)
class TurnVerdicts:
    identity_score: object       # IdentityScore | None
    safety_verdict: object       # SafetyVerdict | None
    ethics_verdict: object       # EthicsVerdict | None
    refusal_emitted: bool        # ADR-0036 / ADR-0037
    hedge_injected: bool         # ADR-0038
```

Fields are typed `object` for the same reason `TurnEvent.safety_verdict`
was: avoid coupling `chat/verdicts.py` to packs.* at module-resolution
time.  Audit consumers downcast at use site.

The bundle is attached to both `ChatResponse.verdicts` and
`TurnEvent.verdicts`.  The pre-existing individual fields
(`safety_verdict`, `ethics_verdict`) remain — back-compat with
ADR-0035 callers — but new consumers should read the bundle.

### 2. Stub-path `TurnEvent` emission

`_stub_response` now accepts an optional `tokens` kwarg.  When invoked
from a real turn (with `tokens` non-empty), it constructs and appends
a `TurnEvent` to `turn_log` before returning the `ChatResponse`.

The stub event records:

| Field | Value |
|---|---|
| `turn` | `self._context.turn - 1` (after `finalize_turn` already ran) |
| `input_tokens` | tokens passed in |
| `surface` | typed refusal if it fired, else the unknown-domain marker |
| `walk_surface` | unknown-domain marker (preserved) |
| `articulation_surface` | unknown-domain marker (preserved) |
| `identity_score` | `None` (no trajectory ran) |
| `cycle_cost_total` | `0.0` |
| `vault_hits` | `0` |
| `versor_condition` | `versor_condition(field_state.F)` |
| `flagged` | `False` |
| `safety_verdict` / `ethics_verdict` / `verdicts` | computed verdicts |

The `correct()` fallback path still calls `_stub_response` without
tokens — that's a defensive call where no real "turn" happened, and
appending a `TurnEvent` would mis-record the audit stream.

### 3. `hedge_injected` signal

The main turn path tracks whether the runtime actually mutated the
surface during hedge injection:

```python
before = response_surface
response_surface = inject_hedge(response_surface, hedge_prefix)
hedge_injected = response_surface != before
```

`inject_hedge()` is idempotent on prefix (ADR-0038) — if the surface
already begins with the hedge phrase, the function returns it
unchanged and `hedge_injected` stays `False`.  This is the correct
audit semantic: "did the runtime ADD a hedge this turn?", not "is
there a hedge somewhere in the surface?"

Stub paths always report `hedge_injected=False` (ADR-0038 prohibits
hedge on stub).

## Consequences

### Positive

* **One field, full picture.**  An audit consumer reads
  `response.verdicts` (or `event.verdicts`) and gets identity +
  safety + ethics + remediation flags.  No correlation across fields.
* **Surface-inspection no longer needed.**  `refusal_emitted` and
  `hedge_injected` answer the runtime-decision questions directly.
* **Stub turns are now first-class audit events.**  `turn_log` now
  covers the entire turn stream; downstream telemetry and replay
  systems can iterate over `turn_log` without missing stub paths.
* **Mutual exclusion is verifiable.**  Existing test
  (`test_refusal_and_hedge_never_both_true`) confirms the runtime
  contract holds at the bundle level.
* **No back-compat breakage.**  ADR-0035 / ADR-0036 / ADR-0037 /
  ADR-0038 individual fields and helpers still work.

### Negative / risks

* **Stub turns now have `identity_score=None` in the audit stream.**
  Downstream consumers that assumed every TurnEvent carried an
  IdentityScore need to handle `None`.  Mitigated: this was already
  true on `ChatResponse.identity_score` for stub paths; consumers
  reading the stream just had no stream entries at all before, and
  now they have entries with `identity_score=None`.  The change is
  additive.
* **The bundle duplicates per-field state.**  `safety_verdict` is
  reachable as both `response.safety_verdict` and
  `response.verdicts.safety_verdict`.  Acceptable cost for
  back-compat; a future ADR could remove the per-field accessors if
  no in-tree consumer still uses them.
* **`hedge_injected` doesn't distinguish "would have fired but
  idempotent" from "didn't fire at all."**  Two distinct cases
  collapse to `hedge_injected=False`.  Audit consumers wanting that
  distinction can read the ethics_verdict directly.
* **Hedge-injection test gate updated.**  The pre-ADR-0039 gate
  ("skip if `turn_log` empty") no longer discriminates stub vs main
  path; the test updated to gate on `walk_surface ==
  _UNKNOWN_DOMAIN_SURFACE` instead.  No semantic change.

## Verification

* `tests/test_turn_verdicts_bundle.py` — 16 tests covering: bundle
  shape and frozen contract; `ChatResponse` and `TurnEvent` carry
  the bundle; stub path appends a `TurnEvent` with input tokens,
  unknown walk/articulation surfaces, `identity_score=None`,
  recorded versor condition; `refusal_emitted` flag toggles on
  forced safety violation, appears symmetrically on
  `ChatResponse.verdicts` and `TurnEvent.verdicts`; `hedge_injected`
  flag defaults False, stays False on stub paths even with opt-in;
  mutual exclusion (refusal supersedes hedge); response and event
  bundles agree on remediation flags and reference the same
  underlying verdicts.
* Combined pack-layer suite: **170 tests, all green** (was 154 after
  ADR-0038).
* CLI suites unchanged: smoke 67, runtime 19, cognition 121.
* `core eval cognition`: intent 100%, versor_closure 100% — baseline
  preserved.

## Open questions deferred to a future ADR

1. **Structured-logging sink that consumes `turn_log`.**  Now that
   stub turns participate in the stream, a structured emitter could
   produce one log line per turn with `pack_id`, `refusal_emitted`,
   `hedge_injected`, and violated boundary ids.
2. **`core chat --show-verdicts` CLI flag.**  Print per-turn verdict
   bundle summaries to stdout/stderr for manual audit.
3. **Drop per-field accessors after a deprecation cycle.**
   `response.safety_verdict` could become `response.verdicts.safety_verdict`-only
   once internal callers migrate.
4. **`identity_score` on stub turns.**  Today stub paths skip the
   trajectory operator entirely and report `None`.  A future ADR
   could compute a degenerate-but-valid IdentityScore for stubs so
   the audit stream is fully populated.
5. **Bundle versioning.**  As more remediation tiers land (per-domain
   default policies, score-decomposition surfaces), the bundle may
   grow.  Frozen-dataclass + optional defaults should scale fine,
   but a `schema_version` field could be added if downstream consumers
   need explicit versioning.
