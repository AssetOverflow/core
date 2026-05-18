# ADR-0051 — Trust-Boundary Hardening Pass

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay

---

## Context

`CLAUDE.md § Security and Trust Boundaries` enumerates six high-risk
surfaces and a required approach.  Up to this point those rules have been
enforced *by convention* across ADR-0027 (identity packs), ADR-0029
(safety packs), ADR-0033 (ethics packs), and the `core pack validate`
CLI introduced earlier.  Several of the load-bearing properties had
ad-hoc enforcement and no dedicated regression tests, which means a
future refactor could quietly weaken them.

This ADR is an audit pass over the four mutable surfaces named in the
doctrine and converts the live properties into type-level and test-level
guards:

1. `core pack validate` dynamic validator execution.
2. Language / source pack loading via `language_packs.compiler`.
3. OOV token grounding error messages.
4. Pack mutation proposal-only enforcement.

The ADR adds **no new capability**.  It hardens what is already there and
pins the trust boundary in regression tests so it can be verified in CI
on every change.

---

## Decision

### Surface 1 — `core pack validate` dynamic validator execution

**Audited state.**  Already hardened in `core/cli.py`:

- `_safe_pack_id(pack_id)` rejects empty ids, `..` traversal, leading
  `/`, and embedded path separators *before* any `Path` join.
- `cmd_pack_validate` requires `--allow-arbitrary-code` to execute the
  pack's `validators.py`.  Default behaviour is fail-closed.
- `--dry-run` reports validator presence without `importlib.util`
  resolving the module spec.

This ADR adds no change to that surface and confirms via
`tests/test_cli_pack_validate_security.py` (pre-existing) that the
boundary holds.  Result: the boundary is doctrinally complete.

### Surface 2 — Language / source pack loading

**Audited state — gap found.**  `language_packs/compiler.py` exposed
three public entrypoints — `load_pack(pack_id)`,
`load_pack_entries(pack_id)`, and `load_mounted_packs(pack_ids)` — that
concatenated their argument straight into a filesystem path
(`Path(__file__).parent / "data" / pack_id`) without any traversal
guard.  The sibling pack loaders (`packs/identity/loader.py`,
`packs/safety/loader.py`, `packs/ethics/loader.py`) already had a
`_find_pack` guard; the language-pack loader did not.

**Fix.**  A module-private `_validate_pack_id` runs *before* any
`Path` operation at every public entrypoint.  It rejects:

