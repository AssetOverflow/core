# ADR-0031: Score-Decomposition Surface — Per-Axis Hedge Phrases

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`identity_packs.md`](../identity_packs.md), [`ADR-0028-identity-surface-wiring.md`](ADR-0028-identity-surface-wiring.md), [`ADR-0030-depth-language-hedge.md`](ADR-0030-depth-language-hedge.md)

## Context

[ADR-0028](ADR-0028-identity-surface-wiring.md) and [ADR-0030](ADR-0030-depth-language-hedge.md) made identity-pack swap visibly affect the surface across English, Hebrew, and Koine Greek. But the differentiation today consults a **single scalar** — `SurfaceContext.identity_alignment`. The system can hedge harder when the trajectory drifts; it cannot say *which* aspect of identity is at issue when it hedges.

`IdentityScore` already carries the information we need: `deviation_axes: FrozenSet[str]` names the specific axes the `IdentityCheck` flagged. Today that field is computed and then ignored at the surface layer. Wiring it through closes the gap: when the system hedges on a trajectory whose deviation is *truthfulness*, the hedge can read "Evidence is thin that…"; on a *coherence* deviation, "This does not yet cohere:…"; on *reverence*, "Reports suggest…". The user learns *why* the system is hedging.

This is the score-decomposition surface.

## Two interpretations considered

**Interpretation A — Dominance-driven phrasing.** Every assertion's character shifts based on which axis is the *leader* of the manifold. Truthfulness-dominant identity → precise phrasing on every assertion; coherence-dominant → unifying phrasing; reverence-dominant → deferential. Rejected for this ADR: requires new dominance scoring, changes confident assertions too (large blast radius), and isn't structurally connected to anything already computed.

**Interpretation B — Deviation-driven hedge phrasing (this ADR).** When the hedge band fires *and* the score reports a specific deviating axis for which the pack supplies an `axis_hedges` entry, the assembler uses that axis's phrase instead of the generic `preferred_hedge_*`. Otherwise the ADR-0028 generic phrase fires. The data we need (`deviation_axes`) already exists; we just plumb it through.

Interpretation A is preserved as a future possibility — nothing in this ADR forecloses it. The pack schema extension is named `axis_hedges` (not `axis_phrasing`) precisely so a future "axis phrasing" concept doesn't collide.

## Decision

### Pack schema extension (optional, additive)

A new optional `axis_hedges` sub-block inside `surface_preferences`:

```json
"surface_preferences": {
  "...existing ADR-0028 fields...": "...",
  "axis_hedges": {
    "truthfulness": {
      "strong":    "Evidence is thin that",
      "soft":      "It is hard to confirm that",
      "qualifier": "Where evidence is partial,"
    },
    "coherence": {
      "strong":    "This does not yet cohere:",
      "soft":      "The threads loosely connect:",
      "qualifier": "Where the connection holds,"
    },
    "reverence": {
      "strong":    "Reports suggest",
      "soft":      "It is said that",
      "qualifier": "By some accounts,"
    }
  }
}
```

Each axis entry is keyed by `axis_id` (must match an existing `value_axes[*].axis_id` semantically, though the loader doesn't enforce that — a pack may declare hedges for axes it doesn't expose, which is harmless because no deviation will reference them). Each entry has three required phrases: `strong`, `soft`, `qualifier`, matching the three bands of the ADR-0028 hedge algorithm.

### Selection algorithm

When the English hedge band fires (after threshold gating):

1. Compute `matching_axes = ctx.deviation_axes ∩ {ah.axis_id for ah in ctx.axis_hedges}`.
2. If `matching_axes` is empty → use the pack's generic `preferred_hedge_*` (ADR-0028 behavior).
3. Otherwise → use the **lex-smallest** matching axis's phrase. The loader emits `axis_hedges` in lex order on `axis_id` for hashability + determinism; the assembler does a linear scan and takes the first match, which is the lex-smallest.

Lex tie-break is deliberate: when multiple axes deviate, the assembler must pick one phrase. Lex order is the simplest deterministic choice that doesn't require additional scoring. If a deployment cares about a different priority (e.g., "always prefer the truthfulness phrase when truthfulness is among the deviators"), they can re-key their `axis_hedges` so the preferred axis sorts earliest (`a_truthfulness`, `b_coherence`, …) — operational discipline, not architectural.

### Three v1 pack profiles

Each pack ships its own English `axis_hedges` block tuned to its character:

| Pack | Truthfulness strong | Coherence strong | Reverence strong |
|---|---|---|---|
| `default_general_v1` | "Evidence is thin that" | "This does not yet cohere:" | "Reports suggest" |
| `precision_first_v1` | "The evidence does not support that" | "This contradicts what is established:" | "Source attestation is weak:" |
| `generosity_first_v1` | "Some hold that" | "There is a thread connecting this:" | "It is reported that" |

Result at `alignment=0.30` (strong band) with `deviation_axes={"truthfulness"}`:

