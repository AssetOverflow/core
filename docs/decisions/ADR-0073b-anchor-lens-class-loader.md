# ADR-0073b — Anchor lens class + loader (Plan Phase L1.2)

**Status:** Accepted
**Date:** 2026-05-19
**Ratified:** 2026-05-19
**Author:** Shay
**Phase:** Plan Phase L1.2 (pack class + loader + unanchored sentinel, no consumer)
**Parent:** [ADR-0073](./ADR-0073-anchor-lens-substrate.md) (umbrella anchor-lens architecture)
**Builds on:** [ADR-0073a](./ADR-0073a-anchor-lens-content-phase.md) (substrate content)
**Pattern:** mirrors ADR-0068 (register pack class) for the substantive-axis sibling

---

## Context

ADR-0073a closed the content gap: the distinction-bearing lemmas
and their distinguishing `logos.<family>.<variant>` atoms exist on
disk across `grc_logos_cognition_v1` and `he_core_cognition_v1`,
with alignment.jsonl edges binding them.

L1.2 introduces the **architectural class** that will later (L1.3)
pivot the composer on those atoms.  At L1.2 no composer consumes the
lens — the class, loader, sentinel pack, and runtime threading
land first.  This isolates the architectural plumbing from the
composer behavioural change exactly the way R1 (ADR-0068) isolated
the register class from R2's realizer wiring.

The load-bearing L1.2 claim is **null-lift**: every existing test +
lane runs byte-identical whether `RuntimeConfig.anchor_lens_id` is
`None` or `"default_unanchored_v1"`.  If null-lift holds, every
caller that does not opt in is provably unaffected by L1.2.

---

## Decision

### `AnchorLens` frozen dataclass

```python
@dataclass(frozen=True)
class AnchorLens:
    lens_id: str
    version: str
    description: str
    display_name: str
    primary_substrate: str             # "grc" | "he" | "en" | "none"
    semantic_domain_preferences: tuple[str, ...]
                                       # ordered atoms; left-most wins at L1.3
    cognitive_mode_label: str          # English compound phrasing label,
                                       # e.g. "experiential" / "systematic"
    mastery_report_sha256: str = ""

    def is_unanchored(self) -> bool: ...
    def is_null_lens(self) -> bool:    # no atoms, "none" substrate, empty label
    @classmethod
    def unanchored(cls) -> "AnchorLens": ...
```

* **`primary_substrate`** is the language whose distinction families
  the lens privileges at composer time.  `"none"` is the L1.2
  null-lens value.
* **`semantic_domain_preferences`** is an ordered tuple of atoms.
  L1.3 composers iterate left-to-right and pick the first lemma
  whose `semantic_domains` includes an atom matching a preferred
  prefix.  Empty tuple ⇒ no preference ⇒ existing English-default
  composer behaviour.
* **`cognitive_mode_label`** is the English compound phrasing
  fragment composers will weave into surfaces at L1.3
  (`"knowing-as-{label}"`).  Empty for the null lens.

The sentinel `AnchorLens.unanchored()` is structurally identical to
the null lens `default_unanchored_v1` — exactly the
register-pack-class pattern.  A module-level `UNANCHORED` constant
is exposed so composers can use it as a keyword-only default
without re-evaluating the classmethod on every call.

### Loader contract

`packs/anchor_lens/loader.py` mirrors `packs/register/loader.py`:

* Reads `packs/anchor_lens/<lens_id>.json`.
* Schema-validates the envelope (required fields, `schema_version`,
  `lens_id` matches filename).
* Bounds-checks `primary_substrate` (∈ `{"grc","he","en","none"}`),
  `semantic_domain_preferences` (list of ≤ 64-char strings, at most
  64 atoms), `cognitive_mode_label` (≤ 64-char string).
* Verifies companion `.mastery_report.json` self-seal +
  `report_sha256` match when `require_ratified=True` (default;
  bypassed by `CORE_ALLOW_UNRATIFIED_ANCHOR_LENS=1` for development).
* Returns a frozen `AnchorLens`.

Trust boundary identical to register pack:
* Pack-id sanitisation via `core._safe_display.safe_pack_id`.
* Path traversal rejected before filesystem access.
* No dynamic imports, no shell passthrough.
* Loader never mutates a pack on disk; pack creation goes through
  `scripts/ratify_anchor_lens_packs.py`.

### `default_unanchored_v1` ratified pack

The L1.2 deliverable on disk:

```json
{
  "lens_id": "default_unanchored_v1",
  "version": "1.0.0",
  "schema_version": "1.0.0",
  "description": "Default unanchored lens. Null primary_substrate,
   empty preferences, empty mode label. Ratification gate is
   byte-identity with the in-memory UNANCHORED sentinel.",
  "display_name": "Default unanchored",
  "primary_substrate": "none",
  "semantic_domain_preferences": [],
  "cognitive_mode_label": "",
  "mastery_report_sha256": "<self-sealed>"
}
```

Ratification method: `byte_identity_null_lift` — the same gate
register's `default_neutral_v1` uses.

### Runtime threading

