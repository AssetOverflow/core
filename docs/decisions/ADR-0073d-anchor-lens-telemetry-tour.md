# ADR-0073d — Anchor-lens telemetry, CLI, and tour demo (Plan Phase L1.4)

**Status:** Accepted
**Date:** 2026-05-19
**Ratified:** 2026-05-19
**Author:** Shay
**Phase:** Plan Phase L1.4 (operator-visible anchor lens, falsifiable demo)
**Parent:** [ADR-0073](./ADR-0073-anchor-lens-substrate.md) (umbrella)
**Builds on:** [ADR-0073a](./ADR-0073a-anchor-lens-content-phase.md),
[ADR-0073b](./ADR-0073b-anchor-lens-class-loader.md),
[ADR-0073c](./ADR-0073c-anchor-lens-composer-wiring.md)
**Pattern:** mirrors ADR-0072 (register R5 — telemetry + tour demo)

---

## Context

L1.1–L1.3 built the anchor-lens subsystem inside-out: substrate
content (L1.1), pack class + loader (L1.2), composer wiring with
surface lift on cognition lemmas (L1.3).  The lens is loaded,
engages on its intended pack lemmas via the alignment graph, and
appends `[lens(<id>):<mode>]` to the surface when engaged.

L1.4 closes the architectural arc by making the lens
**operator-observable, operator-driven, and demo-falsifiable** —
exactly what R5 did for the register subsystem.  After L1.4 the
substantive axis is feature-complete enough to compose against the
register axis in operator-visible demos and audit pipelines.

The load-bearing claim L1.4 ships is the **opposite** of register-tour's:

```
register-tour    : per prompt, fix lens, vary register → trace_hash CONSTANT
anchor-lens-tour : per prompt, fix register, vary lens → trace_hash DISTINCT
```

Both invariants must continue to hold turn-by-turn.  L1.4 packages
the second one into a falsifiable demo.

---

## Decision

L1.4 ships three artifacts:

1. **Telemetry extension** — `TurnEvent` + `ChatResponse` gain
   `anchor_lens_id` (loaded pack id, empty for UNANCHORED) and
   `anchor_lens_mode_label` (engaged mode label this turn, empty
   when the lens didn't engage on this turn's lemma).
2. **Operator surface** — `core chat --anchor-lens <id>` CLI flag
   wires into `RuntimeConfig.anchor_lens_id`.  Invalid id fails
   fast at `ChatRuntime.__init__` (mirrors `--register`).
3. **Narrative demo** — `core demo anchor-lens-tour` walks a fixed
   2-prompt sequence under {default_unanchored_v1, grc_logos_v1,
   he_logos_v1} and asserts the three load-bearing claims.

### Telemetry — `TurnEvent` shape extension

```python
# core/physics/identity.py
@dataclass(frozen=True)
class TurnEvent:
    ...
    register_id: str = ""
    register_variant_id: str = ""
    # ADR-0073d (L1.4) — operator-visible anchor-lens identity per turn.
    anchor_lens_id: str = ""
    anchor_lens_mode_label: str = ""
```

* `anchor_lens_id`: the loaded pack's `lens_id`, or `""` for the
  in-memory `UNANCHORED` sentinel.  Pre-L1.4 callers stay
  byte-identical (empty string is the default).
* `anchor_lens_mode_label`: the engaged `cognitive_mode_label`
  when the lens fired on this turn's lemma, or `""` when the lens
  was loaded but did not engage (different lemma than its
  alignment scope), or when no lens was loaded at all.

Reading this pair tells operators three things at a glance:

* `(id="", mode="")`              — no lens loaded
* `(id="<x>", mode="")`           — lens loaded, did not engage on this turn
* `(id="<x>", mode="<label>")`    — lens loaded, engaged, surface
                                    carries `[lens(<x>):<label>]`

### Mode-label extraction

The composer (L1.3) embeds the engaged mode label in the surface
string as `[lens(<lens_id>):<mode_label>]`.  At telemetry-build
time, the runtime extracts the mode label by reading that
annotation from the pre-decoration surface.  A small deterministic
parser:

```python
# chat/runtime.py
_ANCHOR_LENS_ANNOTATION_RE = re.compile(
    r"\[lens\(([^):]+)\):([^\]]+)\]"
)

def _extract_anchor_lens_mode_label(surface: str, lens_id: str) -> str:
    """Return the engaged mode_label if surface carries an annotation
    for ``lens_id``, else ``""``.  Pure read; no side effects."""
    if not surface or not lens_id:
        return ""
    for match in _ANCHOR_LENS_ANNOTATION_RE.finditer(surface):
        if match.group(1) == lens_id:
            return match.group(2)
    return ""
```

