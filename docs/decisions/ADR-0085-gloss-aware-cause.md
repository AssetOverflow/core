# ADR-0085 — Gloss-Aware CAUSE Composer

**Status:** Accepted
**Date:** 2026-05-20
**Author:** Shay

---

## Context

ADR-0084 ratified a definitional substrate: every opted-in pack carries
per-lemma `gloss` text alongside the existing `semantic_domains` tags,
closure-verified against a small primitives pack.  PR #65 (content) and
PR #68 (integration test) put 333 glosses on disk and pinned the
substrate↔content contract end-to-end.

DEFINITION and RECALL intents *already* consumed those glosses via the
pre-existing pack-grounded composer at
`chat/pack_grounding.py:398-434`.  Surfaces like *"What is light?"*
moved from `light — pack-grounded (...): cognition.illumination;
logos.core.` to `Light is visible medium that reveal truth.
pack-grounded (...).` with no further code change once the content
landed.

CAUSE intent (*"Why does light exist?"*) did not.  It dispatched through
`teaching_grounded_surface` / `teaching_grounded_surface_composed` /
`teaching_grounded_surface_transitive` — chain-walk composers that emit:

```
light — teaching-grounded (cognition_chains_v1):
  cognition.illumination; logos.core.
  light reveals truth (cognition.truth).
  No session evidence yet.
```

The chain-walk is structurally correct (every token is a ratified
lemma, domain tag, connective, or template constant) but the *shape*
is wrong for a *why* question — it's a graph traversal, not an
explanation.  The original user complaint that motivated ADR-0084 was
specifically about the CAUSE-shape mismatch.

The φ-separation result (memory: `phi-separation-falsified`) showed
that semantic capability lives in chain composition, not in φ
geometry.  ADR-0083 raised the *depth* of chain composition.  ADR-0084
raised the *fidelity* (definitions, not just domain tags).  ADR-0085
raises the *shape*: explanation-frame CAUSE surfaces from the same
definitional material.

---

## Decision

Add an additive, opt-in composer that frames CAUSE-intent answers from
the subject lemma's gloss instead of from chain-walk telemetry.  The
composer is *additive* — when no gloss exists for the subject lemma,
it returns `None` and dispatch falls through to the existing
chain-walk path.  No existing CAUSE case loses its surface.

### Composer

```python
def gloss_aware_cause_surface(
    lemma: str,
    pack_ids: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
    *,
    register: RegisterPack = UNREGISTERED,
    anchor_lens: AnchorLens = UNANCHORED,
) -> str | None:
    ...
```

Lives in `chat/pack_grounding.py` next to `pack_grounded_surface`.
Reuses `chat.pack_resolver.resolve_gloss` (lexicon-residency-checked)
and the existing anchor-lens annotation helper.

### Explanation frame

POS-aware, mirroring `_frame_gloss` but in explanation shape:

| POS | Frame |
|---|---|
| NOUN | `{Lemma} exists as {gloss}.` |
| VERB | `To {lemma} is to {gloss}.` |
| ADJ  | `To be {lemma} is to {gloss}.` |
| other | falls back to `_frame_gloss` (predicate-identity) |

Each surface ends with the existing `pack-grounded ({pack_id}).`
provenance marker.  Removing that marker from the user-facing surface
is the *surface-vs-envelope ADR*'s job, not this one.

### Runtime dispatch

```python
# chat/runtime.py — CAUSE intent dispatch
if (self.config.gloss_aware_cause
        and intent.tag is IntentTag.CAUSE):
    surface = gloss_aware_cause_surface(
        lemma, register=self.register_pack,
        anchor_lens=self.anchor_lens,
    )
    if surface is not None:
        return (surface, "pack", ())
# ... fall through to teaching_grounded_surface* chain-walk ...
```

The gloss path is tried FIRST under the flag.  Fall-through is
unconditional on `None` — never silent.

### Opt-in flag

```python
# core/config.py
@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    ...
    # ADR-0085 — gloss-aware CAUSE surface.
    gloss_aware_cause: bool = False
```

Default `False` preserves pre-ADR-0085 surfaces byte-identically
(null-drop invariant — CI-pinned via
`TestCognitionLaneInvariance::test_flag_off_metrics_byte_identical`).

---

## Verification

### Required tests (all in `tests/test_adr_0085_gloss_aware_cause.py`)

- Pure composer:
  - NOUN-glossed lemma returns `"{Lemma} exists as {gloss}."` frame.
  - VERB-glossed lemma returns `"To {lemma} is to {gloss}."` frame.
  - Unknown / empty lemma returns `None`.
  - Surface carries no chain-walk artifacts (`teaching-grounded`,
    `No session evidence yet`, dotted domain tags).
- Runtime dispatch:
  - Flag off → CAUSE prompt produces `teaching-grounded (...)` surface
    (chain-walk preserved byte-identically).
  - Flag on → CAUSE prompt produces `exists as` explanation surface
    with grounding source `pack`.
  - Flag on across multiple glossed subjects (`light`, `knowledge`,
    `wisdom`) all shift to explanation frame.
  - VERIFICATION intent unchanged under flag (CAUSE-only scope).
  - Lemma without gloss still produces a non-empty surface under
    flag (chain-walk fallback engages).
- Cognition lane invariance:
  - Aggregate metrics byte-identical under both flag states.
  - CAUSE-case *surfaces* deliberately shift under flag (the
    structural change), while every counted metric is invariant
    (the null-drop guarantee).

### Lanes (regression check)

