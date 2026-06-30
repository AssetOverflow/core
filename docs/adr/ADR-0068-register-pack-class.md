# ADR-0068 — Register pack class (Plan Phase R1)

**Status:** Accepted
**Date:** 2026-05-19
**Ratified:** 2026-05-19
**Author:** Shay
**Phase:** Plan Phase R1 (presentation-axis foundation)
**Builds on:** ADR-0027 (identity packs) / ADR-0029 (safety pack) / ADR-0033 (ethics pack) / ADR-0048 (pack-grounded surface) / ADR-0062 (composed surface)

---

## Context

CORE's truth path is deterministic by construction: intent classification
→ proposition graph → articulation target → realizer → trace hash. Replay
is bit-exact. The cognition lane is CI-pinned to byte-identity across
flag-off / flag-on for every additive ADR since 0048.

The accepted critique of deterministic systems is not that they are
wrong, but that they can feel *rigid*: same meaning, same wording, same
cadence. A user reads identical surfaces across turns as scripted rather
than thoughtful. The reflexive fix — add sampling to generation — is
forbidden by CLAUDE.md (no stochastic fallback, no hidden normalization,
trace hash must remain stable).

The framing this ADR adopts:

> The problem is not deterministic cognition; the problem is a single
> deterministic rendering channel.

Variation in *how* a resolved answer is rendered does not require
variation in *what* was resolved. Register, cadence, depth, and
discourse-marker choice are orthogonal to the proposition graph,
grounding source, and chain resolution. They belong on a separate axis
— a presentation axis — and that axis can itself be deterministic given
a wider input space.

This ADR introduces the data shape for that axis. It deliberately ships
**no runtime wiring**. The realizer is untouched. The cognition lane
must remain byte-identical after this ADR lands, because nothing
consumes register packs yet.

---

## Decision

Introduce a fourth pack-layer class: **register packs**. Structurally a
sibling to identity / safety / ethics packs (swappable, ratified,
checksum-sealed), but architecturally distinct in *where* they compose:

```
identity ∪ safety ∪ ethics  →  boundary_ids        (manifold-side)
register                    →  realizer parameter  (surface-side)
```

A register pack does not union into the runtime manifold, does not
contribute to `boundary_ids`, does not participate in safety / ethics
verdicts, and does not affect grounding source. It parameterizes
realizer template selection and discourse-marker insertion.

### The load-bearing commitment

**Register is a property of the realizer, not the proposition graph.**

The trace hash is computed on the articulation target plus grounding
evidence, *before* register is consulted. Replay equivalence
(`teaching/replay.py`) continues to compare at the articulation-target
level. Two surfaces that differ only in register render from the same
target, the same grounding source, the same chain set, and the same
trace hash.

If this seam slips — if register ever influences which chain resolves,
which grounding source is selected, or which proposition admits — the
invariant is gone. Tests in this ADR pin the seam.

### Files

```
packs/register/                                               NEW
packs/register/__init__.py                                    NEW
packs/register/loader.py                                      NEW (mirrors packs/identity/loader.py)
packs/register/default_neutral_v1.json                        NEW
packs/register/default_neutral_v1.mastery_report.json         NEW (self-seal)
scripts/ratify_register_packs.py                              NEW (idempotent)
tests/test_register_pack_loader.py                            NEW
tests/test_register_pack_seam.py                              NEW
docs/decisions/ADR-0068-register-pack-class.md                NEW (this file)
```

The loader lives at `packs/register/loader.py` (sibling to
`packs/identity/loader.py`, `packs/safety/loader.py`,
`packs/ethics/loader.py`), not under `core/packs/`. This matches the
existing pack-layer convention.

No changes to `generate/realizer.py`, `chat/runtime.py`,
`core/cognition/pipeline.py`, `core/cognition/trace.py`, or any
existing surface composer. Wiring is deferred to ADR-0069 (Phase R2).

### Pack schema

```json
{
  "register_id": "default_neutral_v1",
  "display_name": "Default neutral",
  "description": "Baseline register. Mirrors current realizer output.",
  "depth_preference": "standard",
  "realizer_overrides": {},
  "discourse_markers": {
    "openings": [],
    "transitions": [],
    "closings": []
  },
  "ratified_on": "2026-05-19",
  "checksum": "<sha256 of pack body bytes>"
}
```

