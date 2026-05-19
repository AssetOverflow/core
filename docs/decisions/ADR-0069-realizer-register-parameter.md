# ADR-0069 — Realizer register parameter (Plan Phase R2)

**Status:** Accepted (amended 2026-05-19)
**Date:** 2026-05-19
**Ratified:** 2026-05-19
**Amended:** 2026-05-19 — composer parameter defaults to `RegisterPack.unregistered()`; runtime-threading lint test replaces the "required keyword-only" rule. See *Amendment* section.
**Author:** Shay
**Phase:** Plan Phase R2 (presentation-axis wiring)
**Builds on:** ADR-0068 (register pack class)

---

## Context

ADR-0068 landed the register pack class — frozen dataclass, loader,
ratification script, `default_neutral_v1` null register, and an
architectural seam test asserting that no upstream module imports
`packs.register`. At R1 the realizer is untouched and the seam is
machine-enforced.

R2 is the first wiring step. Two questions the ADR answers:

1. **Where does the register enter the runtime?** At realizer call
   time — *after* intent classification, propagation, grounding-source
   selection, chain resolution, and articulation-target construction.
   Never earlier.
2. **What happens when register is consumed but the pack is null?**
   Byte-identical output to the unregistered path. This is the
   load-bearing CI gate for R2.

R2 ships *plumbing only*. No composer changes its template choice. No
discourse marker is inserted. The realizer entry points learn to
accept a register parameter; the runtime learns to load and pass it;
the gate asserts that doing so changes nothing. R3 is where the first
non-neutral register starts consuming overrides.

This phasing matters because it lets us prove the seam against the
trace-hash and grounding-source invariants *before* any visible
behaviour change rides on top.

---

## Decision

Widen the realizer call signature to accept a `RegisterPack` parameter
and thread it through every surface composer entry point in
`chat/runtime.py`. Add `RuntimeConfig.register_pack_id: str | None`,
defaulting to `None`. Pin three byte-identity invariants in CI.

### The three byte-identity invariants

R2 ships only if all three hold across the full cognition lane
(public + holdout splits):

```
invariant_A:  register_pack_id=None
              ≡ pre-R2 unregistered output  (byte-for-byte)

invariant_B:  register_pack_id="default_neutral_v1"
              ≡ register_pack_id=None       (byte-for-byte)

invariant_C:  trace_hash(turn) is invariant under register_pack_id
              for every turn in the cognition lane
```

Invariant A proves R2 is a no-op for existing callers. Invariant B
proves the null register is structurally equivalent to "no register."
Invariant C proves register cannot leak into the truth path.

### Files

```
chat/runtime.py                                              EDIT
  - RuntimeConfig gains register_pack_id: str | None = None
  - ChatRuntime.__init__ loads the register pack (or unregistered sentinel)
  - Every realizer call site passes the register through

generate/realizer.py                                         EDIT
  - Public entry points accept register: RegisterPack parameter
  - At R2, register is accepted and discarded (no-op consumption)

generate/templates.py                                        UNCHANGED
  (R3 will start dispatching on register.realizer_overrides;
   R2 leaves templates alone)

chat/pack_grounded_*.py / chat/teaching_grounding.py /       EDIT (parameter only)
chat/cross_pack_grounding.py / chat/narrative_surface.py /
chat/example_surface.py
  - Accept register parameter; do not consume it at R2

tests/test_register_pack_seam.py                             REPLACE
  - R1 version asserted no upstream module imports packs.register;
    R2 narrows the forbidden list (see "Updated seam" below)

tests/test_register_null_lift.py                             NEW
  - Pins invariants A, B, C across the cognition lane

tests/test_runtime_config_register.py                        NEW
  - RuntimeConfig field shape; load behaviour; invalid id rejection

docs/decisions/ADR-0069-realizer-register-parameter.md       NEW (this file)
```

### Wiring shape

