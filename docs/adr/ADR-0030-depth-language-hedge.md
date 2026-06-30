# ADR-0030: Depth-Language Hedge Wiring

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`identity_packs.md`](../identity_packs.md), [`ADR-0028-identity-surface-wiring.md`](ADR-0028-identity-surface-wiring.md)

## Context

[ADR-0028](ADR-0028-identity-surface-wiring.md) wired pack `surface_preferences` into the English assembler so that swapping identity packs produced visibly different English surfaces. ADR-0028 §"Scope limits" explicitly flagged the gap:

> **English-only differentiation.** `_assemble_he` and `_assemble_grc` do not currently consult `SurfaceContext` for hedge/claim-strength shaping; they call neither `_apply_hedge` nor anything sensitive to the new fields. Per-language hedging is a future concern; identity packs are language-neutral, so the same preferences will eventually drive the same logic in `_assemble_he` and `_assemble_grc` once those gain hedge support.

CORE's three-language foundation (English, Hebrew, Koine Greek) is not a localization concern — it's an architectural commitment, called out in the Whitepaper and CLAUDE.md. Leaving Hebrew and Greek surfaces unaffected by the identity pack contradicts the architecture: identity is load-bearing, but only on one of the three first-class languages? That's the wrong shape.

This ADR closes the gap.

## Decision

Apply the same four-band hedge/claim-strength algorithm to Hebrew and Koine Greek surfaces. Same thresholds from the identity pack. Same `claim_strength` policy. Language-appropriate hedge surface strings.

### Phrase ownership

