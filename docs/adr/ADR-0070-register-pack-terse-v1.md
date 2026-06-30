# ADR-0070 — Second ratified register pack: `terse_v1` (Plan Phase R3)

**Status:** Accepted
**Date:** 2026-05-19
**Ratified:** 2026-05-19
**Author:** Shay
**Phase:** Plan Phase R3 (first non-neutral register)
**Builds on:** ADR-0068 (register pack class), ADR-0069 (realizer register parameter)

---

## Context

ADR-0068 landed the register pack class and ratified `default_neutral_v1`
(the null register). ADR-0069 wired a `RegisterPack` parameter through
every realizer-side composer and pinned three byte-identity invariants
(A/B/C) so the cognition lane is provably unchanged under the
unregistered sentinel and the null pack.

R3 is the first ADR where surface output is *allowed* to differ. The
load-bearing question this phase answers is:

> Can a non-neutral register produce visibly different surfaces while
> the **grounding source** (vault / pack / teaching / none) and the
> **trace hash** remain invariant for every prompt in the cognition
> lane?

If yes, we have proven that register is genuinely a property of the
realizer, not the truth path. If no, the seam leaks and R3 reverts.

R3 ships a single concrete knob (`disclosure_domain_count`), the
minimum surface area needed to make the answer testable.

---

## Decision

Ratify a second register pack, `terse_v1`, with one non-default
`realizer_overrides` key: `disclosure_domain_count = 1`. Widen the
without-gloss disclosure path in `chat/pack_grounding.py` to consult
this override. Pin a new CI invariant —
`register_invariant_grounding` — across every cognition lane case.

### The new pack

```json
{
  "register_id": "terse_v1",
  "version": "1.0.0",
  "description": "Terse register. Compresses without-gloss disclosure to one semantic domain. Grounding source and trace hash invariant against default_neutral_v1.",
  "schema_version": "1.0.0",
  "display_name": "Terse",
  "depth_preference": "terse",
  "realizer_overrides": {
    "disclosure_domain_count": 1
  },
  "discourse_markers": {
    "openings": [],
    "transitions": [],
    "closings": []
  }
}
```

`discourse_markers` stay empty — discourse-marker insertion is R4's
job. `depth_preference` is the operator-facing label; the
*behavioural* knob is the explicit `realizer_overrides` entry. The
loader continues to refuse to load an unratified pack without
`mastery_report_sha256` and the companion self-sealed report.

### The R3 ratification gate

The R1/R2 gate (`scripts/ratify_register_packs.py`) refused any pack
that was not structurally null (empty `realizer_overrides`, empty
`discourse_markers`). R3 widens the gate to:

```
1. Accept non-null realizer_overrides, but only known keys.
2. The set of known keys at R3 is exactly:
     - disclosure_domain_count: int in {1, 2, 3}
3. Reject any unknown key with the offending key name in the error.
4. Discourse markers must remain empty at R3 (R4 widens this).
5. The self-seal procedure is unchanged from R1.
```

The "known keys" allow-list is the trust boundary against arbitrary
operator-authored data driving realizer dispatch. R4 widens the
allow-list explicitly per ADR.

### The composer change

Exactly one site changes — the without-gloss disclosure in
`build_pack_surface_candidate` in `chat/pack_grounding.py`:

```python
# Today (ADR-0048):
head = "; ".join(domains[:3])

# At R3:
n = register.realizer_overrides.get("disclosure_domain_count", 3)
head = "; ".join(domains[:n])
```

The default (`3`) is the pre-R3 behaviour, so the sentinel and
`default_neutral_v1` produce identical surfaces to pre-R3 output
(invariants A and B continue to hold trivially because both registers
have `disclosure_domain_count` either absent or unset).

The `pack_grounded_surface` entry point already threads `register`
through (R2), so no further signature change is needed. The downstream
callers — `build_pack_surface_candidate`'s wrappers in the comparison /
correction / procedure paths — already use `domains[:N]` slices with
their own counts (`:3` and `:2`), and those slices stay at their
existing values for R3. The single knob is `pack_grounded_surface`'s
without-gloss disclosure, deliberately.

### The new invariant