```python
# RuntimeConfig (chat/runtime.py)
@dataclass(frozen=True)
class RuntimeConfig:
    ...
    register_pack_id: str | None = None  # NEW (ADR-0069)


# ChatRuntime.__init__
class ChatRuntime:
    def __init__(self, config: RuntimeConfig, ...):
        ...
        if config.register_pack_id is None:
            self._register = RegisterPack.unregistered()
        else:
            self._register = load_register_pack(config.register_pack_id)


# Realizer entry point
def realize_surface(
    target: ArticulationTarget,
    *,
    register: RegisterPack,
) -> str:
    # R2: register is accepted, validated, discarded.
    # R3: register.realizer_overrides[target.intent] selects template family.
    ...
```

### Composer signature widening

Every existing surface composer that the runtime calls — pack-grounded,
teaching-grounded, cross-pack, narrative, example, composed,
correction, procedure — gains a `register: RegisterPack` keyword-only
parameter. At R2 the parameter is required (no default) so call sites
fail loudly if they forget to thread it through. The composer body is
unchanged.

Default arguments are avoided deliberately: silent fall-through to
`RegisterPack.unregistered()` would let R3 sites quietly skip the
register lookup. Required keyword-only parameter forces explicit
threading.

### Updated seam

The R1 seam test forbade `packs.register` imports in every upstream
module. R2 replaces it with a narrowed forbidden list:

```
Still forbidden at R2 (truth-path modules):
  core/cognition/trace.py
  core/cognition/pipeline.py
  core/cognition/result.py
  generate/graph_planner.py
  generate/intent.py
  field/propagate.py
  vault/store.py
  algebra/versor.py

Allowed at R2 (realizer side):
  generate/realizer.py
  generate/templates.py
  chat/runtime.py
  chat/pack_grounded_*.py
  chat/teaching_grounding.py
  chat/cross_pack_grounding.py
  chat/narrative_surface.py
  chat/example_surface.py
```

The structural commitment from R1 is preserved: register is consumed
at realizer call time only. Trace, pipeline, intent classification,
propagation, vault recall, and algebra remain free of register
imports.

### Where the register pack loads

`ChatRuntime.__init__` loads it once and stores it on the instance.
Per-turn lookup is not needed — `RuntimeConfig` is frozen and the
register pack is content-addressed and immutable after load. Reloading
per turn would be wasted work and would obscure the "register is
session-scoped" mental model.

When `register_pack_id` is `None`, the sentinel
`RegisterPack.unregistered()` is used. This is structurally identical
to `default_neutral_v1` (both null registers) and the invariant-B test
proves it.

---

## Consequences

### Capability unlocked at R2

None visible at runtime. R2 lands the wiring and the byte-identity
gate. Capability unlocks at R3 (second ratified register pack).

### Cognition lane — byte-identical

Required and CI-pinned by `test_register_null_lift.py`:

```
public:  intent 100% / surface 100% / term 91.7% / closure 100%
holdout: intent 100% / surface 100% / term 83.3% / closure 100%
```

must hold post-merge across all three invariants (`None`,
`default_neutral_v1`, unregistered sentinel).

### Test coverage

- `test_register_null_lift.py` — runs the cognition lane three ways
  and asserts surfaces are byte-identical pairwise. Also asserts
  `grounding_source` and `trace_hash` are invariant across registers.
- `test_runtime_config_register.py` — `RuntimeConfig.register_pack_id`
  default is `None`; invalid id raises `RegisterPackError` at runtime
  init; `default_neutral_v1` loads cleanly.
- `test_register_pack_seam.py` (replaces R1 version) — narrowed
  forbidden list; loader-side import constraints unchanged.

### Performance

Negligible. One pack load on `ChatRuntime.__init__`; the loaded pack
is a frozen dataclass passed by reference per turn. No new allocations
in the hot path.

---

## Trust boundaries

- **Register cannot mutate truth.** Realizer is the *only* consumer.
  `grounding_source`, chain resolution, trace hash, and proposition
  graph are computed before realizer is called. Invariant C
  CI-enforces this.
- **Required keyword-only parameter.** No composer accepts a default
  register; missing it raises `TypeError` at call time. This catches
  R3 wiring mistakes early.
- **Load-time validation.** Invalid `register_pack_id` raises
  `RegisterPackError` at `ChatRuntime.__init__`, not at first turn.
  Fail-fast on session start.
