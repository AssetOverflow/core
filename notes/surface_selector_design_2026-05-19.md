# SurfaceSelector Design — Deferred RFC

**Date:** 2026-05-19
**Status:** Design proposal — NOT implemented.  Deferred from the
2026-05-19 fluency push because the refactor crosses too many files
to land safely solo.  Picks up cleanly when the reviewer is back.
**Seed type:** `chat/pack_surface_candidate.py::PackSurfaceCandidate`
(landed in commit 46ac737 — already shaped for selector consumption)

## Motivation

The 2026-05-19 design review identified the central architectural
fault behind the fluency bug class:

> **Surface authority fragmentation.**  The runtime, pipeline, walk
> evidence, pack fallback, telemetry, hash, and several composers all
> compete for the user-facing sentence.  The system can be "green"
> while user-facing selection, pipeline selection, and telemetry
> selection disagree.

Phase B1's pipeline-override usefulness gate (commit `c3e2a22`) cured
two symptoms:

- `no_placeholder_rate`: 0.44 → 1.00
- `telemetry_consistency_rate`: 0.44 → 1.00

But it did not cure the third:

- `warm_grounding_stability`: 0.0 (warmed lane)

The warmed-session bug — a pack-grounded surface on turn 1 reverting
to a vault-walk fragment on turn 2 of the same prompt — is the
remaining symptom.  Its fix is structural, not patchable: pack-
grounding must fire by intent + lemma residency, not by vault gate
state.  This is the SurfaceSelector's job.

## Proposed design

### One typed candidate per provider

```python
@dataclass(frozen=True, slots=True)
class SurfaceCandidate:
    surface: str                    # final user-facing string
    grounding_source: str           # "refusal"/"teaching"/"pack"/...
    provider_id: str                # which provider emitted this
    rank_hint: int                  # provider's own confidence tier
    pack_id: str | None             # provenance (None for refusal/OOV)
    intent: IntentTag
    subject_lemma: str | None
    semantic_domains: tuple[str, ...]  # audit content
    epistemic_status: str           # "asserted"/"hedged"/"refused"/...
    is_user_facing_safe: bool
    is_fluent_sentence: bool
    is_replayable: bool
```

`PackSurfaceCandidate` (already landed) is a structural subset of
this — the migration is a strict superset rename + a few new fields.

### Providers

Each provider has one job: produce a candidate (or None) for the
given intent + subject.  No selection logic; no telemetry; no
side effects beyond the candidate's audit fields.

```
RefusalProvider          → refusal candidates (safety/ethics)
TeachingChainProvider    → reviewed-corpus chain candidates
CrossPackChainProvider   → cross-pack chain candidates
PackGlossProvider        → reviewed gloss sentences
PackDomainProvider       → dotted-domain disclosure
OOVInvitationProvider    → "I haven't learned X yet"
VaultRecallProvider      → vault-grounded candidates (when warranted)
ArticulationProvider     → realizer/walk fallback (lowest rank)
```

Today these all live as branches in
`chat/runtime.py::_maybe_pack_grounded_surface()` and parallel
dispatchers.  The selector collapses them into a registered list.

### Selection

```python
def select(candidates: Sequence[SurfaceCandidate],
           context: SelectionContext) -> SurfaceCandidate | None:
    """One pure function over the candidate list.

    Returns the highest-ranked candidate where:
      - is_user_facing_safe is True
      - the candidate's intent matches context.intent
      - the candidate respects context.constraints (e.g. cold_start
        suppresses VaultRecallProvider on turn 1)

    Ordering:
      refusal > teaching > pack_gloss > pack_domain > oov > vault > walk

    Within the same grounding_source rank, prefer
    is_fluent_sentence=True.
    """
```

### Single emission point

