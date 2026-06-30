# ADR-0087 — Rhetorical Style as Selection Axis (Pre-Work for Writing Curriculum)

**Status:** Proposed
**Date:** 2026-05-20
**Author:** Shay

---

## Context

A writing-curriculum extension to CORE is being scoped (informal name:
"PhD-level reading/writing"). Before any composer, content, or eval-lane
work begins, one architectural decision must be pinned: **what kind of
mechanism is rhetorical style?**

Two answers are plausible:

1. **A motor.** Style is encoded as a versor applied to the field at
   compose time. A "scientific" style is a different operator than a
   "popular" style; the operator transforms the realized state before
   surface emission.
2. **A selection axis.** Style is encoded as a pack the operator
   mounts at configuration time. A "scientific" deployment loads one
   pack; a "popular" deployment loads another. The realizer does not
   change behavior at compose time; it draws from a different
   substrate.

These look superficially similar — both can produce different
surfaces for the same prompt. They are not similar at all
structurally. The choice we make here propagates into every
downstream design decision in the writing curriculum.

### Why this is the right moment to decide

Two prior results constrain the answer:

- **The φ-separation result** (memory:
  [`phi-separation-falsified`](../../.claude/projects/-Users-kaizenpro-Projects-core/memory/MEMORY.md))
  established that semantic capability lives in *chain composition*,
  not in φ geometry. By extension, *style* capability — to the
  extent it is rhetorical-mode selection rather than semantic-content
  change — should not require a φ change either.

- **ADR-0085's "fusion operator" rejection.** The proposal to fuse
  realized template with geometric state before lexical collapse was
  declined on the grounds that it re-couples the realizer to field
  dynamics, breaks deterministic replay in a new place, and re-imports
  the transformer-style coupling CORE deliberately is not. A
  style-as-motor design has the same anti-pattern shape.

The current decoupling — geometric field → propositional plan →
deterministic realizer → realized surface → register decoration — is
load-bearing. Every prior ADR that improved capability did so by
*expanding the substrate the realizer draws from*, not by reaching
into the geometry. ADR-0083 added depth (transitive chains). ADR-0084
added definitions (gloss substrate). ADR-0085 added a frame for the
same substrate (gloss-aware CAUSE). None of them changed the field.

Rhetorical style should follow the same pattern.

### Existing axes for context

Two selection axes are already pinned by prior ADRs:

| Axis | ADR | What varies | `trace_hash` behavior | Engagement point |
|---|---|---|---|---|
| Register | [ADR-0070](./ADR-0070-register-terse-v1.md) | Surface decoration (terse / convivial / formal) | **CONSTANT** | post-composer (decorate_surface) |
| Anchor lens | [ADR-0073](./ADR-0073-anchor-lens-substrate.md) | Semantic-vocabulary tradition (Greek philosophical / Hebrew covenant) | **DISTINCT** | pre-realizer (substrate composer) |

These are CI-pinned as orthogonal:
[`anchor_lens_byte_identity_null_lift`](../../tests/test_anchor_lens_byte_identity.py)
holds the unanchored-vs-null identity; the register tour holds the
register-vs-trace invariance; the anchor-lens tour holds the
lens-vs-trace distinctness. Both invariants hold simultaneously
(memory: `adr-0073d-anchor-lens-telemetry-tour`).

Rhetorical style needs to slot into this taxonomy without breaking
either axis.

---

## Decision

**Rhetorical style is a selection axis, not a motor.** It is a
*third* substantive axis, sibling to anchor lens, orthogonal to
register.

### Axis definition

| Property | Value |
|---|---|
| **Mechanism** | Pack the operator mounts at runtime configuration time. Not a geometric operator, not a φ change, not a fusion at compose time. |
| **What it varies** | The rhetorical-mode frames the realizer is permitted to emit AND the rhetorical-move requirements the composer applies (e.g., academic style requires an evidence-bearing chain for every assertion; popular style does not). |
| **What it does NOT vary** | The semantic content (that's anchor-lens territory). The surface decoration (that's register territory). The field dynamics, versor closure, vault recall, or trace machinery (those are non-negotiable invariants). |
| **`trace_hash` behavior** | **DISTINCT across styles.** Style selection is substantive: it changes which moves the composer requires and which frames the realizer emits, which changes the propositional plan that feeds the trace. (CONTRAST with register, which holds trace constant.) |
| **Engagement point** | Pre-realizer, alongside anchor lens. The composer consults the active rhetorical-style pack when assembling the proposition graph; the realizer consults it when choosing frames. |
| **Default** | A `default_unstyled_v1` pack identical in effect to the absence of styling — null-lift, byte-identical traces. Mirrors ADR-0073b's `default_unanchored_v1`. |