This keeps L1.4 a **read-only telemetry pass** over the L1.3
surface.  The composer remains the only source of truth for
engagement; the runtime simply mirrors what the composer emitted.

### CLI — `core chat --anchor-lens <id>`

```python
chat.add_argument(
    "--anchor-lens",
    metavar="LENS_ID",
    default=None,
    help=(
        "optional anchor-lens pack id (ADR-0073+); default: no "
        "lens (unanchored sentinel, byte-identical to "
        "default_unanchored_v1).  Examples: default_unanchored_v1, "
        "grc_logos_v1, he_logos_v1.  Invalid ids fail-fast at "
        "runtime init before the REPL starts."
    ),
)
```

Threads into `_runtime_config_from_args` as
`RuntimeConfig(anchor_lens_id=args.anchor_lens)`.  Invalid id ⇒
`AnchorLensError` at `ChatRuntime.__init__` — the CLI catches and
surfaces it as `_die("invalid --anchor-lens pack id: ...", code=2)`
before the REPL launches, exactly as `--register` does.

### Demo — `core demo anchor-lens-tour`

A narrative demo that walks a fixed two-prompt sequence under each
ratified lens, prints a lens × prompt grid, and emits a structured
JSON record with the three load-bearing claims:

```
Lenses exercised:
  - default_unanchored_v1   (engagement baseline; no annotation expected)
  - grc_logos_v1            (engages on knowledge via ἐπιστήμη)
  - he_logos_v1             (engages on truth via אמת)

Prompt sequence (2 prompts; deterministic order):
  P1: "What is knowledge?"
  P2: "What is truth?"

Per cell, the demo records:
  surface, grounding_source, trace_hash, anchor_lens_id, anchor_lens_mode_label.

Load-bearing claims (asserted before exit):
  lens_ids_recorded_per_turn               : True
  trace_hashes_distinct_across_lenses      : True (≥ 2 distinct hashes per prompt)
  surface_propositions_distinct_across_lenses: True (≥ 2 distinct surfaces per prompt)
  no_substrate_glyph_leak                  : True (surfaces stay ASCII at the lens block)
```

Exit code `0` iff every claim holds.  Schema mirrors
`core demo register-tour --json`.

### Files

```
core/physics/identity.py                                      EDIT
  - TurnEvent gains anchor_lens_id + anchor_lens_mode_label

chat/runtime.py                                               EDIT
  - _extract_anchor_lens_mode_label helper
  - both stub + main paths populate the two new fields on
    TurnEvent and ChatResponse
  - ChatResponse mirrors the two fields

chat/telemetry.py                                             EDIT
  - serialize_turn_event surfaces both fields

core/cli.py                                                   EDIT
  - cmd_chat adds --anchor-lens flag with fail-fast handler
  - _runtime_config_from_args threads anchor_lens_id
  - demo target choices add "anchor-lens-tour"
  - cmd_demo handler wires evals/anchor_lens_tour/run_tour
  - EPILOG gains "core demo anchor-lens-tour"

evals/anchor_lens_tour/__init__.py                            NEW
evals/anchor_lens_tour/run_tour.py                            NEW

tests/test_anchor_lens_telemetry.py                           NEW
  - TurnEvent default empty / populated under each lens
  - serialize_turn_event surfaces both fields
  - mode_label is "" when lens loaded but no engagement this turn
  - ChatResponse mirrors event fields

tests/test_anchor_lens_cli.py                                 NEW
  - _runtime_config_from_args threading
  - --anchor-lens parser wiring + default None
  - Invalid id ⇒ AnchorLensError at ChatRuntime init

tests/test_anchor_lens_tour_demo.py                           NEW
  - Three seam claims pinned individually
  - all_claims_supported overall
  - Per-cell anchor_lens_id recorded correctly
  - No substrate glyphs in the surfaces

docs/decisions/ADR-0073d-anchor-lens-telemetry-tour.md        NEW (this file)
```

### Invariants pinned at L1.4

```
anchor_lens_byte_identity_null_lift (L1.2)        — preserved
anchor_lens_lifts_proposition (L1.3)              — preserved
anchor_lens_no_glyph_leak (L1.3)                  — preserved
register-tour seam (R5)                            — preserved

invariant_anchor_lens_telemetry_visible (NEW):
  serialize_turn_event(event) always contains
  anchor_lens_id and anchor_lens_mode_label keys; the values
  reflect the runtime's loaded lens and the engaged mode label
  on this turn (or empty when no engagement).

invariant_anchor_lens_tour_seam (NEW):
  evals/anchor_lens_tour/run_tour.py asserts:
    - anchor_lens_id recorded per turn (matches runtime config)
    - trace_hash DISTINCT across lenses per prompt where lens engages
    - surface DISTINCT across lenses per prompt where lens engages
    - no substrate-block glyphs in any surface under any lens
  Exits non-zero on any violation.  Pinned by
  tests/test_anchor_lens_tour_demo.py.
```