Hedge phrases for English live on `SurfaceContext` (lifted from the pack's `surface_preferences` block — ADR-0028). Hedge phrases for Hebrew and Koine Greek live as module-level constants in `generate/surface.py`:

```python
_DEPTH_HEDGE_PHRASES: dict[str, tuple[str, str, str]] = {
    "he": (
        "נראה ש",         # strong — "nir'eh she" — it seems that
        "אולי",                  # soft   — "ulai" — perhaps
        "במקרים מסוימים,",  # qualifier — "in some cases,"
    ),
    "grc": (
        "δοκεῖ ὅτι",  # strong — "dokei hoti" — it seems that
        "ἴσως",                              # soft   — "isos" — perhaps
        "ἐνίοτε,",                # qualifier — "eniote," — at times,
    ),
}
```

This is deliberate: at v1, depth-language phrases are *canonical* — every pack uses the same Hebrew strong-hedge phrase, the same Greek soft-hedge phrase, etc. Pack-supplied overrides per language would require either (a) extending the pack schema to carry a `languages` block, or (b) lifting depth-language phrases out of `surface.py` into language packs. Both are larger architectural moves; neither belongs in this ADR. The current arrangement is the minimum that closes the ADR-0028 gap.

### What pack swap *does* affect in Hebrew/Greek

Even though the phrases themselves are canonical, pack swap still visibly affects depth-language output because **thresholds and claim_strength come from the pack**:

| Alignment | default_general_v1 (he) | precision_first_v1 (he) | generosity_first_v1 (he) |
|---|---|---|---|
| 0.30 | strong hedge "נראה ש" | strong hedge "נראה ש" | bare (above generosity's strong 0.20) |
| 0.45 | soft hedge "אולי" | strong hedge "נראה ש" (precision's strong is 0.55) | bare (above generosity's soft 0.30) |
| 0.60 | bare | soft hedge "אולי" (precision's soft is 0.70) | bare |
| 0.80 | bare | qualifier "במקרים מסוימים," (precision is qualified, marginal band 0.70–0.85) | bare |

Same trajectory through the manifold → three different Hebrew surfaces depending on which pack is selected. Same for Greek. Test `TestDepthPackSwapDivergence::test_hebrew_pack_swap_visible_at_alignment_0p45` asserts this explicitly.

### Algorithm

`_apply_hedge` gains a `lang` parameter (defaulting to `"en"` so existing callers are unaffected):

```python
def _apply_hedge(surface: str, ctx: SurfaceContext, lang: str = "en") -> str:
    alignment = ctx.identity_alignment
    if lang in _DEPTH_HEDGE_PHRASES:
        strong, soft, qualifier = _DEPTH_HEDGE_PHRASES[lang]
    else:
        strong = ctx.preferred_hedge_strong
        soft = ctx.preferred_hedge_soft
        qualifier = ctx.preferred_qualifier
    # ... four-band algorithm unchanged ...
```

`_assemble_he` and `_assemble_grc` gain `ctx: SurfaceContext | None` parameters and call `_apply_hedge` with the appropriate `lang` when `ctx is not None`. When `ctx is None` (legacy callers, mostly tests), no hedge is applied and behavior is byte-for-byte preserved.

### Backward compatibility

- **`_apply_hedge` callers passing only two arguments** continue to work — `lang` defaults to `"en"`.
- **English surface output is unchanged** because the English branch falls through to the same `ctx.preferred_hedge_*` fields it consulted before.
- **`_assemble_he` / `_assemble_grc` callers passing `ctx=None`** get the pre-ADR Hebrew/Greek surface byte-for-byte. The test class `TestBackwardCompatibility` in `tests/test_identity_surface_divergence_depth.py` asserts this.
- **Existing cognition / runtime / smoke / formation / teaching suites** are green at the ADR landing revision.

### What this ADR does *not* do

- **Does not introduce a `languages` block in the identity-pack schema.** Per-pack depth-language phrase overrides are deferred. A future ADR may add them once a concrete need emerges (e.g., a robotics deployment needs a different Hebrew hedge phrase for their domain). The current `_DEPTH_HEDGE_PHRASES` is a canonical default, not a hardcoded ceiling.
- **Does not extend `_apply_contrast` ("However, ...") or `_apply_subordination` ("Given that ..., ...") to Hebrew / Greek.** Those would need translations and grammar considerations beyond hedge phrases. Hedge phrases are the dominant differentiator; the others are nice-to-have.
- **Does not change Hebrew or Greek grammar / word order.** The existing `_assemble_he` and `_assemble_grc` constructions (VSO for Hebrew, SOV for Greek) are preserved verbatim. ADR-0030 only prefixes a hedge phrase to whatever the existing assembler produced.

## Consequences

### Positive

- **Identity is now load-bearing across all three foundational languages.** The ADR-0027 → ADR-0028 → ADR-0030 chain closes the loop: identity packs are swappable (0027), the swap visibly affects English surfaces (0028), and now Hebrew and Greek surfaces too (0030). The architectural claim that "identity informs doing" applies uniformly across CORE's three-language foundation.
- **Same algorithm, same thresholds, same claim_strength policy.** Operators reasoning about "when does this pack hedge?" don't need to track per-language exceptions. One mental model.
- **Pure addition.** No existing test changed; no existing surface output changed. New behavior only emerges when callers explicitly pass `ctx` to depth-language assemblers and the alignment falls in a hedging band.

### Negative / risks

- **Phrases are canonical, not pack-overridable.** A future deployment that wants `"ייתכן ש"` instead of `"נראה ש"` for their Hebrew strong-hedge can't supply it without an ADR-0030 follow-up. The current set was chosen as the lexically simplest and most theologically neutral options.
- **Hebrew RTL rendering can look strange in terminals that don't bidi correctly.** The string is logically correct (hedge first in memory), but terminal display may visually reorder. Tests assert on byte content, not visual order, so this is a presentation-layer concern, not a correctness one.
- **`_lower_first` is a no-op for Hebrew (unicameral) and a real transform for Greek (case-bearing).** Calling it uniformly is correct but worth noting: a future ADR introducing depth-language pre-formatting may need to revisit.
- **The phrase set is small** — three phrases per depth language. A richer set (sentence-final hedges, different forms by mood, etc.) is a future concern.

### Scope limits (explicit non-goals for this ADR)

- No depth-language contrast ("However, ..." equivalent in Hebrew / Greek).
- No depth-language subordination ("Given that ..., ..." equivalent).
- No per-pack depth-language phrase overrides.
- No grammar-aware hedge placement (e.g., putting a hedge after the first verb instead of sentence-initial).

## Verification

- `tests/test_identity_surface_divergence_depth.py` — 15 tests covering Hebrew hedge bands, Greek hedge bands, pack-swap divergence in both languages, three-language hedge phrase distinctness, and backward compatibility under `ctx=None`.
- Cognition (121), teaching (17), runtime (19), formation (182), smoke (67) suites green at the same revision.
- `tests/test_identity_surface_divergence.py` (ADR-0028) — 15 tests still passing (English regression check).