`core/config.py` gains:

```python
@dataclass(frozen=True)
class RuntimeConfig:
    ...
    anchor_lens_id: str | None = None
```

`chat/runtime.py` loads the lens at `__init__` and stores it on the
runtime exactly the way it loads the register pack:

```python
if resolved_config.anchor_lens_id is None:
    self.anchor_lens: AnchorLens = AnchorLens.unanchored()
else:
    self.anchor_lens = load_anchor_lens(resolved_config.anchor_lens_id)
self.anchor_lens_id = resolved_config.anchor_lens_id
```

**No composer consumes `self.anchor_lens` at L1.2.**  It sits next to
`self.register_pack` until L1.3 wires it into
`chat/pack_grounding.py`.

### Architectural seam

`tests/test_anchor_lens_pack_seam.py` mirrors the register seam
test:

> Truth-path modules MUST NOT import `packs.anchor_lens` at L1.2.

Specifically the proposition-graph / trace-hash / propagation /
vault / algebra modules stay anchor-lens-free.  When L1.3 lands and
composers start consuming the lens, the seam widens to include the
composer files (mirroring how register's seam was widened at R2);
truth-path purity remains absolute.

### Invariants pinned at L1.2

```
anchor_lens_byte_identity_null_lift (NEW):
  Full public cognition lane runs byte-identical for both
  `anchor_lens_id=None` and `anchor_lens_id="default_unanchored_v1"`.
  Surface, grounding_source, trace_hash — all byte-for-byte equal.

anchor_lens_seam (NEW):
  AST-level test refuses any new import of `packs.anchor_lens` from
  truth-path modules.  Fails the moment anchor lens leaks upstream
  of the realizer.

register-tour, register_invariant_grounding, seeded_variation
  invariants (R5 → R1 chain): unchanged.  L1.2 does not touch
  register, identity, safety, or ethics layers.
```

---

## Files

```
packs/anchor_lens/__init__.py                                   NEW
packs/anchor_lens/loader.py                                     NEW
packs/anchor_lens/default_unanchored_v1.json                    NEW
packs/anchor_lens/default_unanchored_v1.mastery_report.json     NEW

scripts/ratify_anchor_lens_packs.py                             NEW

core/config.py                                                  EDIT
  - RuntimeConfig.anchor_lens_id: str | None = None

chat/runtime.py                                                 EDIT
  - Load lens at __init__, store on self.anchor_lens / .anchor_lens_id.
  - No composer wiring (deferred to L1.3).

tests/test_anchor_lens_pack_loader.py                           NEW
tests/test_anchor_lens_null_lift.py                             NEW
tests/test_anchor_lens_pack_seam.py                             NEW

docs/decisions/ADR-0073b-anchor-lens-class-loader.md            NEW (this file)
```

---

## Consequences

### Capability unlocked at L1.2

None directly visible to users.  L1.2 is pure architectural
plumbing — the lens loads, the runtime exposes it, the seam is
guarded, the sentinel is ratified.  Capability arrives at L1.3 when
composers start consuming it.

### Cognition lane

Byte-identical under both `None` and `default_unanchored_v1`.  The
`anchor_lens_byte_identity_null_lift` test pins this in CI.  Any
future change that breaks null-lift fails the lane the moment it
lands.

### Backwards compatibility

* `RuntimeConfig.anchor_lens_id` defaults to `None` — pre-L1.2
  callers stay byte-identical.
* `ChatRuntime.anchor_lens` is a new attribute; no public API
  consumes it yet.
* No telemetry field added at L1.2 (that's L1.4).
* No CLI flag added at L1.2 (that's L1.4).

### Performance

One additional JSON read at `ChatRuntime.__init__` when
`anchor_lens_id` is set.  Zero per-turn overhead because nothing
consumes the lens.

### Trust boundaries

Identical to the register pack class (ADR-0068, ADR-0051
hardening):

* Pack-id sanitisation through `safe_pack_id`.
* Path traversal rejected.
* No dynamic imports.
* Ratification verifier mirrors `verify_register_pack_seal` exactly.
* Loader is read-only; mutation only through the ratify script.

### What L1.2 deliberately does NOT do

* No composer consumption (L1.3).
* No telemetry field on TurnEvent / ChatResponse (L1.4).
* No `core chat --anchor-lens` CLI flag (L1.4).
* No demo (L1.4).
* No anchor-lens-tour assertions (L1.4).

These deferrals keep the L1.2 diff to plumbing + tests — exactly
the inside-out cadence ADR-0068 used.

---

## Verification

```
python -m pytest tests/test_anchor_lens_pack_loader.py -q     N passed
python -m pytest tests/test_anchor_lens_null_lift.py -q       N passed
python -m pytest tests/test_anchor_lens_pack_seam.py -q       N passed
python -m core.cli test --suite full -q                        2632+ passed
python -m core.cli eval cognition                              public byte-identical
core demo register-tour                                        exit 0 (R5 still holds)
```

Cognition eval byte-identity under both `None` and
`default_unanchored_v1` is the canonical L1.2 gate.
