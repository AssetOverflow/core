# ADR-0071 — Seeded surface variation + discourse markers (Plan Phase R4)

**Status:** Accepted
**Date:** 2026-05-19
**Ratified:** 2026-05-19
**Author:** Shay
**Phase:** Plan Phase R4 (deterministic surface variation)
**Builds on:** ADR-0068 (register pack class), ADR-0069 (realizer
register parameter), ADR-0070 (`terse_v1` + `realizer_overrides`)

---

## Context

ADR-0070 proved a non-neutral register can vary surface text while
grounding source and trace hash stay invariant. That register
(`terse_v1`) varies *depth* — one knob, one composer site, one
deterministic change per turn given the same input.

R4 is where the system gains genuine *output variation across turns*
without losing replay equivalence. The load-bearing question is:

> Can a single register produce different surfaces on repeat invocations
> while remaining bit-for-bit reproducible from
> `(input, pack_set, register_pack_id, turn_idx)`?

The original-question framing (the deterministic-AI "canned response"
critique) bottoms out here. A user who asks the same question twice
should not get verbatim-identical text — but the system must still be
fully reproducible. The mechanism is *seeded* variation: the variation
is a deterministic function of inputs the user does not control but the
system commits to.

R4 ships three things:

1. A deterministic seed derived from `(trace_hash, register_id,
   turn_idx)` that selects from bounded discourse-marker buckets.
2. A second non-neutral register pack — `convivial_v1` — that exercises
   the marker buckets end-to-end. (`terse_v1` keeps its empty markers;
   the R3 invariants over it still hold.)
3. A schema widening for `realizer_overrides` to support a `per_intent`
   nested key, so future R5+ work can dispatch per intent without
   another schema change.

---

## Decision

Introduce `chat/register_variation.py` as the single deterministic-seed
surface to which the runtime delegates post-composer decoration. Widen
the ratify gate to allow non-empty discourse markers and `per_intent`
overrides. Add the `convivial_v1` register pack. Pin a new
load-bearing invariant — `seeded_variation_replay_equivalence` —
across the cognition lane.

### The seed

```python
# chat/register_variation.py
def _select_bucket_entry(
    bucket: tuple[str, ...],
    *,
    trace_hash: str,
    register_id: str,
    turn_idx: int,
    bucket_name: str,
) -> str:
    """Deterministically pick one entry from *bucket*, or '' if empty.

    Seed is one-way: it READS trace_hash but NEVER feeds back into it.
    Pinned by ADR-0069 invariant C and ADR-0070 register_invariant_grounding.
    """
    if not bucket:
        return ""
    seed_bytes = (
        f"{trace_hash}|{register_id}|{turn_idx}|{bucket_name}"
    ).encode("utf-8")
    digest = hashlib.sha256(seed_bytes).digest()
    idx = int.from_bytes(digest[:8], "big") % len(bucket)
    return bucket[idx]
```

The choice of inputs is load-bearing:

- `trace_hash` — couples variation to the truth path so two semantically
  different turns under the same register never collide on the same
  marker by accident. **One-way coupling**: trace_hash is read here but
  *cannot* feed back into itself (it has already been computed and
  sealed by the time the realizer is called).
- `register_id` — different registers under the same trace_hash pick
  different markers. Switching registers mid-session produces visibly
  different surfaces even on byte-identical truth content.
- `turn_idx` — same prompt twice in one session does NOT produce
  byte-identical surface, because turn_idx increments. Replay against
  the same `(input_sequence, register, packs)` does, because turn_idx
  is part of the inputs.
- `bucket_name` — `"openings"`, `"transitions"`, `"closings"` use
  different seeds so e.g. opening and closing don't always correlate.

### Decoration shape

```python
def decorate_surface(
    surface: str,
    register: RegisterPack,
    *,
    trace_hash: str,
    turn_idx: int,
) -> str:
    """Apply seeded discourse-marker decoration to *surface*.

    Always returns at minimum the original surface (empty buckets ⇒
    no-op).  Order is opening + ' ' + surface + closing, with the
    closing concatenated directly so a marker like ' — does that help?'
    can attach without a separator.
    """
    opening = _select_bucket_entry(
        register.discourse_markers.openings,
        trace_hash=trace_hash, register_id=register.register_id,
        turn_idx=turn_idx, bucket_name="openings",
    )
    closing = _select_bucket_entry(
        register.discourse_markers.closings,
        trace_hash=trace_hash, register_id=register.register_id,
        turn_idx=turn_idx, bucket_name="closings",
    )
    out = surface
    if opening:
        out = f"{opening} {out}"
    if closing:
        out = f"{out}{closing}"
    return out
```

