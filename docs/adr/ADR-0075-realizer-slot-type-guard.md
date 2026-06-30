# ADR-0075 — Realizer slot-type guard (C1: coherence floor)

**Status:** Accepted
**Date:** 2026-05-19
**Ratified:** 2026-05-19
**Author:** Shay
**Builds on:** [ADR-0048](./ADR-0048-pack-grounded-surface.md)
(pack-grounded surface), [ADR-0049](./ADR-0049-intent-subject-extraction.md)
(intent subject extraction), [ADR-0053](./ADR-0053-cognition-lane-closure.md)
(cognition lane closure)
**Series:** C1 — Coherence floor (precedes C2 confirmation-tag normalization,
R6 substantive register knobs, T1 curated teaching depth)

---

## Context

The orthogonality tour landed `4426f38` with `all_claims_supported=true`
across the full 3 × 3 × 2 grid.  But inspection of the grid surfaced a
real coherence regression on a fourth prompt under live demo:

```text
"Light reveals truth, right?"  →  "Right does not thought."
```

That surface is grammatically illegal: the verb slot of a
`<subject> does not <verb>` construction is occupied by a bare noun
(`thought`, which is a noun in `en_core_cognition_v1`).  All three
registers reproduced this illegal form byte-identically, which is the
correct behavior for the register axis (it preserves whatever the
truth path produced) but reveals that the truth path itself is
licensing surfaces that no realizer template should be able to emit.

The doctrine in CLAUDE.md is explicit:

> Code and tests should make illegal states difficult to represent.
> Prefer inspectable state, provenance, and deterministic replay over
> impressive-looking but ungrounded outputs.

C1 addresses this at the construction boundary — a deterministic
slot-type verifier that rejects illegal articulations before they can
escape to the user surface, regardless of which composer or intent
path produced them.  This is the coherence floor that C2
(confirmation-tag normalization), R6 (substantive register knobs),
and T1 (curated teaching) all rest on.

### Why this comes first

If C2 is fixed before C1, the specific bug above goes away but the
underlying property — "no illegal articulation ever escapes" — is
not established.  The next intent/extraction bug will produce a new
word-salad surface and the cycle repeats.  C1 establishes the
invariant; C2 fixes the specific input class that exposed it.

If R6 ships before C1, terse and convivial registers will start
emitting substantively distinct surfaces on top of a path that can
still produce word salad.  Worse cosmetics on the same broken floor.

If T1 ships before C1, the reviewed corpus inherits the illegal
articulation pattern wherever it touches a path the guard would have
caught — the corpus becomes a vector for the bug, not a fix for it.

---

## Decision

### Mechanism

A pure verifier `generate/realizer_guard.py` that runs on every
candidate surface produced by `pack_grounded_surface`,
`pack_grounded_comparison_surface`,
`pack_grounded_correction_surface`,
`pack_grounded_procedure_surface`, the cross-pack chain composer,
NARRATIVE / EXAMPLE composers, and any vault-grounded realizer
output, before that surface is assigned to `ChatResponse.surface` or
emitted on `walk_surface`.

The guard is deterministic, reads pack POS data already loaded at
runtime, performs a single linear pass, and emits a verdict:

```python
@dataclass(frozen=True)
class RealizerGuardVerdict:
    status: Literal["ok", "rejected"]
    rule_id: str          # e.g. "R1_no_finite_verb"; "" when ok
    detail: str           # surface fragment that violated the rule
```

### Slot-type rules (C1 active scope — two rules)

```
R2_aux_neg_requires_verb:
    If the surface contains a do-support negation
    ("does not" / "do not" / "did not"), the immediately following
    content token must have POS = VERB per pack lookup.
    Adverbs between the negation and the verb are allowed
    ("does not always reveal" — "always" is skipped, then "reveal"
    must be VERB).

R3_be_neg_requires_predicate:
    If the surface contains a be-negation
    ("is not" / "are not" / "was not" / "were not"), the immediately
    following content token must have POS ∈ {NOUN, ADJ, DET, ADV,
    PRON} per pack lookup.  Bare verbs after be-negation are
    illegal ("is not reveal" is rejected).
```

Both rules fire on **presence of an illegal pattern**, not on
**absence of an expected token** — high precision, low false-positive
rate.  They cover the observed failure mode and the symmetric form.

### Deferred during ratification

```
R1_no_finite_verb:
    Every emitted clause must contain at least one finite verb token.
    Deferred from active C1 scope: the cognition pack's POS coverage
    does not include every English finite verb the teaching-chain
    realizer emits (notably "requires" and "makes"), and switching
    R1 on regresses currently-passing cases — a violation of the
    byte-identity invariant the ADR explicitly flags as the canary.
    R1's intent is preserved for a follow-up coherence ADR that
    either broadens pack POS coverage or adds a closed English-
    vocabulary POS table.

Subject / object / predicate pack-residency:
    Further rules (subject-pack-residency, object-pack-residency,
    proposition-graph-residency) are deliberately deferred to a
    follow-up coherence ADR — C1 is a narrow floor, not a parser.
```