```
core test --suite smoke -q       67 passed
core test --suite cognition -q   120 passed, 1 skipped
core test --suite packs -q        6 passed
core test --suite teaching -q    17 passed
core test --suite runtime -q     19 passed
core eval cognition              byte-identical 100/91.7/100/100
                                 under both flag states
```

### Prompt-diversity lift (flag ON vs flag OFF, v1/public/26 cases)

| Metric | OFF | ON | Δ |
|---|---|---|---|
| `intent_accuracy` | 65.4% | 65.4% | — |
| `versor_closure_rate` | 100.0% | 100.0% | — |
| `response_shape_fit` | 57.7% | 57.7% | — |
| `audit_in_surface_rate` | 42.3% | 42.3% | — |
| `gloss_quote_rate` | 11.5% | **23.1%** | **+11.5pp** |

`gloss_quote_rate` doubles — the structural lift on CAUSE-shape cases.
`response_shape_fit` stays flat because the prompt-diversity
classifier was updated in the same PR to recognize the explanation
frame (`exists as`, `is to`, etc.) alongside the existing chain-walk
markers — neither frame is penalised relative to the other.

---

## Consequences

### What changes

- `chat/pack_grounding.py` — new `gloss_aware_cause_surface()`
  composer + new `_frame_cause_gloss()` POS-aware explanation frame
  helper.
- `chat/runtime.py` — CAUSE dispatch tries the gloss path first under
  the flag, falls through to chain-walk on `None`.
- `core/config.py` — `RuntimeConfig.gloss_aware_cause: bool = False`.
- `evals/prompt_diversity/runner.py` — explanation-frame markers
  (`exists as`, `is to`, etc.) added to `_CAUSE_MARKERS` so
  `response_shape_fit` measures the new shape correctly.

### What does not change

- VERIFICATION intent dispatch.  ADR-0085 is CAUSE-only.
- DEFINITION / RECALL composers.  Already gloss-aware via
  `pack_grounded_surface`.
- NARRATIVE / EXAMPLE composers.  Out of scope; their composers
  (`chat.narrative_surface`, `chat.example_surface`) walk teaching
  corpora in a way that's not a one-line frame swap.  Future ADR.
- The chain-walk composers (`teaching_grounded_surface*`).  Still the
  fallback for CAUSE cases where no gloss exists.
- `versor_condition(F) < 1e-6` invariant.  Unchanged — no algebra
  edits.
- ADR-0073 anchor lens engagement.  The composer threads the lens
  through `_maybe_append_anchor_lens_annotation` exactly as the
  DEFINITION composer does.

### What stays out of scope

- **Surface-vs-envelope cleanup.** The `pack-grounded ({pack_id}).`
  provenance marker still leaks into the user surface.  Removing it
  to telemetry-only is a separate ADR's job (the prompt-diversity
  contract's `audit_in_surface_rate` metric pins this for the future
  PR).
- **Predicate-licensing.** ADR-0085 does not yet *check* that the
  gloss text uses only predicates from the lemma's
  `predicates_invited` list.  That's ADR-0086.  Today the gloss is
  trusted to be coherent because it was ratified through the
  closure-rule gate at content time.
- **Content style.** Some glosses today read as `"what support truth"`
  rather than `"what supports truth"` — bare-lemma forms instead of
  inflected English.  A content-style pass is queued as a follow-up
  brief to the content agent; the substrate doesn't change.

---

## Scope limits

- **CAUSE intent only.**  VERIFICATION still chain-walks (different
  shape — yes/no, not explanation).
- **English pilot only.**  Greek/Hebrew cognition packs (`grc_*` /
  `he_*`) are not opted into the definitional layer yet (deferred per
  ADR-0084 scope limit); they continue to use the chain-walk under
  this flag.
- **Single-lemma subjects.**  Compound or anaphoric CAUSE subjects
  fall through to the chain-walk path.
- **Opt-in.**  Default off until the cognition holdout split confirms
  the lift transfers off-fixture; this can be flipped on by default
  in a follow-up after holdout numbers settle.

---

## Why now

ADR-0084 made the substrate available; ADR-0085 lets the realizer use
it on the load-bearing intent.  CAUSE was the original complaint
target (*"Why does light exist?"*); shipping it second after the
substrate is the natural sequencing — substrate first, consumer
second.

ADR-0085 is also the smallest possible step toward the realizer
becoming "richer in material" without introducing a normalization
layer or coupling the realizer to geometric state.  It's purely a
*frame swap on existing pack-resident material* — same gloss text,
same provenance, different sentence shape.

---

## Cross-References

- [ADR-0084](./ADR-0084-definitional-layer.md) — the substrate this
  consumes.  Without 0084 there is no gloss to frame.
- [ADR-0083](./ADR-0083-transitive-chain-surface.md) — raised the
  *depth* ceiling on chain composition; 0085 raises the *shape*
  ceiling on CAUSE-frame composition.
- [ADR-0048](./ADR-0048-pack-grounded-surface.md) — original
  pack-grounded surface for DEFINITION / RECALL; the gloss path was
  wired here pre-content.
- `evals/prompt_diversity/contract.md` — the measurement instrument
  that proves this lift quantitatively.
- Future ADR-0086 — predicate licensing at ratification (will
  constrain which predicates the realizer may invoke given a lemma's
  `predicates_invited` list).
- Future surface-vs-envelope ADR — will move
  `pack-grounded ({pack_id}).` from surface to telemetry; ADR-0085's
  surface format will need to update one line when that lands.