Transitions are **deferred to a later phase**. Clause-boundary
detection is realizer-internal and tangling it into R4 widens scope
without commensurate evidence. The schema accepts a `transitions`
bucket; R4 reads it and validates it; nothing consumes it yet.

### Per-intent override schema

Open question from ADR-0070 closed: `realizer_overrides` gains an
optional `per_intent` nested key. Flat keys remain valid and apply to
all intents; `per_intent[intent_tag]` overrides them per-intent.

```json
{
  "realizer_overrides": {
    "disclosure_domain_count": 3,
    "per_intent": {
      "DEFINITION": {"disclosure_domain_count": 1},
      "COMPARISON": {"disclosure_domain_count": 2}
    }
  }
}
```

The composer resolves overrides as `per_intent[current_intent] >> flat
>> default`. R4 wires this through `_resolve_disclosure_domain_count`
in `chat/pack_grounding.py` (already R3-ready) so the resolution is a
single dispatch.

Per-intent IS NOT exercised by `convivial_v1` (which leans on discourse
markers, not depth). It's wired so R5 packs can opt in without another
schema change.

### The new pack — `convivial_v1`

```json
{
  "register_id": "convivial_v1",
  "version": "1.0.0",
  "description": "Warm, conversational register. Seeded openings and closings draw from small bounded buckets; depth follows the standard (3-domain) default. Variation is deterministic across (trace_hash, register_id, turn_idx). See ADR-0071.",
  "schema_version": "1.0.0",
  "mastery_report_sha256": "",
  "display_name": "Convivial",
  "depth_preference": "standard",
  "realizer_overrides": {},
  "discourse_markers": {
    "openings": ["So,", "Right —", "OK,"],
    "transitions": [],
    "closings": ["", " — does that help?", " — make sense?"]
  }
}
```

The empty-string entry in `closings` is intentional: ~1/3 of turns get
no closing, so the register does not feel mechanically marker-stuffed.
The seed enforces uniformity across the bucket, not a frequency curve.
That is acceptable for R4 — frequency shaping is an R5+ design space.

### Ratify gate widening

`scripts/ratify_register_packs.py`:

1. Known-key allow-list adds `per_intent` (validated as a dict whose
   keys are valid `IntentTag` names and whose values are dicts of
   known flat keys — same allow-list, one nesting level).
2. Discourse markers may now be non-empty. Buckets are validated by
   the loader's existing bounds checks (`_MAX_MARKER_LEN`,
   `_MAX_MARKERS_PER_BUCKET`). The gate adds:
   - At least one of `openings`/`closings` must be non-empty for a pack
     to claim a non-`null` register status (defensive: an "empty"
     non-null pack is just `default_neutral_v1` with extra ratification
     overhead — refuse with a clear message).
   - `transitions` accepted but reported in evidence as
     `transitions_reserved=true`. R4 does not consume them.
3. Ratification method label for marker-using packs:
   `seeded_variation_replay_equivalence`.

### Runtime threading

```python
# chat/runtime.py
class ChatRuntime:
    def chat(self, text: str, ...) -> ChatResponse:
        ...
        # Compute the trace hash (truth path; unchanged from R3).
        result = self._pipeline.run(text, ...)
        # Realize the surface (composers consume register).
        surface = self._maybe_pack_grounded_surface(...)  # or fallback
        # Apply seeded decoration AFTER trace_hash is sealed.
        turn_idx = len(self.turn_log)
        surface = decorate_surface(
            surface,
            self.register_pack,
            trace_hash=result.trace_hash,
            turn_idx=turn_idx,
        )
        ...
```

The decoration call is unconditional but is a no-op when buckets are
empty (sentinel, neutral, terse — every R1/R2/R3 register). The
existing register-aware composer call sites are untouched.

### Files