`register_invariant_grounding` joins A/B/C as the load-bearing CI gate
for R3:

```
invariant_register_grounding:
  For every case in the cognition lane (public + holdout),
  grounding_source(case) is identical across:
    - register_pack_id = None
    - register_pack_id = "default_neutral_v1"
    - register_pack_id = "terse_v1"
```

Surface text is allowed to differ between `terse_v1` and the two null
registers (that is the whole point of R3). `grounding_source` is not.
If terse_v1 routes a case to a different grounding source, the seam is
leaking and the merge is blocked.

Invariants A/B/C from ADR-0069 continue to hold without modification —
they only compare the two null registers (None ≡ neutral) and never
involve terse_v1. The terse_v1 path adds the fourth invariant on top.

### Files

```
packs/register/terse_v1.json                                 NEW
packs/register/terse_v1.mastery_report.json                  NEW (generated)
scripts/ratify_register_packs.py                             EDIT
  - Widen R1 null-only gate to "non-null overrides allowed,
    known keys only, discourse_markers must stay empty"
  - Known-key allow-list: {"disclosure_domain_count"} at R3

chat/pack_grounding.py                                       EDIT
  - build_pack_surface_candidate reads
    register.realizer_overrides.get("disclosure_domain_count", 3)
  - Threaded into the without-gloss head construction
  - No other composer site touched

tests/test_register_pack_terse_v1.py                         NEW
  - terse_v1 loads, self-seal verifies, depth_preference == "terse"
  - realizer_overrides == {"disclosure_domain_count": 1}
  - pack_grounded_surface(lemma, register=terse) emits one-domain head
  - pack_grounded_surface(lemma, register=neutral) emits three-domain head
  - Both surfaces carry the same pack-grounded({pack_id}) provenance

tests/test_register_invariant_grounding.py                   NEW
  - Runs the cognition lane three ways
    (None / default_neutral_v1 / terse_v1)
  - Asserts grounding_source identical case-by-case
  - Asserts trace_hash invariant across all three (extends invariant C)
  - Asserts versor closure rate identical across all three

docs/decisions/ADR-0070-register-pack-terse-v1.md            NEW (this file)
```

### Wiring shape

```python
# chat/pack_grounding.py — build_pack_surface_candidate
def build_pack_surface_candidate(
    lemma: str,
    pack_ids: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
    *,
    register: RegisterPack = UNREGISTERED,
) -> PackSurfaceCandidate | None:
    ...
    # without-gloss disclosure path
    n = register.realizer_overrides.get("disclosure_domain_count", 3)
    if not isinstance(n, int) or n < 1 or n > 3:
        # Defensive: ratification gate already enforces this, but
        # the realizer hot path must not crash on malformed data.
        n = 3
    head = "; ".join(domains[:n])
    ...
```

The defensive `1 ≤ n ≤ 3` clamp duplicates the ratification gate's
allow-list. Acceptable belt-and-suspenders because the realizer hot
path is invoked once per turn and a crash here would block the entire
session. The ratification gate stays the authoritative trust boundary;
the clamp is a fail-soft for off-path callers.

---

## Consequences

### Capability unlocked at R3

The first non-neutral register, end-to-end. An operator can now boot
`ChatRuntime` with `RuntimeConfig(register_pack_id="terse_v1")` and
receive measurably shorter without-gloss surfaces while the grounding
source and trace hash are unchanged.

This is what R3 is *for*: prove the seam holds when something
actually moves.

### Cognition lane — split expectation

```
None       :  unchanged from R2 baseline
neutral    :  unchanged from R2 baseline (invariant B)
terse      :  surface_grounded MAY differ; intent / term-capture /
              versor closure MUST match neutral byte-for-byte
              UNLESS surface_grounded depends on disclosure word count
              (it does not — substring tests look for "pack-grounded")
```

The R3 expectation is that terse_v1 lane numbers will equal neutral
lane numbers, because the cognition lane's surface predicates pin
provenance markers (`pack-grounded ({pack_id})`) and lemma presence,
not full disclosure clauses. If a case fails under terse but passes
under neutral, the cognition lane fixture has a latent dependency on
the third disclosure domain — useful debugging signal, but should not
gate R3.