Field semantics:

- `register_id` — kebab-case unique id, validated via `_safe_pack_id`
  (ADR-0051 trust-boundary doctrine).
- `depth_preference` — one of `terse` / `standard` / `pedagogical`.
  Consumed by future composed-surface depth modulation (ADR-0062
  generalisation). v1 default packs use `standard`.
- `realizer_overrides` — mapping `intent → template_family_id`. An
  empty mapping means "use the unregistered realizer template" for
  every intent. v1 `default_neutral_v1` ships empty by design — its
  ratification gate is exactly *byte-identity with the unregistered
  path*.
- `discourse_markers` — three bounded lists. v1 ships all empty. R4
  introduces seeded selection from non-empty lists.
- `checksum` — SHA-256 of the JSON body bytes excluding the
  `checksum` field itself, mirroring identity pack mastery-report
  doctrine.

### Mastery report (self-seal)

Each register pack ships a companion `.mastery_report.json`:

```json
{
  "register_id": "default_neutral_v1",
  "ratified_on": "2026-05-19",
  "ratification_method": "byte_identity_null_lift",
  "evidence": {
    "cognition_lane_byte_identical": true,
    "discourse_markers_empty": true,
    "realizer_overrides_empty": true
  },
  "checksum": "<sha256 of pack body>",
  "report_checksum": "<sha256 of this report body excluding report_checksum>"
}
```

The loader verifies the pack checksum and the mastery report checksum
in production mode (same gate as identity packs, ADR-0027).

### Loader contract

```python
# core/packs/register.py
def load_register_pack(register_id: str) -> RegisterPack: ...
def list_available_register_packs() -> tuple[str, ...]: ...
def verify_register_pack_seal(register_id: str) -> bool: ...
```

`load_register_pack(None)` returns an explicit sentinel `RegisterPack.unregistered()`
— frozen, empty, never serialised to disk. This is what the realizer
will consume when `RuntimeConfig.register_pack_id is None` (R2). The
sentinel is structurally identical to `default_neutral_v1`'s in-memory
form; the two paths are required by test to render byte-identically
once R2 wires them.

### v1 ratified pack

`default_neutral_v1` is the **null-register baseline**. It is the
register whose surfaces match the current unregistered output exactly.
Its ratification evidence is the byte-identity check, not eval-lift
numbers. This pack exists so that:

1. The pack class has at least one ratified member at R1 close.
2. The R2 wiring has an explicit "loaded but no-op" target to test
   against (vs. the `None` sentinel path).
3. Non-neutral registers in R3 have a structural baseline to diff
   against during ratification.

No second register ships in this ADR. `terse_v1` is the R3 work.

### Ratification script

`scripts/ratify_register_packs.py` mirrors
`scripts/ratify_identity_packs.py`:

- Reads pack JSON, normalises field ordering, computes checksum.
- Writes back the pack with `checksum` populated.
- Generates the `.mastery_report.json` with `ratification_method`,
  `evidence` block, and `report_checksum`.
- Idempotent: re-running produces byte-identical files.

---

## Consequences

### Capability unlocked at R1

None visible at runtime. R1 lands the data shape and the loader.
Capability unlocks at R2 (realizer parameterization), R3 (second
ratified register pack), R4 (seeded selection), R5 (telemetry +
demo).

### Cognition lane — byte-identical

Required and CI-pinned. Nothing in this ADR consumes register packs at
runtime, so:

```
public:  intent 100% / surface 100% / term 91.7% / closure 100%
holdout: intent 100% / surface 100% / term 83.3% / closure 100%
```

must hold post-merge, exactly as pre-merge.

### Test coverage

- `test_register_pack_loader.py` — load / list / verify-seal /
  unregistered-sentinel structural identity / ratification idempotence
  / invalid `register_id` rejection / missing mastery report rejection
  in production mode / checksum mismatch rejection.
