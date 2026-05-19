# ADR-0072 — Register telemetry + operator surface (Plan Phase R5)

**Status:** Proposed
**Date:** 2026-05-19
**Author:** Shay
**Phase:** Plan Phase R5 (operator-visible register)
**Builds on:** ADR-0068 (register pack class), ADR-0069 (realizer
register parameter), ADR-0070 (`terse_v1`), ADR-0071 (`convivial_v1` +
seeded variation)

---

## Context

R1–R4 built the register subsystem inside-out: pack class (R1),
realizer wiring (R2), first non-neutral knob (R3), seeded variation
(R4). At R4 the system *can* produce visibly different surfaces
across turns while staying bit-for-bit reproducible, but the register
is invisible to operators:

- `TurnEvent` carries `grounding_source` but not `register_id`.
- The audit JSONL stream has no field that distinguishes a
  neutral-register turn from a convivial-register turn that happens
  to have selected the empty closing.
- The CLI has no way to drive a register at all — every `core chat`
  invocation runs unregistered.
- There is no narrative demo showing the seam holding under variation
  the way `core demo audit-tour` shows it holding under identity /
  safety / ethics.

R5 closes those gaps. The register-pack architecture becomes
operator-observable, operator-driven, and demo-falsifiable. After
R5, the presentation axis is feature-complete enough to compose
against the substantive axis (Greek/Hebrew anchor lens) without
further plumbing.

---

## Decision

R5 ships three artifacts:

1. **Telemetry extension** — `TurnEvent` gains `register_id` and
   `register_variant_id`; the telemetry serializer surfaces them in
   every audit line.
2. **Operator surface** — `core chat --register <id>` CLI flag wires
   into `RuntimeConfig.register_pack_id`.
3. **Narrative demo** — `core demo register-tour` walks the same
   prompt sequence under {default_neutral_v1, terse_v1, convivial_v1}
   and prints a grid with per-cell `(surface, grounding_source,
   trace_hash, register_id, register_variant_id)`. The demo asserts
   the load-bearing seam claim — grounding_source and trace_hash are
   byte-identical across registers, only `surface` varies — and
   exits non-zero if it fails.

### Telemetry — `TurnEvent` shape extension

```python
# core/physics/identity.py
@dataclass(frozen=True)
class TurnEvent:
    ...
    grounding_source: str = "none"
    # ADR-0072 (R5) — operator-visible register identity per turn.
    register_id: str = ""
    register_variant_id: str = ""
```

- `register_id`: the loaded pack's `register_id`, or `""` for the
  in-memory `UNREGISTERED` sentinel. Pre-R4 deployments stay
  byte-identical (empty string is the default).
- `register_variant_id`: a stable 12-char SHA-256 digest of the
  selected `(opening, closing)` marker pair. Empty (`""`) when no
  decoration was applied (empty buckets, or empty surface). Different
  turns under the same register that select the same marker pair
  share the same `variant_id` — useful for "how many distinct
  variants did this register actually produce across N turns?"

The variant_id is intentionally a digest, not the literal strings:

- The literal markers are operator-authored content already on disk
  in `packs/register/<id>.json`; reproducing them inline in every
  TurnEvent is redundant.
- A digest is content-addressed: two different turns with the same
  variant_id provably picked the same marker pair without storing the
  pair twice.
- 12 chars (48 bits) is far more than enough to distinguish among at
  most `len(openings) × len(closings)` variants per register
  (currently ≤ 9 for convivial_v1).

### Decoration return type widens

Today `decorate_surface(surface, register, *, turn_idx, seed_text=None) -> str`.
R5 needs the variant_id alongside the surface. Two options:

- (A) Return a small frozen dataclass `DecorationResult(surface,
  opening, closing, variant_id)`.
- (B) Add a parallel `compute_decoration(...) -> DecorationResult` and
  leave `decorate_surface` as a thin wrapper.

R5 chooses **(A)** — a single source of truth for what decoration
happened. The R4 call sites in `chat/runtime.py` already expect a
string; they will be updated to read `.surface`. `decorate_surface`
gains a slim `decorate_surface_str` alias preserving the old return
type for off-runtime callers (tests, ad-hoc CLI tools).

```python
@dataclass(frozen=True, slots=True)
class DecorationResult:
    surface: str            # post-decoration string
    opening: str            # marker chosen for the opening bucket
    closing: str            # marker chosen for the closing bucket
    variant_id: str         # 12-char sha256(f"{opening}|{closing}") prefix

def decorate_surface(
    surface: str,
    register: RegisterPack,
    *,
    turn_idx: int,
    seed_text: str | None = None,
) -> DecorationResult: ...

def decorate_surface_str(...) -> str:
    return decorate_surface(...).surface
```