### Failure routing — fail closed, not silent

When the guard returns `status == "rejected"` on a candidate surface,
the truth path:

1. **Does not** silently drop the surface.
2. **Does not** retry the realizer with different parameters.
3. **Does** replace the surface with a deterministic bounded
   disclosure string:

```text
"I do not have a reviewed articulation for that yet."
```

4. **Does** preserve the pre-guard surface on `walk_surface` for
   telemetry / debugging (consistent with the existing
   `surface` ≠ `walk_surface` runtime contract).
5. **Does** flag `grounding_source` as `"none"` regardless of what
   the rejected candidate had claimed (an illegal surface is
   ungrounded by construction).

### Telemetry surface

`TurnEvent` gains two fields, default empty:

```
realizer_guard_status : "" | "ok" | "rejected"
realizer_guard_rule   : "" | "R1_no_finite_verb" | "R2_aux_neg_requires_verb"
                        | "R3_be_neg_requires_predicate"
```

`serialize_turn_event` emits both fields alphabetically, deterministic.

`ChatResponse` gains the same two fields, propagated identically on
stub and main paths (mirrors `register_id` / `anchor_lens_id`
threading pattern).

### Hook point

Single seam in `chat/runtime.py`, immediately after the composer
returns a candidate surface and before the surface is assigned to
`ChatResponse.surface` or to the `pre_decoration_surface_*` slot that
feeds the register decoration step.  This placement matters:

* Guard runs **before** register decoration, so the
  register-decorated form is never the verifier's responsibility.
* Guard runs **before** anchor-lens annotation extraction, so the
  `[lens(...):...]` annotation is never on a guard-rejected surface.
* Guard runs **after** all composers, so a single seam catches
  every articulation path.

### Files

```
generate/realizer_guard.py                              NEW
  - RealizerGuardVerdict frozen dataclass
  - check_surface(surface: str, *, pack_lexicons: Mapping)
        -> RealizerGuardVerdict
  - Three pure rule helpers; no I/O; no mutation.

chat/runtime.py                                          EDIT
  - Hook check_surface() between composer return and surface assignment
  - Failure routing: surface = bounded disclosure; walk_surface = raw
    rejected candidate; grounding_source = "none"; populate guard
    telemetry fields on TurnEvent + ChatResponse.

core/physics/identity.py                                 EDIT
  - TurnEvent.realizer_guard_status: str = ""
  - TurnEvent.realizer_guard_rule:   str = ""

chat/telemetry.py                                        EDIT
  - serialize_turn_event: emit both fields alphabetically.

evals/realizer_guard/__init__.py                         NEW
evals/realizer_guard/run_holdout.py                      NEW
  - Six confirmation-tag / illegal-articulation prompts that
    currently produce illegal surfaces.  Under C1 alone (without
    C2), every one routes to bounded disclosure with
    realizer_guard_status="rejected" and a recorded rule_id.
  - Exit code 0 iff invariant_realizer_no_illegal_articulation holds
    across the cluster.

tests/test_realizer_guard_unit.py                        NEW
  - 22 cases: R2 / R3 (each negation form, copula handling, adverb
    skipping, end-of-surface, unknown lemma fail-closed); R1
    deferred (the verb-less cases pin current pass-through behavior
    so re-enablement is intentional).

tests/test_realizer_guard_runtime_seam.py                NEW
  - Stub + main path: rejected candidate → bounded disclosure on
    surface, raw candidate on walk_surface, grounding_source="none",
    telemetry fields populated.
  - AST seam: realizer_guard imports no truth-path modules.

tests/test_realizer_guard_holdout.py                     NEW
  - Holdout cluster: six confirmation-tag / illegal-articulation
    prompts; every one rejected with expected rule_id.
  - Cognition eval cases: zero rejections (byte-identical baseline).

docs/decisions/ADR-0075-realizer-slot-type-guard.md      NEW (this file)
```

No pack mutation.  No composer rewrites.  No new dynamic imports.
No new filesystem writes.  No CLI surface changes (telemetry only).

### Invariants pinned

```
invariant_realizer_no_illegal_articulation (NEW):
  For every prompt in the cognition eval lane + every prompt in the
  C1 holdout cluster + every demo grid cell in register-tour /
  anchor-lens-tour / orthogonality-tour, the surface emitted on
  ChatResponse.surface satisfies R2 and R3.
  Holdout cluster surfaces are bounded disclosure strings (rejection
  is the correct behavior for that input class under C1 alone).

invariant_realizer_guard_byte_identity_on_currently_passing_cases (NEW):
  For every cognition eval case that currently produces a legal
  articulation, the post-C1 surface is byte-identical to the pre-C1
  surface.  The guard must not regress any legal articulation.

register-tour invariant                                  — preserved
anchor-lens-tour invariant                               — preserved
orthogonality-tour invariant                             — preserved
anchor_lens_byte_identity_null_lift                       — preserved
register_invariant_grounding                              — preserved
```

