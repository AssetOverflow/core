# ADR-0025 — Rotor / Frame Admissibility

| Field         | Value                                          |
|---------------|------------------------------------------------|
| Status        | **Accepted** (2026-05-17)                      |
| Date          | 2026-05-17                                     |
| Supersedes    | The design-note version of ADR-0025 (Draft)    |
| Extends       | ADR-0022, ADR-0023, ADR-0024, ADR-0026         |
| Decision lead | Shay (with CORE assistant)                     |

---

## Status note

This ADR promotes the previous design-note draft to Accepted, with
the **architectural home decision reversed**.  The earlier draft
leaned toward Option B (`algebra/versor.py`); after re-examining the
trade-offs in light of CLAUDE.md doctrine and Phase 3's wiring, the
correct placement is a *fourth option* the draft did not crystalise:
a sibling-but-separate module under `generate/` —
**`generate/rotor_admissibility.py`**.  See §"Architectural home" for
the full argument.

The threshold-scheme question (draft's Question 2) is closed by
inheritance from ADR-0026 / Phase 3: the rotor side reuses the
ranked-with-margin contract — although, in Phase 4, the per-candidate
rotor check operates at a simpler positivity bar (`score > 0`),
matching the per-step gating shape of ADR-0024.  A future iteration
may extend rotor-side ranking with a margin, once we have multiple
candidate rotors and a corpus that motivates it.

The teaching-loop question (draft's Question 3) is closed at
**Stance A — strictly hygiene-only**, as recommended in the draft.

---

## Context

ADR-0024 added per-step inner-loop admissibility for the
*destination-token / direction* side of an `AdmissibilityRegion`:
when a candidate's CGA inner product against `relation_blade` falls
below the configured bar, the candidate is excluded and the walk
re-selects (or refuses, ADR-0024 Phase 2 / ADR-0026 / Phase 3).

ADR-0024 explicitly deferred:

> Frame-versor admissibility (does the rotor preserve / transform
> within the frame constraint?) remains out of scope.

That deferral is closed here.  Rotor-side admissibility asks a
different question than destination-side admissibility:

* **Destination admissibility (ADR-0024 / ADR-0026):** does the
  candidate destination versor align with the relation blade?
* **Rotor admissibility (this ADR):** does the rotor `V` applied to
  the current field `F` land within the region's frame-versor
  admissible cone?

The two are independent gates that compose: a candidate is admitted
iff both pass.  A region carrying both `relation_blade` and
`frame_versor` exercises both gates; a region carrying only one
exercises only that one; an unconstrained region exercises neither.

---

## Architectural home — the decision

Three candidates the draft considered, plus a fourth option that
crystalised during Phase 4 implementation:

### Option A (rejected): single inner-loop in `generate/stream.py`

Inline the rotor check in the same per-step inner loop as the
destination check.  Draft's objection: "Pushes algebra-shaped
invariants into a generation-shaped module ... bloats the hot path
and entangles concerns."

Rejected here too — but for a more precise reason: it conflates the
two semantic axes (destination vs rotor) into one decision site,
making the trace harder to read and the refusal reason harder to
classify.  The fix is *separation*, not relocation.

### Option B (rejected): `algebra/versor.py` (closure invariant)

Make rotor admissibility part of `word_transition_rotor`'s
construction — same shape as `versor_condition < 1e-6`.

The draft recommended this on doctrinal grounds ("algebra-owned
closure belongs in `algebra/`").  **Rejected on closer reading.**

Admissibility is not closure.  Closure asks "does the constructed
versor satisfy the algebra's idempotency invariant?" — a
*structural* property of the rotor itself.  Admissibility asks "does
the rotor's *effect on the field* land in a pack-grounded admissible
region?" — a *semantic* property of the rotor as applied to specific
field state in the presence of a pack-derived frame versor.

Putting the semantic test inside the algebra layer has two structural
costs:

1. **Coupling.** `algebra/` becomes dependent on
   `generate.admissibility.AdmissibilityRegion`, a pack-derived
   construct.  This crosses a layer boundary that was clean
   yesterday.
2. **Repair temptation.** Once the check lives in algebra, the
   natural next move is "if a rotor isn't admissible, re-project it
   onto the frame cone."  That is exactly the hot-path repair
   CLAUDE.md §Normalization Rules forbids — grade projection,
   monitoring, watchdogs whose only purpose is to repair another
   function.

Algebra closure must stay structural; semantic admissibility belongs
upstream of algebra construction.

### Option C (rejected): `field/propagate.py` (precondition guard)

Enforce just before `propagate_step` commits the new field.  The
draft flagged the doctrinal risk:

> `field/propagate.py` is explicitly listed in CLAUDE.md as a
> forbidden site for normalization / drift repair / monitoring [...]
> An admissibility guard (raise on violation, never repair) is
> closer to a precondition than a monitor, but the boundary needs to
> be made explicit before this option is chosen.

Rejected.  Even framed as precondition, a check in
`field/propagate.py` blurs the rule and invites future "just one
more guard" additions.  The clean answer is to keep
`field/propagate.py` as the no-conditional-branching tight loop it
is documented to be.

### Option D (Accepted): `generate/rotor_admissibility.py`

A new sibling module to `generate/admissibility.py`, at the same
generation/propagation seam as ADR-0024's destination-side check.

**Why this is the right home:**

* **Same architectural seam as destination admissibility.**  Both
  rotor and destination checks operate at the boundary between
  candidate selection and field propagation.  They share infrastructure
  (the inner loop, the rejected_attempts trace, the
  `InnerLoopExhaustion` refusal mechanism) but live in distinct
  files, so the *concepts* stay separable even as the *seam* stays
  unified.
* **No layer-boundary crossing.**  `generate/` already depends on
  `algebra/` (it calls `versor_apply`, `word_transition_rotor`,
  `cga_inner`).  Putting rotor admissibility here keeps that
  dependency direction; Option B would have inverted it.
* **No hot-path repair temptation.**  The module's only public
  surface is `check_rotor_admissibility(region, field_current,
  rotor) -> RotorVerdict`.  It returns a typed verdict, doesn't
  mutate field state, doesn't repair anything.  The naming —
  *admissibility*, not *projection* or *normalization* — encodes
  the contract.
* **Trace parity with destination admissibility.**  Refusal flows
  through the same `InnerLoopExhaustion` plumbing wired in Phase 2,
  with a distinct `RefusalReason.ROTOR_REJECTION` so the trace names
  the axis that ran out without needing a parallel exception type.
* **File separation answers Option A's bloat objection.**
  Endpoint admissibility (token-side, blade) stays in
  `generate/admissibility.py`.  Rotor admissibility (rotor-side,
  frame) lives in `generate/rotor_admissibility.py`.  The inner loop
  in `generate/stream.py` calls both, but neither file grows the
  other's concerns.

---

## Decision

Rotor-side admissibility is enforced at the generation/propagation
seam by a new module:

```text
generate/rotor_admissibility.py
    RotorVerdict
    check_rotor_admissibility(region, *, field_current, rotor)
```

Wiring:

| Surface                                | Behavior                                                          |
|----------------------------------------|-------------------------------------------------------------------|
| `generate/stream.py` (threshold mode)  | Per-candidate rotor check after destination admit; on reject, log rotor score in `rejected_attempts`, retry next candidate, escalate to `InnerLoopExhaustion` with `reason=ROTOR_REJECTION` on exhaustion (iff *any* rotor rejection occurred) |
| `generate/stream.py` (margin mode)     | Rotor check on the top-ranked admissible candidate; on reject, immediate `InnerLoopExhaustion(reason=ROTOR_REJECTION)` carrying the destination ranking plus the rejected rotor's score |
| `generate/exhaustion.py`               | `RefusalReason.ROTOR_REJECTION` enum member (Phase 2 plumbing carries it through traces unchanged) |
| `docs/runtime_contracts.md`            | "Rotor admissibility contract" subsection documenting the seam, the algorithm, and the refusal taxonomy |

The check itself:

```text
score = cga_inner(versor_apply(V, F_current), region.frame_versor)
admit iff score > 0   (basic positivity in the frame half-space)
```

A region with `frame_versor is None` (or null-norm) trivially admits
every rotor with `score = +inf` — backward-compatible with every
pre-Phase-4 region in the codebase.

---

## Why Phase 4 keeps positivity (not margin) on the rotor side

Phase 3 / ADR-0026 replaced the static-threshold destination check
with ranked-with-margin because Phase 4 characterization established
that blade norms varied ~10× across cases, making a single absolute
threshold geometrically invalid.

The rotor side does not yet have an equivalent corpus.  The Phase 4
rotor check uses a simpler positivity bar (`score > 0`) — a strict
"the rotor lands in the frame's half-space" test — because:

1. **There is no cross-case calibration evidence to inform a margin
   constant yet.**  Picking a rotor-margin `delta` today would be
   guessing.
2. **Positivity is the doctrinally cleanest semantic bar.**  Either
   the post-rotor field stays in the frame's positive cone or it
   doesn't; there is no static threshold to be wrong about.
3. **Phase 5 (diversified failure-mode families) is the right place
   to surface whether rotor-side margin matters.**  If a family
   shows that rotor scores cluster near zero (margin signal weak),
   the finding is architectural and motivates a rotor-margin
   extension at that point.

ADR-0026's margin is preserved on the destination side; rotor side
stays at positivity until evidence demands otherwise.

---

## Invariants preserved

* **`versor_condition(F) < 1e-6`** — `check_rotor_admissibility`
  does not mutate field state; the closure invariant is the algebra
  layer's responsibility on the actual `propagate_step`, which only
  runs after an admitted rotor.  Test
  `tests/test_rotor_admissibility.py::TestGenerateRotorAdmissibility::test_versor_condition_preserved_on_admitted_rotor`
  pins this.
* **Deterministic replay** — rotor refusal carries the same evidence
  shape as destination refusal (the typed exception + canonical
  trace step).  Tests
  `TestRotorAdmissibilityDeterminism::{test_admitted_rotor_replay_stable,test_rotor_refusal_replay_stable}`
  assert 5-run replay equality for both admitted and refused turns.
* **No new code in `field/propagate.py`, `algebra/versor.py`,
  `vault/store.py`.**  Phase 4's surface is `generate/`-local.
* **No approximate recall, no cosine similarity, no HNSW/ANN.**
  Only `cga_inner` and `versor_apply`, both already in the runtime
  path.
* **Honest refusal preserved** — `RefusalReason.ROTOR_REJECTION` is
  a new enum member, not a string; the typed-exception subclass
  hierarchy (`InnerLoopExhaustion` ⊂ `ValueError`) is unchanged, so
  every pre-Phase-4 `except ValueError` handler continues to catch
  rotor refusals byte-identically.

---

## Trust boundary

`generate/rotor_admissibility.py` has no I/O, no learned state, no
dynamic imports.  It consumes `AdmissibilityRegion.frame_versor` (a
numpy array from pack-derived construction) and the current
`FieldState.F` (from upstream runtime).  No new external surface;
the trust boundary of ADR-0022 / ADR-0024 applies unchanged.

---

## Teaching boundary

**Stance A confirmed: hygiene-only.**  Rotor rejections, like
destination rejections, are deterministic geometric outcomes derived
from intents and frames.  They are not reviewed teaching examples and
do not enter the teaching loop.  CLAUDE.md §Teaching Safety forbids
parallel correction paths; entangling rotor rejection with reviewed
teaching would create exactly that.

If a corpus emerges where rotor admissibility consistently rejects
under conditions the operator considers wrong, the fix is to change
the *region construction* (the upstream pack-grounded geometry that
produces the frame versor), not the rotor check itself.

---

## Acceptance evidence

* **No-frame back-compat.** A region with `frame_versor is None`
  produces identical tokens before and after Phase 4.
  `TestGenerateRotorAdmissibility::test_no_frame_versor_preserves_phase3_behavior`.
* **Admit when aligned.** `frame_versor = seed direction` admits
  the seed→destination rotor; the field stays in the seed-aligned
  half-space.
  `test_frame_aligned_with_seed_admits`.
* **Refuse with named axis when misaligned.** An orthogonal frame
  versor refuses via `InnerLoopExhaustion(reason=ROTOR_REJECTION)`,
  not `INNER_LOOP_EXHAUSTION`.
  `test_frame_orthogonal_refuses_with_rotor_rejection`,
  `test_threshold_mode_rotor_rejection_routes_reason`.
* **`versor_condition` preserved.**
  `test_versor_condition_preserved_on_admitted_rotor` asserts
  `< 1e-6` on the final field state of an admitted run.
* **Deterministic replay.** 5-run replay equality for both admitted
  and refused turns.
  `TestRotorAdmissibilityDeterminism`.
* **Suite green.** 1048 passed, 2 skipped on `core test --suite
  full -q` (+11 new rotor tests over the post-Phase-3 baseline of
  1037).

---

## Out of scope

* **Rotor-side margin.**  Phase 4 keeps positivity (`score > 0`).
  Promotion to ranked-with-margin awaits Phase 5 evidence.
* **Region construction for frame versors.**  This ADR enforces the
  check; it does not specify *what* frame versors a given intent
  produces.  Frame derivation lives upstream (intent ratification,
  proposition graph) and is out of scope here.
* **Rotor-side teaching.**  Stance A above.
* **`ChatRuntime.respond()` materialisation.**  The Phase 2
  residual silent path (the `except ValueError: return ""` in
  `respond()`) still applies to rotor refusals.  Materialising
  `refusal_reason` on `ChatResponse` is a future ADR.

---

## Risks

* **Frame versor mis-specification upstream.**  A wrongly-constructed
  frame versor will refuse rotors that should admit, surfacing as
  `ROTOR_REJECTION` exhaustion on real turns.  Mitigation: the
  trace names the axis (`ROTOR_REJECTION` ≠ `INNER_LOOP_EXHAUSTION`),
  so debugging starts at frame construction, not admissibility logic.
* **Positivity bar may be too strict.**  Some legitimate rotors may
  land at `score == 0` exactly (boundary of the cone).  Phase 4's
  bar `score > 0` refuses these.  Promoting to `score >= 0` is one
  edit if evidence motivates it; left at strict `>` to mirror the
  load-bearing strict-`>` tie-break elsewhere.
* **Cost.**  Each per-candidate rotor check is one
  `versor_apply` + one `cga_inner`.  In threshold mode this adds at
  most `len(admissible_set)` extra applies per step; in margin mode,
  exactly one extra apply per step.  No approximation introduced.

---

## Rollback

Construct regions with `frame_versor=None` (or omit the field, which
defaults to `None`).  The rotor check returns trivial admit with
`score = +inf` and the runtime behaves identically to ADR-0026 /
Phase 3.  No trace-hash migration required.

---

## Evidence and links

* ADR-0022 — Forward Semantic Control (region prefilter)
* ADR-0023 — FSC proof evidence
* ADR-0024 — Inner-loop per-rotor admissibility (token-side)
* ADR-0026 — Ranked admissibility with margin (Phase 3)
* `generate/rotor_admissibility.py` — the module
* `tests/test_rotor_admissibility.py` — 11 tests pinning the contract
* `docs/runtime_contracts.md` §"Rotor admissibility contract"