```python
def chat(self, text: str, ...) -> ChatResponse:
    ...
    candidates = self._collect_candidates(intent, subject, field_state)
    chosen = self._selector.select(candidates, context)
    # one emission point: telemetry, hash, ChatResponse all
    # built from the same `chosen` object.
    self._emit_turn_event(chosen, ...)
    return ChatResponse(surface=chosen.surface, ..., chosen=chosen)
```

The pipeline either consumes the runtime's chosen candidate or
becomes a provider itself.  Either way, there is exactly one
selector, one emission point, one trace-hash input.

## What gets fixed by this

| Symptom | Fixed how |
|---|---|
| Warm-grounding instability | `_collect_candidates` queries `PackGlossProvider`/`PackDomainProvider` by intent + lemma residency, independent of vault gate state.  Turn N>1 produces the same candidate set as turn 1 for the same prompt. |
| Telemetry / hash drift | Single emission point.  No second-pass override path exists. |
| `chat/runtime.py::_maybe_pack_grounded_surface` dispatcher pile | Decomposes into one provider per surface family.  Adding a new surface kind = adding a new provider, not editing the dispatcher. |
| Pipeline-vs-runtime fragmentation | Pipeline either consumes the runtime selection or registers itself as a provider; in both cases the user-facing selection happens exactly once. |
| Spine fragmentation (separate RFC) | `core chat` / `core trace` / cognition eval / pulse all call into the same selector entry point. |

## What does NOT get fixed by this

- Gloss content coverage (handled by Phase C)
- Intent classification gaps (handled by `b52e04a`)
- Pipeline placeholder prose (already cured by `c3e2a22` — selector
  enforces the same `_is_useful_surface` check as a candidate filter)
- Subjective fluency (out of scope — selector doesn't author content)

## Migration shape

1. Create `chat/surface_selector.py` with `SurfaceCandidate`,
   `SurfaceProvider` protocol, and `SurfaceSelector.select()`.
2. Add a `SurfaceCandidate.from_pack_surface_candidate()` adapter so
   the existing `chat/pack_surface_candidate.py::PackSurfaceCandidate`
   becomes a SurfaceCandidate via 1-line conversion.
3. Wrap each existing dispatcher branch in
   `_maybe_pack_grounded_surface()` as a provider.  No behaviour
   change yet — each provider emits the same surface its branch
   used to emit.
4. Replace `_maybe_pack_grounded_surface()` with
   `selector.select(_collect_candidates(...))`.  Behaviour-preserving
   if the selector's ordering matches the dispatcher's order.
5. Move the pipeline's override path through the selector.
6. Add `core chat` / `core trace` integration paths.

Each step is a separate commit, each ends green, each is independently
revertable.  None requires authoring new content.

## Testing approach

- `warmed_session_consistency` already pins the lift target.
  `warm_grounding_stability` going from 0.0 to 1.0 is the regression
  signal for the selector landing.
- `deterministic_fluency` continues to pin the structural floor.
- New `tests/test_surface_selector.py` for the selector itself:
  ordering invariants, candidate-set determinism, single-emission
  invariant (only one TurnEvent emitted per chat call).

## Risk register

- **Pipeline integration** — touches `core/cognition/pipeline.py`.
  Mitigation: the pipeline override gate (`c3e2a22`) already filters
  unuseful surfaces, so the selector's job is mostly to consume the
  runtime's chosen candidate.  Pipeline-specific override semantics
  may be expressible as a single ordered provider.
- **Trace hash drift** — selector emits one hash; pipeline's
  separate hash path goes away.  Old test fixtures with frozen
  hashes (`tests/test_cognitive_turn_pipeline.py:119-123`) compare
  run-to-run, not against stored values, so this is safe.
- **OOV / refusal precedence** — already encoded by the ordering
  rank.  The current dispatcher's order is preserved by spec.

## When to land

Best landed by the engineer who wrote the 2026-05-19 design review
(they have the cleanest model of the call sites that need migration).
Solo-landable when warmed-session work is the next architectural
priority.  Not for accidental work — this refactor crosses too many
files to reverse cheaply.