The first invariant is the load-bearing one — it is the formal
statement that illegal articulations cannot escape, regardless of
which composer or intent path produced them.

---

## Consequences

### Capability unlocked

Word-salad surfaces (`"Right does not thought."` and its symmetric
forms) cannot escape to the user, even when intent classification or
subject extraction is wrong.  Bugs in upstream stages now degrade
gracefully to a bounded disclosure surface rather than to ungrounded
articulation.  This is the precondition that lets C2 / R6 / T1 ship
safely.

### Cognition lane

Expected byte-identical on currently-passing cases (invariant
`invariant_realizer_guard_byte_identity_on_currently_passing_cases`
is part of the CI gate).  Any case that the guard rejects under C1
is, by definition, a case where the prior surface was illegal —
those move to bounded disclosure and lose their `term_capture` /
`surface_groundedness` credit until C2 + T1 land the proper fix.

If any currently-passing case regresses, the rule is too aggressive
and must be narrowed before merge.  The byte-identity invariant is
the canary.

### Performance

Single linear pass over the candidate surface tokens with a
dictionary lookup per content token.  O(n) on surface length, runs
once per turn.  Well below the per-turn latency floor measured in
the teaching-loop bench (mean 1.85s).  No new caches.

### Trust boundaries

* **Construction-boundary verifier, not hot-path repair.**  The
  guard rejects and reroutes; it never edits the candidate surface.
  This keeps it firmly outside the "forbidden normalization sites"
  list in CLAUDE.md (it is not normalization — it is admission
  control with a deterministic fallback).
* **No filesystem, no dynamic import, no shell.**  The guard reads
  pack lexicons already loaded at runtime.
* **No user-text mutation path.**  Guard output is structural
  (status + rule_id + detail); the bounded disclosure string is a
  module-level constant, never composed from user input.
* **AST seam test** in `tests/test_realizer_guard_runtime_seam.py`
  refuses truth-path imports of `generate.realizer_guard` from any
  module other than `chat/runtime.py` — the hook is centralized,
  not sprinkled.
* **Telemetry redaction unchanged.**  `realizer_guard_rule` is a
  rule_id from a closed set; `realizer_guard_status` is a closed
  enum.  Neither field can leak user content.

### Replay determinism

Guard is a pure function of `(surface_string, pack_lexicons)`.
Pack lexicons are deterministic from manifest checksums.  Therefore
guard verdicts are deterministic and replay-equivalent across runs.
This composes with the existing trace_hash discipline: a rejected
turn's trace_hash is computed on the pre-decoration **disclosure**
surface (the user-facing surface), which keeps replay equivalence
intact.

### What this explicitly does *not* do

* Does not fix the confirmation-tag intent bug.  That is C2.
* Does not change register substantive consumption.  That is R6.
* Does not add new teaching chains.  That is T1.
* Does not extend the rule set beyond R1/R2/R3.  Subject-pack-
  residency, object-pack-residency, and proposition-graph residency
  are deferred to a follow-up ADR after C1 + C2 land and the failure
  modes are re-surveyed.
* Does not retry or refine on rejection.  Fail closed, route to
  disclosure, surface the verdict to telemetry, move on.

---

## Verification

```
python -m pytest tests/test_realizer_guard_unit.py -q            N passed
python -m pytest tests/test_realizer_guard_runtime_seam.py -q    N passed
python -m pytest tests/test_realizer_guard_holdout.py -q         N passed

python -m evals.realizer_guard.run_holdout                       exit 0
core eval cognition                                              byte-identical
                                                                 on currently
                                                                 passing cases

Curated lanes (must remain green):
  smoke / cognition / teaching / packs / runtime / algebra / full

Existing demos continue to pass:
  core demo register-tour                                        exit 0
  core demo anchor-lens-tour                                     exit 0
  core demo orthogonality-tour                                   exit 0
```

The C1 holdout cluster's exit code is the canonical coherence-floor
gate — if any illegal articulation can escape, it exits non-zero.

---

## Follow-ups (not in C1 scope)

* **C2** — Confirmation-tag normalization.  Make
  `"X reveals Y, right?"` preserve the propositional content
  (`subject=X, relation=reveals, object=Y`, intent=VERIFICATION)
  so the holdout cluster moves from "correctly rejected" to
  "correctly articulated".  Eval cases re-pin under C2.
* **R6** — Substantive register knobs on pack-grounded composers,
  plus replacement of the weak `surfaces_vary_at_least_once`
  register-tour gate with per-register substantive distinctness.
* **T1** — Curated teaching depth for the core epistemic vocabulary
  appearing in the live demos (light / truth / knowledge / evidence
  / wisdom / recall), through the existing
  `core teaching propose → review → accept` flywheel.
* **Coherence rule extensions** — subject-pack-residency,
  object-pack-residency, proposition-graph residency.  Deferred
  until the C1 / C2 failure surface is observed in CI for at least
  one full eval cycle.