When both `opening` and `closing` are empty, `variant_id` is `""`
(the "no decoration applied" sentinel). This means
`UNREGISTERED`, `default_neutral_v1`, and `terse_v1` all emit
`variant_id=""` — they don't pollute the audit stream with a
no-op digest.

### CLI — `core chat --register <id>`

```python
# core/cli.py — cmd_chat argparser
chat_parser.add_argument(
    "--register",
    metavar="REGISTER_ID",
    default=None,
    help=(
        "Optional register pack ID (ADR-0068+).  Default: no register "
        "(unregistered sentinel, byte-identical to default_neutral_v1)."
    ),
)
```

Threads into `_runtime_config_from_args` as
`RuntimeConfig(register_pack_id=args.register)`. An invalid
register_id raises `RegisterPackError` at `ChatRuntime.__init__` — the
CLI catches and surfaces it as a clear error before the chat REPL
starts, not on the first turn.

### Demo — `core demo register-tour`

A narrative demo that walks a fixed prompt sequence under each
ratified register, prints a register × prompt grid of surfaces, and
emits a JSON record with the load-bearing claim:

```
Registers exercised:
  - default_neutral_v1
  - terse_v1
  - convivial_v1

Prompt sequence (4 prompts; deterministic order):
  P1: "What is light?"
  P2: "Define knowledge."
  P3: "What is truth?"
  P4: "Light reveals truth, right?"

Per cell, the demo records:
  surface, grounding_source, trace_hash, register_id, register_variant_id.

Load-bearing claim (asserted before exit):
  all_grounding_sources_identical: True
  all_trace_hashes_identical:      True
  surfaces_vary_at_least_once:     True (convivial vs neutral)
```

The demo prints a human-readable grid to stdout and a structured JSON
record (matching `core demo audit-tour --json` shape) for downstream
consumption. Exit code `0` iff every claim holds.

### Files

```
core/physics/identity.py                                     EDIT
  - TurnEvent gains register_id and register_variant_id
    (both default "" — pre-R4 byte-identical)

chat/register_variation.py                                   EDIT
  - DecorationResult dataclass added
  - decorate_surface return type widened
  - decorate_surface_str alias added for old callers

chat/runtime.py                                              EDIT
  - Both call sites of decorate_surface updated to read .surface
  - TurnEvent construction gains register_id + register_variant_id
    from the decoration result
  - Stub path also fills the two new fields

chat/telemetry.py                                            EDIT
  - serialize_turn_event adds register_id and register_variant_id
    to the output dict (always — pre-R4 emit "" for both)

core/cli.py                                                  EDIT
  - cmd_chat adds --register flag
  - _runtime_config_from_args reads args.register

evals/register_tour/run_tour.py                              NEW
  - Narrative demo runner; mirrors evals/audit_tour/run_tour.py shape
evals/register_tour/__init__.py                              NEW

core/cli.py                                                  EDIT
  - cmd_demo_register_tour subcommand wires to evals.register_tour
  - EPILOG gains "core demo register-tour" example

tests/test_register_telemetry.py                             NEW
  - TurnEvent fields populated on every chat() turn
  - serialize_turn_event surfaces both fields
  - register_id="" when register_pack_id=None
  - register_variant_id="" for null/empty-bucket registers
  - register_variant_id is a 12-char hex digest under convivial_v1

tests/test_register_cli.py                                   NEW
  - core chat --register convivial_v1 boots successfully
  - core chat --register bogus_v999 exits with clear error
  - flag default (no --register) preserves R4 behaviour

tests/test_register_tour_demo.py                             NEW
  - core demo register-tour exits 0 under all three registers
  - all_grounding_sources_identical == True
  - all_trace_hashes_identical == True
  - surfaces_vary_at_least_once == True
  - JSON output schema is stable (snapshot pin)

docs/decisions/ADR-0072-register-telemetry-operator-surface.md  NEW (this file)
```

### Invariants pinned in CI at R5

```
invariants A, B, C (ADR-0069)                       — preserved
invariant_register_grounding (ADR-0070)             — extended
invariant_seeded_variation_replay (ADR-0071)        — preserved
invariant_seeded_variation_turn_distinct (ADR-0071) — preserved

invariant_telemetry_register_visible (NEW):
  serialize_turn_event(event) always contains
  register_id and register_variant_id keys; the values reflect the
  runtime's loaded register at turn-emit time.

invariant_register_tour_seam (NEW):
  evals/register_tour/run_tour.py asserts:
    - grounding_source identical across registers per prompt
    - trace_hash identical across registers per prompt
    - surface differs at least once (convivial vs neutral)
  Exits non-zero on any violation.  Pinned by
  tests/test_register_tour_demo.py.
```