### Pack shape (substrate, not consumer)

Analogous to `packs/anchor_lens/<id>/`:

```
packs/rhetorical_style/<id>/
  manifest.json              — pack identity, version, mastery_report seal
  rhetorical_style.json      — the pack content (see schema below)
  <id>.mastery_report.json   — companion self-seal, verified at load
```

`rhetorical_style.json` schema (proposed v1):

```jsonc
{
  "pack_id": "en_academic_v1",
  "version": 1,
  "issued_at": "2026-05-21T00:00:00Z",
  "default_unstyled": false,            // true only for the no-op pack
  "permitted_frames": [                 // realizer frame allow-list
    "warrant",                          //   "Therefore X, because Y."
    "concession",                       //   "While X, Y."
    "hedge",                            //   "This suggests X, though Q."
    "definitional_move"                 //   "By X we mean {gloss}."
  ],
  "required_moves_per_claim": [         // composer must include
    "evidence",                         //   every assertion needs evidence
    "warrant"                           //   bridging the evidence-claim gap
  ],
  "forbidden_moves": [                  // moves the style refuses
    "bare_assertion"                    //   no claims without warrant
  ],
  "provenance": "adr-0087:reviewed:2026-05-21"
}
```

Three named frames in the v0 vocabulary (`warrant`, `concession`,
`hedge`, `definitional_move`) are the *minimum* set the realizer
needs to express the claim-evidence-warrant triad. More frames are
added as the writing curriculum proves their necessity, not
preemptively.

### Composer & realizer contract

This ADR pins the *contract*; it does not implement the
consumers. The consumer ADR (call it ADR-0089 in the writing
sequence) will add:

- A `RuntimeConfig.rhetorical_style_id: str | None = None` field
  (default → `default_unstyled_v1` per mounting discipline).
- A `chat/runtime.py` plumb to make the active style pack available
  to the composer and realizer.
- Realizer extensions that read `permitted_frames` and refuse to
  emit frames outside the allow-list.
- Composer extensions that read `required_moves_per_claim` and
  refuse to ratify a surface that omits a required move.

The *substrate* lands first (this ADR + pack schema + loader +
`default_unstyled_v1` pack). The *consumer* lands second after the
substrate ratifies. This is the same sequencing discipline as
ADR-0084 → 0085.

### Forbidden alternatives

These are explicitly **not** the design, named here so future PRs
recognize them as anti-patterns:

| Anti-pattern | Why rejected |
|---|---|
| **Style as motor.** A versor applied to the field at compose time. | Re-couples realizer to geometry. Breaks deterministic replay (`trace_hash` now depends on compose-time field state). Same shape as the rejected ADR-0085 fusion proposal. |
| **Style as register.** Treating "academic" as a register-pack variant. | Conflates substantive (what moves must appear) with stylistic (how to decorate the surface). Would either bloat register packs with rhetorical-mode logic or silently broaden the trace-constant invariant. |
| **Style as identity axis.** A `precision: high` axis under `IdentityPack`. | Identity should be load-bearing and falsifiable (memory: `identity-doctrine`), not a place to encode per-deployment preferences. Adding "is academic style" as an identity axis is the bloat that doctrine refuses. |
| **Style detected from user input.** Auto-routing prompts to "scientific" vs "popular" lens based on heuristics. | Substantive variation should be operator-chosen, not auto-detected. The system shouldn't decide that this user "wants science"; the deployment decides what the system is. |

---

## Verification

### Required tests for the substrate

- **Pack loader**:
  - `default_unstyled_v1` ratifies with the same mastery-report
    self-seal discipline as `default_unanchored_v1`.
  - Missing pack → `RhetoricalStylePackError` (fail-closed, sister to
    `SafetyPackError`).
  - `permitted_frames` keys validated against a known-frame allow-list.
- **Schema validation**:
  - Unknown keys inside the rhetorical-style block → ratification
    failure.
  - `default_unstyled: true` only valid when `permitted_frames`,
    `required_moves_per_claim`, and `forbidden_moves` are all empty.
- **Null-lift invariant (CI-pinned)**:
  - `rhetorical_style_null_lift`: under `rhetorical_style_id=None`
    (resolves to `default_unstyled_v1`), every cognition lane case
    produces a byte-identical surface + `trace_hash` to today's
    no-style baseline.