```
packs/register/convivial_v1.json                             NEW
packs/register/convivial_v1.mastery_report.json              NEW (generated)
scripts/ratify_register_packs.py                             EDIT
  - REGISTER_IDS gains "convivial_v1"
  - Known-key allow-list adds "per_intent" (dict validator)
  - Discourse markers may be non-empty
  - Ratification method label "seeded_variation_replay_equivalence"
    for marker-using packs
  - Evidence dict gains: marker_bucket_sizes,
    per_intent_keys, transitions_reserved

chat/register_variation.py                                   NEW
  - _select_bucket_entry (deterministic seeded selector)
  - decorate_surface (post-composer wrapper)

chat/runtime.py                                              EDIT
  - Import decorate_surface from chat.register_variation
  - Call decorate_surface AFTER pack-grounded composers and AFTER
    trace_hash is sealed, AFTER turn_event construction
  - turn_idx = len(self.turn_log) at call time

chat/pack_grounding.py                                       EDIT
  - _resolve_disclosure_domain_count(register, intent=None)
    consults register.realizer_overrides["per_intent"][intent.name]
    before the flat key
  - Existing callers passing no intent stay safe (flat key only)
  - build_pack_surface_candidate gains optional intent: IntentTag | None

packs/register/loader.py                                     EDIT
  - _validate_overrides accepts a `per_intent` nested dict
    (whitelist key, value-shape validated recursively)

tests/test_register_variation.py                             NEW
  - _select_bucket_entry determinism (same inputs → same output)
  - _select_bucket_entry distribution (across 1000 fake trace hashes,
    every bucket entry is selected at least once → uniform sanity)
  - decorate_surface empty buckets ⇒ no-op
  - decorate_surface neutral + sentinel ⇒ surface unchanged

tests/test_register_pack_convivial_v1.py                     NEW
  - convivial_v1 loads, self-seal verifies
  - Discourse markers populated as declared
  - Repeated ChatRuntime.chat(prompt) across separate sessions ⇒
    identical surfaces (replay equivalence)
  - Same prompt, three turns in one session ⇒ at least one surface
    differs (turn_idx variation is observable)

tests/test_seeded_variation_replay_equivalence.py            NEW
  - Run cognition lane under convivial_v1 in two fresh runtimes
  - Assert per-case surfaces are byte-identical between runs (replay)
  - Assert grounding_source byte-identical between runs
  - Assert trace_hash byte-identical between runs
  - Assert at least one case under convivial differs from neutral
    (variation is actually visible somewhere in the lane)

tests/test_register_invariant_grounding.py                   EDIT
  - Extend to include convivial_v1 alongside terse_v1
  - grounding_source + trace_hash + aggregate metrics still invariant

tests/test_register_runtime_threading.py                     UNCHANGED
  - decorate_surface is post-composer; not on the threaded list

docs/decisions/ADR-0071-seeded-surface-variation.md          NEW (this file)
```

### Invariants pinned in CI at R4

```
invariant_A (ADR-0069):  register_pack_id=None ≡ pre-R2 unregistered
invariant_B (ADR-0069):  None ≡ default_neutral_v1 (byte-identical)
invariant_C (ADR-0069):  trace_hash invariant under register

invariant_register_grounding (ADR-0070):
  grounding_source identical across {None, neutral, terse, convivial}

invariant_seeded_variation_replay (ADR-0071):  NEW
  Two fresh ChatRuntime sessions under the same register, given the
  same input sequence and pack set, produce byte-identical surfaces.

invariant_seeded_variation_turn_distinct (ADR-0071):  NEW
  Same prompt, multiple turns in one session, under a marker-using
  register: at least one turn's surface differs from the others
  (proves the seed actually moves with turn_idx).
```

The two new invariants are the load-bearing R4 artifacts. If they pass,
the deterministic-AI critique is structurally answered.

---

## Consequences

### Capability unlocked at R4

A non-neutral register that produces *visibly different* surfaces
across turns while remaining bit-for-bit reproducible from
`(input_sequence, register_pack_id, pack_set)`. The first end-to-end
demonstration of "deterministic without canned."

### Cognition lane — split expectation

```
None         :  unchanged from R3 baseline
neutral      :  unchanged from R3 baseline (invariants A, B)
terse        :  unchanged from R3 baseline (empty markers, decoration
                is no-op; invariant_register_grounding still holds)
convivial    :  surfaces may differ from neutral on most cases;
                grounding_source / trace_hash / versor_closures /
                intent_correct match neutral byte-for-byte; aggregate
                term_capture_rate and surface_groundedness MAY differ
                (lane assertions are substring-permissive — markers
                don't disrupt the provenance substrings)
```

If the cognition lane's surface predicates fail under `convivial_v1`
because a marker collides with a substring assertion, the ADR-0070
debugging signal applies: the lane fixture has a latent dependency,
not an architectural bug. R4 expectation: lane substring predicates
match through marker decoration because markers attach as prefix/suffix
and the provenance markers (`pack-grounded (X)`) sit mid-surface.

### Performance