- non-string inputs,
- empty strings,
- `..` substrings,
- `/` or `\` separators,
- leading `.` (hidden-dir convention),
- any character outside ASCII alphanumerics, `_`, or `-`.

The guard's exception message routes the offending fragment through
`core._safe_display.safe_pack_id` so a hostile pack id cannot inject
control characters into the error string.

### Surface 3 — OOV grounding error messages

**Audited state.**  The OOV-grounding error message in
`chat/runtime.py:_apply_oov_policy` interpolates a raw user-controlled
token into a `KeyError` string
(`KeyError(f"OOV token requires vocab proposal: {token}")`).  The
exception is raised at the runtime boundary and is caught by
`respond()`, but other callers consume the exception text directly.

**Fix.**  This ADR introduces a *central* safe-display sanitiser at
`core/_safe_display.py` with two helpers:

- `safe_display(value, *, max_len=64)` — neutralises ASCII C0 and C1
  control characters (the ANSI ESC `\x1b` prefix, newlines, carriage
  returns, NULs, DEL, and the C1 range 0x80-0x9F), coerces non-strings
  through `repr`, and truncates with a trailing `"..."`.  The
  transformation is deterministic, pure, and lossy on purpose.
- `safe_pack_id(value)` — a narrower mask suitable for pack ids: only
  ASCII alphanumerics, `-`, `_`, and `.` survive; everything else is
  replaced with `?`.

`chat/runtime.py` is on the doctrine-fenced file list for this ADR, so
the runtime call-site itself is not rewired here — `core._safe_display`
ships as the canonical helper that the runtime OOV site (and any
future log/error site) **must** route through.  That follow-up wiring
is a small, mechanical change reserved for a separate ADR that touches
the chat runtime under its own review.

The sanitiser is doctrinally a logging/display helper.  It must never
be imported by `algebra/`, `generate/`, `field/`, or `vault/` — the
module docstring states this and the test suite asserts it stays out
of those paths transitively.

### Surface 4 — Pack mutation proposal-only enforcement

**Audited state.**  `teaching/store.py:PackMutationProposal` is already
declared as `@dataclass(frozen=True, slots=True)` with
`applied: bool = False` and `epistemic_status =
EpistemicStatus.SPECULATIVE` defaults.  `with_status` returns a new
instance via `dataclasses.replace`.  No `apply_proposal` /
`apply_mutation` path exists in the codebase.

**Fix.**  No code change — the type was already correct.  This ADR
adds `tests/test_mutation_proposal_type.py`, which encodes the
invariants as CI-enforced guards:

- The class is a dataclass.
- Frozen — direct attribute assignment raises `FrozenInstanceError`.
- Slots — arbitrary attribute monkey-patching raises `AttributeError`.
- `applied` defaults to `False`.
- Default `epistemic_status` is `SPECULATIVE`.
- `with_status` returns a new instance, never mutates the original.
- No field named `final`, `frozen`, `axiom`, `permanent`, or
  `immutable` exists on the dataclass (ADR-0021 non-hardening
  invariant).

If a future refactor weakens any of these, CI fails before the change
merges.

---

## Why this is doctrine-aligned

CLAUDE.md prohibits *hidden normalisation, hot-path repair, stochastic
fallback, approximate recall, and unreviewed mutation*.  This ADR:

- **Adds no algebra.**  `versor_condition(F) < 1e-6` is unaffected —
  no new operator, no field state touched.
- **Adds no hot-path normalisation.**  `core/_safe_display.py` is a
  display sanitiser, not a runtime normaliser.  Importing it from
  `algebra/`, `generate/`, `field/`, or `vault/` is explicitly out of
  scope.
- **Adds no LLM fallback or stochastic sampling.**  The sanitiser is
  deterministic and pure.
- **Adds no broad infrastructure.**  Two new small modules
  (`core/_safe_display.py`, the `_validate_pack_id` helper inside
  `language_packs/compiler.py`) and three new test files.
- **Pins the boundary in tests.**  The invariants previously enforced
  by convention now fail closed in CI.

---

## Consequences

### What changes

- New module `core/_safe_display.py` — central sanitiser for user-
  controlled fragments in error / log messages.
- `language_packs/compiler.py` gains `_validate_pack_id` and wires it
  into `load_pack`, `load_pack_entries`, and `load_mounted_packs`.
- Three new test files:
  - `tests/test_safe_display.py` (20 tests)
  - `tests/test_language_pack_load_safety.py` (24 tests)
  - `tests/test_mutation_proposal_type.py` (9 tests)

### What does not change

- No runtime behaviour for any happy-path code (real pack ids load
  unchanged).
- `chat/runtime.py`, `chat/pack_grounding.py`, `chat/telemetry.py`,
  `chat/verdicts.py`, `generate/intent.py`, `generate/intent_bridge.py`,
  `teaching/*`, `core/physics/identity.py`, and
  `core/cognition/pipeline.py` are untouched.
- `core eval cognition` metrics are unchanged.  Baseline:
  `intent_accuracy = 100.0 %`, `surface_groundedness = 69.2 %`,
  `term_capture_rate = 58.3 %`, `versor_closure_rate = 100.0 %`.

### Follow-up reserved for a separate ADR

- Wiring `chat/runtime.py:_apply_oov_policy`'s `KeyError(f"OOV token
  requires vocab proposal: {token}")` to route through
  `core._safe_display.safe_display(token)`.  The mechanical change is
  one line; the fence keeps it out of scope here.

### Scope limits

- This ADR is an audit pass, not a feature.  It does not change any
  user-facing surface.
- The sanitiser caps at 64 characters by default and 48 for pack ids —
  callers that need full fidelity in a *trusted* context can pass a
  larger `max_len`, but the default is the conservative choice.

---

## Cross-References

- `CLAUDE.md § Security and Trust Boundaries` — the doctrine this ADR
  audits.
- [ADR-0021](./ADR-0021-epistemic-grade-policy.md) — the
  non-hardening invariant on proposal status pinned by
  `test_no_forbidden_finality_flags_on_proposal`.
- [ADR-0027](./ADR-0027-identity-packs.md) /
  [ADR-0029](./ADR-0029-safety-packs.md) /
  [ADR-0033](./ADR-0033-ethics-packs.md) — sibling pack loaders that
  already carry the `_find_pack` traversal guard the language-pack
  loader now mirrors.
- [ADR-0040](./ADR-0040-telemetry-sink.md) — the redact-by-default
  telemetry sink whose discipline this ADR generalises to error-
  message sites.

---

## Verification

```
tests/test_safe_display.py                  20 tests, all green
tests/test_language_pack_load_safety.py     24 tests, all green
tests/test_mutation_proposal_type.py         9 tests, all green
tests/test_cli_pack_validate_security.py    (pre-existing) all green

Lanes (all green on this branch):
  core test --suite smoke         67 passed
  core test --suite cognition    121 passed
  core test --suite runtime       19 passed
  core test --suite packs          6 passed
  core test --suite algebra      132 passed

core eval cognition (baseline preserved):
  intent_accuracy        100.0%   (=)
  surface_groundedness    69.2%   (=)
  term_capture_rate       58.3%   (=)
  versor_closure_rate    100.0%   (=)
```

The non-negotiable field invariant (`versor_condition(F) < 1e-6`) is
preserved — this ADR introduces no algebra, no rotor construction, and
no field update.