- **No mutation surface.** ADR-0068 doctrine preserved: register packs
  are operator-authored and ratified through
  `scripts/ratify_register_packs.py`. R2 adds no runtime write path to
  `packs/register/`.
- **Telemetry stays redact-safe.** R2 does not extend `TurnEvent`.
  Adding `register_id` to telemetry is an R5 task (ADR-0072) — out of
  scope here.

---

## Verification

```
tests/test_register_null_lift.py                             N passed
tests/test_runtime_config_register.py                        N passed
tests/test_register_pack_seam.py                             updated, N passed
Curated lanes (must remain green):
  smoke / cognition / teaching / packs / runtime / algebra
Cognition eval byte-identical across:
  register_pack_id=None
  register_pack_id="default_neutral_v1"
Full lane: zero new failures.
```

The invariant-A/B/C test is the load-bearing artifact. If it lands and
passes, R2 has shipped its full promise.

---

## Open questions deferred to later phases

- **How do composers consult `realizer_overrides`?** R3 question. R2
  only proves the parameter threads cleanly.
- **Where do discourse markers attach to surfaces?** R4 question.
  Likely a post-composer wrapper that consults
  `register.discourse_markers` and the seeded selection function. Not
  part of R2.
- **Should `RegisterPack.unregistered()` be replaced with the loaded
  `default_neutral_v1` by default?** Open. Two arguments:
  - *Replace*: simpler mental model; one canonical null register.
  - *Keep separate*: sentinel doesn't require disk presence;
    works in minimal/test environments where packs/register/ is
    absent. Lean toward keep-separate; revisit if it causes
    confusion in R3.
- **Should the realizer signature change to accept a richer
  `RealizerContext` object (register + future fields) instead of bare
  `RegisterPack`?** Probably yes by R4, but premature at R2. Deferred.

---

## Amendment (2026-05-19)

The original ADR required composers to take `register` as a **required
keyword-only** parameter, on the principle that defaults would let R3
sites silently fall through to `RegisterPack.unregistered()`. R2
implementation scouting found that rule lands on 167 call sites across
15 test files. Each of those sites calls a composer as a bare function
(e.g. `teaching_grounded_surface("light", IntentTag.CAUSE)`) and would
need a register keyword added.

That cost was not measured in the original ADR. Updated decision:

- **Composers accept `register: RegisterPack = RegisterPack.unregistered()`**
  as a keyword-only argument with a default. Existing test call sites
  remain valid.
- **A new lint test, `test_register_runtime_threading.py`, AST-parses
  `chat/runtime.py`** and asserts that every call to a composer
  function passes `register` explicitly. This is the runtime-side
  enforcement that R3 cannot silently drop the register lookup.
- **The default is the unregistered sentinel, not a loaded pack.** A
  composer called without `register=` from a non-runtime caller (test,
  ad-hoc CLI) defaults to the same in-memory shape that runtime would
  use when `register_pack_id=None`. Byte-identity invariants A/B/C
  still hold trivially because the runtime path always threads
  explicitly.

The seam intent — "R3 cannot quietly skip the register lookup" — is
preserved by the lint test rather than by the function signature. The
trade is: signature-level rigour for blast-radius reduction, with the
seam guarantee re-located one level up.

This amendment supersedes the "Composer signature widening" subsection
above where it conflicts.

---

## Future ADRs unlocked

- **ADR-0070 (Phase R3)** — second ratified register pack. First
  non-neutral register (`terse_v1` candidate). Composers start
  consulting `realizer_overrides`. New CI metric:
  `register_invariant_grounding=True` (grounding source identical
  across registers for every prompt; only surface wording varies).
- **ADR-0071 (Phase R4)** — seeded surface variation.
  `(trace_hash, register, turn_idx) → template_variant`. Discourse
  markers gain bounded variants pulled by deterministic seed.
- **ADR-0072 (Phase R5)** — telemetry + operator surface. TurnEvent
  gains `register_id` and `template_variant_id`. `core chat
  --register <id>` flag. `core demo register-tour`.