---

## Consequences

### Capability unlocked at L1.4

* Operators drive any ratified lens from the CLI.
* Every audit JSONL line names which lens was active and whether it
  engaged on that turn.
* A single demo proves end-to-end that switching lenses moves
  trace_hash and surface — the opposite invariant from
  `register-tour`, asserted continuously.
* The anchor-lens × register matrix is now feature-complete enough
  to compose: any combination of `--register` × `--anchor-lens` is
  operator-driveable and audit-traceable.

### Cognition lane — unchanged

Empty defaults on the new TurnEvent fields preserve byte-identical
output.  The L1.2 null-lift and L1.3 lift invariants continue to
hold.  The cognition eval public/holdout numbers stay byte-identical
under the unanchored default.

### Backwards compatibility

* `TurnEvent` fields default to `""` — pre-L1.4 callers that
  construct `TurnEvent(...)` without the new fields keep working.
* `ChatResponse` defaults likewise.
* Existing telemetry consumers that read JSONL by key access continue
  to work; snapshot consumers may need to update — `anchor_lens_id`
  and `anchor_lens_mode_label` are added.  Snapshot tests document
  the new shape.

### Performance

One additional regex match per turn (for `_extract_anchor_lens_
mode_label`) when a lens is loaded.  When unanchored, the helper
early-exits on the empty `lens_id`.  Negligible.

### Trust boundaries

* **`--anchor-lens` flag does not bypass ratification.**  The flag
  value is passed through `_find_pack` and the loader's
  ratification check (see ADR-0073b).  An unratified pack id raises
  `AnchorLensError` exactly as a config-driven load would.
* **Mode-label extraction is read-only.**  The regex parses a
  surface the composer already produced; nothing in L1.4 can
  forge a `[lens(...):...]` annotation that the composer didn't
  emit, because the regex anchors on the literal
  composer-emitted format.
* **Telemetry stays redact-safe.**  Neither `anchor_lens_id` nor
  `anchor_lens_mode_label` carries surface content; both are pack
  identifiers / mode labels.  `include_content=False` paths surface
  them unconditionally because they're not content.
* **No new mutation surface.**  Pack files on disk are not modified
  by anything in L1.4.

---

## Verification

```
tests/test_anchor_lens_telemetry.py                           N passed
tests/test_anchor_lens_cli.py                                 N passed
tests/test_anchor_lens_tour_demo.py                           N passed
Curated lanes (must remain green):
  smoke / cognition / teaching / packs / runtime / algebra
Cognition eval byte-identical under default_unanchored_v1:
  public 100 / 100 / 91.7 / 100
core demo anchor-lens-tour                                    exit 0
core demo anchor-lens-tour --json                             stable schema
core demo register-tour                                       exit 0
                                                                (R5 seam still
                                                                 holds; both
                                                                 tours coexist)
```

The tour exit code is the canonical L1.4 gate — if `anchor-lens-tour`
ever exits non-zero in CI, the substantive axis has regressed.

---

## Composition with the register axis

`core demo register-tour` and `core demo anchor-lens-tour` test
opposite invariants and both must pass continuously:

```
register-tour    : trace_hash CONSTANT across registers
anchor-lens-tour : trace_hash DISTINCT across lenses
```

A future two-axis tour (`anchor-lens × register × prompts`) is
natural follow-on work but deferred — single-axis tours land first,
composition tour after.

---

## Open questions deferred

* **Combined CLI flag composition.**  `core chat --register X
  --anchor-lens Y` already works at the wiring level (both flags
  thread into `RuntimeConfig`).  A combined "audit view" demo
  showing the orthogonality matrix is a future ADR.
* **TurnVerdicts integration.**  Should TurnVerdicts carry
  `anchor_lens_id` / `register_id` alongside safety/ethics?  Yes
  eventually, but L1.4 keeps the fields on TurnEvent itself for now.
  A unifying ADR can consolidate later.
* **Mid-session lens switching.**  Today the lens is loaded once at
  `ChatRuntime.__init__`.  A `runtime.set_anchor_lens(<id>)` API
  would let an operator switch live.  Deferred — needs careful
  thinking about replay equivalence across the switch (mirror of
  the same deferral for register).