One SHA-256 per bucket per turn. Two buckets currently consulted
(`openings`, `closings`). Two `int.from_bytes` + one modulo. Negligible
in the hot path.

### Test coverage

- `test_register_variation.py` — determinism + bucket distribution.
- `test_register_pack_convivial_v1.py` — pack-level integration.
- `test_seeded_variation_replay_equivalence.py` — load-bearing R4
  artifact (replay equivalence across separate sessions).
- `test_register_invariant_grounding.py` — extended to four registers.

### Trust boundaries

- **Seed is one-way.** `trace_hash → marker_selection`; never the
  reverse. The seam test (ADR-0068, narrowed at R2) continues to refuse
  imports of `packs.register` from truth-path modules. Add
  `chat/register_variation.py` to the *allowed-realizer-side* list.
- **Markers are bounded.** Loader bounds (`_MAX_MARKER_LEN`,
  `_MAX_MARKERS_PER_BUCKET`) already enforced at R1. Ratify gate adds
  the additional check that at least one marker bucket be populated
  for a marker-using ratification.
- **Per-intent dispatch is allow-listed.** `per_intent` keys must be
  valid `IntentTag` names (whitelist), values must be dicts of known
  flat keys. Unknown intent names are refused with a clear error.
- **Transitions reserved.** Schema accepts the bucket but R4 does not
  consume it. Operators can ship transition entries; they sit until a
  later phase consumes them. Loader validates bounds; ratify reports
  `transitions_reserved=true` in evidence.
- **No new mutation surface.** No runtime write path to
  `packs/register/`.
- **Replay determinism preserved.** Two runtimes started from the same
  config and given the same input sequence produce identical
  `turn_log`. Pinned by `invariant_seeded_variation_replay`.

### Backwards compatibility

R3-and-earlier registers (`UNREGISTERED`, `default_neutral_v1`,
`terse_v1`) have empty marker buckets, so `decorate_surface` is a no-op
for them. ADR-0069 invariants A/B/C remain byte-identical. ADR-0070
`register_invariant_grounding` continues to hold and is extended to
include `convivial_v1`.

---

## Verification

```
tests/test_register_variation.py                             N passed
tests/test_register_pack_convivial_v1.py                     N passed
tests/test_seeded_variation_replay_equivalence.py            N passed
tests/test_register_invariant_grounding.py                   N passed (extended)
Curated lanes (must remain green):
  smoke / cognition / teaching / packs / runtime / algebra
Cognition eval:
  register_pack_id=None              == R3 baseline (byte-identical)
  register_pack_id="default_neutral_v1" == None (invariant B)
  register_pack_id="terse_v1"         == R3 baseline (empty markers)
  register_pack_id="convivial_v1"     grounding_source / trace_hash /
                                      versor_closures byte-identical
                                      against neutral; surface differs
                                      on marker-decorated cases
Replay-equivalence test:
  Two fresh ChatRuntime sessions under convivial_v1, same prompt
  sequence ⇒ byte-identical surfaces.
```

---

## Open questions deferred to later phases

- **Transition markers.** Schema accepted; not consumed. Needs clause
  boundary detection — realizer-internal — deferred until a concrete
  use case forces the wiring.
- **Frequency shaping.** Current selector is uniform over the bucket.
  Real conversational variation has a frequency curve (closings less
  often than openings, for example). One option: bucket entries weight
  themselves with explicit `count` multipliers. Deferred to R5+ once
  operator-author feedback is available.
- **Multi-pack discourse-marker composition.** A future "personality"
  pack alongside a "register" pack might want to compose markers. Out
  of scope.
- **Should `decorate_surface` short-circuit for non-pack-grounded
  surfaces?** Currently no — it decorates every surface uniformly.
  Open question whether vault-grounded recall surfaces should also be
  decorated. R4 keeps the uniform path; revisit if it causes
  surprising decoration on rote recall.

---

## Future ADRs unlocked

- **ADR-0072 (Phase R5)** — telemetry + operator surface. `TurnEvent`
  gains `register_id` and `template_variant_id` (or the marker-pair
  selected by the seed). `core chat --register <id>` CLI flag.
  `core demo register-tour` walks neutral → terse → convivial on the
  same prompt sequence so the variation is operator-visible.
- **ADR-0073+ (post-R5)** — anchor-lens / Greek-Hebrew substantive
  variation. The presentation axis is now solid enough to compose
  against a true content-axis variation. See
  `[[greek-hebrew-pack-scout-2026-05-19]]`.