### Test coverage

- `test_register_pack_terse_v1.py` — direct load + composer
  invocation under both registers.
- `test_register_invariant_grounding.py` — the load-bearing artifact.
  Cognition lane × three registers × grounding-source diff.
- Existing tests (`test_register_null_lift.py`, etc.) continue to
  pass without modification because they pair only None and neutral.

### Performance

`register.realizer_overrides.get(key, default)` is a dict lookup per
turn (one composer site). Negligible. The pack is loaded once at
session start and passed by reference.

### Trust boundaries

- **Operator-authored data cannot drive arbitrary realizer
  dispatch.** The ratification gate's known-key allow-list is the
  defence-in-depth: a pack file claiming `realizer_overrides:
  {"exec_python": "..."}` cannot ratify. R4 will widen the allow-list
  with the same gate.
- **Defensive realizer clamp** is fail-soft, not a primary trust
  surface. Removing it would not change correctness — the gate would
  have rejected the pack — but it would change failure mode from
  "shorter disclosure" to "IndexError on next turn." Fail-soft is
  preferable in the realizer hot path.
- **Self-seal still verified.** `verify_register_pack_seal` is
  unchanged; terse_v1 ships with its own
  `terse_v1.mastery_report.json` produced by the ratify script.
- **No new mutation surface.** No runtime write path to
  `packs/register/`. Operator-authored pack files only.
- **Path-traversal protection unchanged.** Pack IDs continue through
  `_validate_pack_id` (ADR-0051).

### Replay determinism

`disclosure_domain_count` is a pack-resident integer. The surface for
a given `(lemma, register_pack_id)` is a deterministic function of
the ratified pack file. Replay against the same packs produces
identical output. Replay against a session that used a different
register produces different surfaces — but the trace hash and
grounding source remain invariant, so the cognition turn is still
fully reproducible from `(input, pack_set, register_pack_id)`.

---

## Verification

```
tests/test_register_pack_terse_v1.py                         N passed
tests/test_register_invariant_grounding.py                   N passed
tests/test_register_pack_seam.py                             unchanged, passes
tests/test_register_runtime_threading.py                     unchanged, passes
tests/test_register_null_lift.py                             unchanged, passes
Curated lanes (must remain green):
  smoke / cognition / teaching / packs / runtime / algebra
Cognition eval:
  register_pack_id=None              == R2 baseline (byte-identical)
  register_pack_id="default_neutral_v1" == None (invariant B)
  register_pack_id="terse_v1"         grounding_source / trace_hash /
                                      versor_closures byte-identical
                                      against neutral; surface MAY differ
                                      on without-gloss disclosure cases
```

The new invariant test is the load-bearing R3 artifact. If it passes,
the seam survives its first stress test.

---

## Trust boundaries (summary)

- Ratification gate widened with explicit known-key allow-list.
- Realizer hot path defends against malformed data via clamp.
- Self-seal verification preserved.
- Path-traversal protection unchanged.
- No new runtime write surface.

---

## Open questions deferred to later phases

- **Per-intent overrides** (e.g. `realizer_overrides:
  {"DEFINITION": {...}, "COMPARISON": {...}}`)? Deferred. R3's flat
  schema is enough to prove the seam; per-intent dispatch is R4
  alongside discourse markers.
- **Should `terse_v1` also compress the comparison surface
  (`contrasts with`) or correction surface?** Deferred. R3 is one
  knob, one composer. Multi-composer override is R4.
- **Should the runtime auto-resolve `register_pack_id=None` to
  `default_neutral_v1`?** Still open from ADR-0069's open
  questions. R3 does not change the answer. Sentinel and pack remain
  structurally equivalent; the resolution question stays deferred to
  R4 or later.

---

## Future ADRs unlocked

- **ADR-0071 (Phase R4)** — seeded surface variation +
  discourse-marker insertion + per-intent realizer overrides.
  `(trace_hash, register, turn_idx) → template_variant`. Widens
  ratification gate further.
- **ADR-0072 (Phase R5)** — telemetry + operator surface.
  `TurnEvent` gains `register_id` and `template_variant_id`. `core
  chat --register <id>` flag. `core demo register-tour`.