- **Three-axis orthogonality (CI-pinned)**:
  - With register + anchor lens + rhetorical style all selectable
    independently, the orthogonality tour must show:
    - Register varies → `trace_hash` CONSTANT (existing invariant).
    - Anchor lens varies → `trace_hash` DISTINCT (existing invariant).
    - Rhetorical style varies → `trace_hash` DISTINCT (new invariant).
    - All three axes vary simultaneously without breaking either
      style or lens axis.

### Lanes (regression check)

```
core test --suite smoke -q
core test --suite cognition -q
core test --suite packs -q
core test --suite teaching -q
core test --suite runtime -q
core eval cognition          (byte-identical at default config)
```

### What this ADR does NOT verify

- Realizer frame-emission correctness — that's the consumer ADR.
- `required_moves_per_claim` enforcement — that's the consumer ADR.
- The harvester (Layer 0 of the writing curriculum) — separate spec.
- Genre-specific gloss content for any style other than
  `default_unstyled_v1` — separate content effort.

---

## Consequences

### What changes

- New `packs/rhetorical_style/<id>/` directory layout, sister to
  `packs/anchor_lens/` and `packs/safety/`.
- New `packs/rhetorical_style/loader.py` with `RhetoricalStylePack`
  dataclass and ratification gates.
- New `default_unstyled_v1` pack that produces the null-lift baseline.
- `docs/runtime_contracts.md` updated to declare rhetorical style as
  the third substantive axis with its `trace_hash` invariant.

### What does not change

- Composer or realizer behavior. Substrate-only ADR; consumers are a
  follow-up.
- Register or anchor-lens axes. Both remain operational with their
  current invariants.
- Versor / vault / recall / field dynamics. Untouched.
- The non-negotiable `versor_condition(F) < 1e-6` invariant.
- Identity / safety / ethics packs. Style is a fourth pack family
  (`identity` | `safety` | `ethics` | `rhetorical_style`), not a
  modification to any of them.

---

## Scope limits

- **No consumer code.** Realizer + composer integration is the next
  ADR's job.
- **No genre packs.** Only `default_unstyled_v1` ships in this ADR.
  `en_academic_v1`, `en_technical_v1`, etc., are content efforts that
  follow once the substrate ratifies and the consumer ADR lands.
- **No prompt-routing.** Style selection is operator-set at
  `RuntimeConfig` time only. Auto-detection is explicitly out of scope.
- **No retroactive renaming of anchor lens.** Anchor lens stays
  substantive-vocabulary; rhetorical style is the substantive-frame
  axis. They are siblings, not subsets.
- **No motor variant accepted.** Future PRs proposing
  style-as-motor must rebut this ADR; the burden of proof is on the
  proposer.

---

## Why now

A writing curriculum is being scoped. Before any composer extension,
content harvest, or eval lane lands for that curriculum, the
mechanism of rhetorical style needs to be fixed in writing. Without
this ADR, every downstream PR will face the same question ("should
this be a motor?") and the temptation to reach for the geometry will
recur every time the realizer produces a stilted surface. Pinning
the axis up front prevents that recurrence.

ADR-0087 is also the smallest possible commitment: pack schema +
loader + one null-lift pack + invariants. No consumer code, no
content, no realizer change. It's the most reversible-yet-
load-bearing step in the writing-curriculum sequence.

---

## Cross-References

- [ADR-0070](./ADR-0070-register-terse-v1.md) — register axis
  (stylistic, trace CONSTANT). Rhetorical style is the substantive
  sibling.
- [ADR-0073](./ADR-0073-anchor-lens-substrate.md) — anchor lens axis
  (substantive vocabulary, trace DISTINCT). Rhetorical style adopts
  the same substrate-pack discipline.
- [ADR-0084](./ADR-0084-definitional-layer.md) — substrate-then-
  consumer sequencing pattern. Reused here verbatim.
- [ADR-0085](./ADR-0085-gloss-aware-cause.md) — frame-swap-not-fusion
  precedent. The "fusion operator" rejection is the load-bearing
  prior art for this ADR's "motor rejection."
- Memory: `phi-separation-falsified` — semantic capability lives in
  chain composition, not φ geometry. Style capability is the natural
  next case of the same principle.
- Memory: `identity-doctrine` — why style does not belong on the
  identity axis.
- Future ADR-0088: rhetorical-style consumer (composer + realizer
  integration).
- Future ADR-0089: writing-chain harvester (Layer 0 of the writing
  curriculum, separately specified).
- Future spec: `docs/curriculum/writing-chain-harvester-spec.md` —
  the harvester specification this ADR's substrate ultimately serves.