| Pack | Surface |
|---|---|
| `default_general_v1` | "Evidence is thin that truth reveals reality." |
| `precision_first_v1` | "The evidence does not support that truth reveals reality." |
| `generosity_first_v1` | "Truth reveals reality." *(generosity's strong threshold is 0.20; 0.30 is above the hedge band so no phrase prepends regardless of deviation)* |

Same trajectory, same deviating axis, three different surfaces.

### Implementation

- `core/physics/identity.py`: new `AxisHedge` frozen dataclass (strong / soft / qualifier strings); `SurfacePreferences` gains `axis_hedges: Tuple = ()` field (tuple of `(axis_id, AxisHedge)` pairs, lex order).
- `packs/identity/loader.py`: `_build_axis_hedges()` parses the optional sub-block, bounds-checks each phrase via the existing `_validate_hedge_phrase` (length 1–64), emits pairs in lex order on `axis_id`.
- `generate/surface.py`: `SurfaceContext` gains two new frozen-and-hashable fields — `deviation_axes: frozenset[str]` and `axis_hedges: tuple[tuple[str, str, str, str], ...]` (flattened quadruples for hashability). New helper `_axis_specific_phrase(ctx)` returns the lex-smallest matching axis's `(strong, soft, qualifier)` or `None`. `_apply_hedge` consults it before falling back to ADR-0028 generic phrases.
- `chat/runtime.py::ChatRuntime._build_surface_context`: lifts `identity_score.deviation_axes` and `prefs.axis_hedges` into the constructed `SurfaceContext`.
- `packs/identity/*.json`: three v1 packs gain `axis_hedges` blocks. Pack body changed → re-ratified.

### Re-ratification

Adding `axis_hedges` to each pack changed the canonical body → new `pack_source_sha` → new `MasteryReport`. `scripts/ratify_identity_packs.py` handled it idempotently. Updated SHAs:

- `default_general_v1` → `2ab7d469013509ba5030313ca9a609a443d0716e3ddcc5596f59858ce054f5d3`
- `precision_first_v1` → `78aa1e6a68a35c2c8576b6196a52d421b94f6d11e006128986902a4fd08679af`
- `generosity_first_v1` → `511f1ce20edd4266239da61443bfc93473a5433f20bfee6692a25a03073dc933`

## Consequences

### Positive

- **Hedges now name what's at issue.** When the system hedges on a trajectory whose truthfulness axis is flagged, the user reads "Evidence is thin that…" — the refusal text is informative, not a generic disclaimer. This is meaningfully better epistemic communication.
- **Per-axis hedges are pack-tuned.** A precision-first deployment hedges with evidential vocabulary; a generosity-first deployment hedges by attribution to "some". Same architecture, different voice.
- **Forward-compatible with Interpretation A.** Dominance-driven phrasing (when a single axis *leads* rather than *deviates*) would slot in alongside `axis_hedges` without changing this ADR's shape.
- **No new scoring infrastructure.** `IdentityScore.deviation_axes` already existed; this ADR is purely plumbing + a phrase table.
- **Backward compatible at every layer.** Packs without `axis_hedges` fall through to ADR-0028 byte-for-byte. `SurfaceContext()` (no-args) carries `deviation_axes=frozenset()` and `axis_hedges=()`, so legacy callers see no behavioral change.

### Negative / risks

- **English-only at v1.** Depth languages still use the canonical `_DEPTH_HEDGE_PHRASES` from ADR-0030 regardless of which axis deviates. Closing this requires either a pack-schema bump (axis_hedges per language) or canonical depth-language axis hedges in `surface.py`. Both are tractable; neither belongs in this ADR.
- **Lex tie-break is operational, not semantic.** When multiple axes deviate simultaneously, the chosen phrase is whichever axis_id sorts earliest — not necessarily the "most relevant" one. Deployments that need a different priority must use operational discipline (re-keying axis_ids) or wait for a follow-up ADR introducing per-pack axis priority.
- **Pack body grew.** Three new phrases per axis × three axes = nine new strings per pack. The canonical JSON is still well under any practical size limit, and the ratification driver handled the change without issue.
- **`SurfaceContext` is bigger again.** Two more fields. Both have safe defaults so direct `SurfaceContext()` construction in tests continues to work.

### Scope limits (explicit non-goals for this ADR)

- No per-language axis hedges. v1 axis_hedges are English-only.
- No dominance-driven phrasing (Interpretation A). Phrasing changes only when the score reports deviation, not when a particular axis happens to lead.
- No per-pack axis priority. Lex order is the tie-break.
- No realizer-side use of `deviation_axes` beyond hedging (no rotor bias, no token selection shift, no separate refusal surface).

## Verification

This ADR is satisfied when:

- `tests/test_identity_score_decomposition.py` passes — 17 tests covering per-axis phrase selection, band gating still applies, pack-swap with deviation, lex tie-break, depth-language fallback, backward compatibility, and the contract that all three v1 packs ship axis_hedges for all three default axes.
- Cognition (121), teaching (17), runtime (19), formation (182), smoke (67) suites green.
- `tests/test_identity_surface_divergence.py` (ADR-0028) and `tests/test_identity_surface_divergence_depth.py` (ADR-0030) — both still passing (no regressions in the generic-phrase or depth-language paths).
- All three v1 identity packs re-ratified with the new SHAs recorded above.