- `test_register_pack_seam.py` — pin the architectural commitment.
  Imports `core/cognition/trace.py`, `generate/realizer.py`,
  `chat/runtime.py`, and asserts none of them import
  `core/packs/register.py`. This test fails the moment register
  leaks upstream of the realizer. Removed in R2 and replaced with a
  narrower seam test once the realizer legitimately imports the
  loader.

---

## Trust boundaries

- **Register cannot mutate truth.** Loader returns a frozen dataclass;
  no setter, no in-place mutation. Realizer (R2) receives it by value.
- **`register_id` is path-sanitised.** `_safe_pack_id` from
  `core/_safe_display.py` (ADR-0051) rejects traversal and unsafe
  ids before filesystem access.
- **Checksum-sealed.** Pack body and mastery report are both
  SHA-256-sealed; production loader verifies both.
- **No new mutation surface.** Register packs are operator-authored
  and ratified through `scripts/ratify_register_packs.py`. There is no
  runtime path that writes to `packs/register/`. ADR-0057 doctrine
  (corpus mutation only through `accept_proposal` or
  `supersede_chain`) is unrelated — register packs are not corpora.
- **Manifold isolation.** Register packs do not contribute to
  `boundary_ids`. Safety / ethics / identity composition is unchanged.
  A separate test asserts `compose_boundary_ids` ignores any register
  pack id passed in.
- **Trace hash unchanged.** Test asserts the trace hash of a turn is
  invariant under `RuntimeConfig.register_pack_id` once R2 lands; for
  R1, asserts the trace-hash codepath has no import of the register
  loader.

---

## Verification

```
tests/test_register_pack_loader.py                           N passed
tests/test_register_pack_seam.py                             N passed
scripts/ratify_register_packs.py                             idempotent
Curated lanes (must remain green):
  smoke / cognition / teaching / packs / runtime / algebra
Cognition eval byte-identical (public + holdout).
Full lane: zero new failures.
```

The ratification script must produce byte-identical output on a second
run (idempotence gate). The mastery report `evidence` block must
include `cognition_lane_byte_identical: true` — verified by running
`core eval cognition` with no runtime change and confirming pre/post
output equality.

---

## Open questions deferred to later phases

- **Where exactly does `register_pack_id` live in `RuntimeConfig`?**
  R2 question. R1 only requires the loader to exist.
- **How does composition work when a register pack and a domain
  ethics pack both want to soften a refusal?** Out of scope. Refusal
  remediation is a manifold-side concern (ADR-0036 / ADR-0037 /
  ADR-0038). Register is surface-side only. They cannot collide
  because they operate on different fields of `ChatResponse`.
- **Can register affect `grounding_source`?** No, by construction.
  Grounding source is computed before realizer is invoked. A test in
  R2 will pin this; in R1 the seam test is sufficient.
- **Do CORRECTION (ADR-0060) and PROCEDURE (ADR-0061) templates
  factor cleanly for register overrides?** Open R2 question. May
  require template refactor before `terse_v1` can ratify in R3.
- **Auto-detect user's preferred register from phrasing?** Separate
  cognitive task (intent classification extension). Deferred — needs
  its own ADR, not bundled here.

---

## Future ADRs unlocked

- **ADR-0069 (Phase R2)** — realizer parameterization. Widen
  `generate/realizer.py` to accept `(target, register=None) → surface`.
  Add `RuntimeConfig.register_pack_id`. CI-pin null-lift invariant:
  `register_pack_id=None` ≡ `register_pack_id="default_neutral_v1"` ≡
  current unregistered output, byte-for-byte.
- **ADR-0070 (Phase R3)** — second ratified register pack
  (`terse_v1` candidate). First non-neutral register. Ratification
  gate: cognition lane passes on both registers; new metric
  `register_invariant_grounding=True` (grounding source identical
  across registers for every prompt).
- **ADR-0071 (Phase R4)** — seeded surface variation.
  `(trace_hash, register, turn_idx) → template_variant_within_family`.
  Discourse markers and template families gain bounded variants.
  Replay still bit-exact given the same seed inputs.
- **ADR-0072 (Phase R5)** — telemetry + operator surface.
  TurnEvent gains `register_id` and `template_variant_id`.
  `core chat --register <id>` flag. `core demo register-tour` —
  three-scene demo: identical grounding evidence, three surfaces.
