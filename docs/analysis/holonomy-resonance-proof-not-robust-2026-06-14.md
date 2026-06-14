# Finding: the holonomy tri-language "resonance proof" is not robust

**Date:** 2026-06-14
**Status:** substrate finding (load-bearing for the CORE-Logos roadmap and the
field-as-reasoner research track). Triggered by W-Holonomy ("make the crown
proof legible in the Studio"): measuring the real geometry before building the
UI showed there is **no robust proof to make legible yet.**

## Claim under test

The "crown proof" of the three-language design (`HolonomyAlignmentCase`,
`language_packs/schema.py`): *aligned canonical clauses across Hebrew / Greek /
English produce nearby holonomies — closer than a misaligned negative — without
flattening their distinctions.* The flagship case is HAC-001:
`word/דבר/λόγος + beginning/ראשית/ἀρχή + truth/אמת/ἀλήθεια`, negative = truth→ζωή
(vitality). Encoding via `algebra.holonomy.holonomy_encode`; comparison metric
in question.

## Measurements (deterministic; re-encode is bit-identical)

**1. The engine's own metric (`holonomy_similarity` = CGA inner product) anti-correlates.**

| pair | `holonomy_similarity` |
|---|---|
| anchor(en) ↔ aligned(he) | −14.49 |
| anchor(en) ↔ aligned(grc) | −159.93 |
| anchor(en) ↔ **negative**(grc, ζωή) | **+122.63** |

Aligned mean **−87.2** vs negative **+122.6** → the *misaligned* clause scores as
**more** similar. The owned metric says the opposite of the claim.

**2. The Euclidean norm "passes" only via an averaging artifact + one cherry-picked negative.**

- aligned Greek alone: `‖en − grc_aligned‖ = 56.85`
- misaligned negative: `‖en − grc_ζωή‖ = 43.63`
- → the **aligned** Greek clause is **farther** from the anchor than the misaligned one.
- The original test passed only because it averaged in the close Hebrew distance
  (`‖en − he‖ ≈ 29.3`): `mean(29.3, 56.85) = 43.07 < 43.63` — a **1.3%** margin.

**3. Swapping the negative flips the verdict wildly** (per-component, grc 3rd token swapped):

| negative token | `‖en − grc_neg‖` | aligned(56.85) closer? | margin |
|---|---|---|---|
| ζωή (vitality) | 43.63 | no | −23.3% |
| ἀρχή (beginning) | 25.71 | no | −54.8% |
| λόγος (word) | 68.40 | yes | +20.3% |

## Conclusion

The `HolonomyAlignmentCase` obligation is **decoration, not proof** by CLAUDE.md's
own bar (*Schema-Defined Proof Obligations*: "A test that passes under conditions
that bypass the obligation it nominally proves is decoration, not proof"). The
passing test `test_holonomy_alignment_case_positive_closer_than_negative` holds
only for one averaged configuration and one negative, at a 1.3% margin, and
inverts under equally-valid alternatives. Under the engine's own similarity
metric it inverts entirely.

**Therefore:**
- A Studio "Holonomy proof-card" tab cannot be built honestly. Rendering a "holds"
  verdict off this would be the impressive-but-ungrounded output CLAUDE.md forbids.
  Holonomy stays **honest-absent** (`missing_evidence`) in the Studio — which is
  exactly what LG-2/3/4 already do. Confirmed correct.
- The decoration test is **downgraded** (this PR) to assert only the true state —
  the resonance does **not** robustly separate aligned from misaligned — so the
  obligation is no longer silently green. It is a tripwire: if a future encoding
  makes the resonance robust, the guard fails and must be replaced by a real proof
  (and this doc updated).

## What a real proof would require (research, not wiring)

A legitimate holonomy resonance proof must robustly separate aligned from
misaligned across **many** clauses × **many** negatives, with a stable margin,
under a **single declared metric** (ideally the owned `holonomy_similarity`, or a
geometrically-justified alternative with a stated reason). The current encoding
does not do this even for the flagship example. This belongs in the deferred
**field-as-reasoner / content-stays-meaningful** research track, not the workbench
build. It is **not pitch-blocking** — holonomy is honestly absent regardless.

## Open research questions (for a bounded, falsifiable spike)

1. Is there a metric (normalized `holonomy_similarity`, geodesic distance on the
   Spin manifold, …) under which aligned robustly > misaligned across a corpus?
2. Is the per-token `_position_rotor` injection drowning the semantic signal in
   path-order geometry? (Aligned-grc being farther than a random negative hints
   the encoding is dominated by something other than meaning.)
3. Does the proof need a *clustering* formulation (aligned clauses mutually close,
   negative an outlier) rather than anchor-distance?

Any spike here is bounded and falsifiable: "does construction X separate aligned
from misaligned across N×M with margin ≥ τ?" — answerable, not open-ended.

## Tests downgraded in this PR

Two tests asserted the holonomy-**clause** resonance as if proven; both are
downgraded to honest tripwires that assert the *true* state (aligned clause
farther than the misaligned negative) and will fail — pointing back here — if a
future encoding makes the resonance real:

- `tests/test_alignment_graph.py::test_holonomy_alignment_resonance_is_not_yet_a_robust_proof`
  (was `..._positive_closer_than_negative` — the `HolonomyAlignmentCase`
  schema-defined obligation).
- `tests/test_holonomy_resonance.py::test_aligned_clause_holonomy_does_not_robustly_beat_misaligned`
  (was `test_aligned_clauses_have_higher_similarity_than_unrelated` — the
  identical averaged-distance artifact).

**Not audited here (separate, narrower claim):** the *token-pair* `cga_inner`
resonance tests — `test_triple_alignment_closer_than_other_triples`,
`test_light_alignment_clusters_across_mounted_trilingual_field`,
`test_same_root_hebrew_forms_land_closer_than_unrelated_noun`,
`test_structured_morphology_improves_same_root_hebrew_resonance`. These compare
*individual versors* (not multi-token clause holonomies), a different and
narrower property than the clause-resonance proof above. They currently pass;
whether each is robust or another cherry-picked configuration is an open
follow-up, not covered by this finding.