The tour demo is the load-bearing R5 artifact. It is the
operator-visible answer to "does the seam actually hold?" and it
exits non-zero if it doesn't — turning the architectural claim into a
falsifiable CI check.

---

## Consequences

### Capability unlocked at R5

- An operator can drive any ratified register from the CLI.
- Every audit JSONL line names which register was active and which
  variant fired — the audit trail can answer "did the operator's
  --register flag actually take effect?" without inferring it.
- A single demo proves end-to-end that switching registers does not
  move trace_hash or grounding_source, only surface text.

### Cognition lane — unchanged

Empty defaults on the new TurnEvent fields preserve byte-identical
output. The R1–R4 invariants continue to hold. The cognition eval
public/holdout numbers stay byte-identical.

### Backwards compatibility

- `TurnEvent` fields default to `""` — pre-R5 callers that construct
  `TurnEvent(...)` without the new fields keep working.
- `decorate_surface` signature is widening from `-> str` to
  `-> DecorationResult`. The two runtime call sites are updated in
  the same PR. Off-runtime callers (tests, ad-hoc CLI) use the new
  `decorate_surface_str` alias when they only want the string.
- Existing telemetry consumers that read JSONL by key access continue
  to work; consumers that snapshot the *exact* set of keys may need
  to update — `register_id` and `register_variant_id` are added.
  Snapshot tests in `tests/test_register_telemetry.py` document the
  new shape.

### Performance

One additional SHA-256 per turn (for variant_id), one new dict entry
in the telemetry payload. Negligible.

### Trust boundaries

- **`--register` flag does not bypass ratification.** The flag value
  is passed through `_validate_pack_id` (already in the loader) and
  through the ratify gate at load time. An unratified pack id raises
  `RegisterPackError` exactly as a config-driven load would.
- **Variant_id is content-addressed.** Two operators staring at the
  same variant_id are looking at the same marker pair, full stop.
  No content rendering required; no info leak beyond what
  `register_id` already implies.
- **CLI value sanitization.** `args.register` is a user-controlled
  string entering the trust boundary. Path traversal and unsafe ids
  are rejected by the loader's existing `_find_pack` guard.
- **Telemetry stays redact-safe.** Neither `register_id` nor
  `register_variant_id` carries content; both are pack identifiers /
  digests. `include_content=False` paths surface them unconditionally
  because they're not content.
- **No new mutation surface.** Pack files on disk are not modified
  by anything in R5.

---

## Verification

```
tests/test_register_telemetry.py                             N passed
tests/test_register_cli.py                                   N passed
tests/test_register_tour_demo.py                             N passed
Curated lanes (must remain green):
  smoke / cognition / teaching / packs / runtime / algebra
Cognition eval byte-identical:
  public 100 / 100 / 91.7 / 100
  holdout 100 / 100 / 83.3 / 100
core demo register-tour                                      exit 0
core demo register-tour --json                               stable schema
```

The tour exit code is the canonical R5 gate — if it ever exits
non-zero in CI, the register subsystem has regressed.

---

## Open questions deferred to later phases

- **TurnVerdicts integration.** Should `TurnVerdicts` carry the
  register identity alongside safety/ethics/identity? Probably yes
  for a fully unified audit bundle, but R5 keeps the field on
  TurnEvent itself for now. Future ADR may consolidate.
- **Variant_id collision space.** A 12-char hex prefix is 48 bits.
  Two distinct `(opening, closing)` pairs collide with probability
  ~2^-48 — effectively zero across any realistic operator-authored
  bucket. If buckets ever grow to thousands of entries, widen to 16
  or 20 chars. Not an R5 concern.
- **Operator-driven register switching mid-session.** Today the
  register is loaded once at `ChatRuntime.__init__`. A `runtime.set_
  register(<id>)` API would let an operator switch live. Deferred —
  needs careful thinking about replay equivalence across the switch.

---

## Future ADRs unlocked

- **ADR-0073+ (post-R5)** — anchor lens / substantive variation
  (Greek/Hebrew). The presentation axis is now operator-visible,
  CI-falsifiable, and audit-traceable. Anchor lens composes against
  it as an *orthogonal* axis (content variation, not surface
  variation). See `[[greek-hebrew-pack-scout-2026-05-19]]` for the
  content prerequisites (distinction-bearing lemmas, alignment
  files on cognition-tier packs, reviewed teaching corpus in non-
  English).
