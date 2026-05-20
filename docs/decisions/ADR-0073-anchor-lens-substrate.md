# ADR-0073 — Anchor lens: substrate-driven substantive variation

**Status:** Proposed
**Date:** 2026-05-19
**Author:** Shay
**Phase:** Plan Phase L1 (anchor lens, inside-out)
**Builds on:** ADR-0048 (pack-grounded surface), ADR-0050 (COMPARISON),
ADR-0052 (teaching-grounded surface), ADR-0063 (cross-pack resolver),
ADR-0064 (cross-pack teaching), ADR-0068..0072 (register subsystem)
**Composes against:** the register axis (ADR-0068..0072) as an
*orthogonal* axis — register varies surface text, anchor lens varies
the *proposition itself*.

---

## Context

The register subsystem (R1–R5) closed the **presentation axis**: same
truth, different wording.  That is cosmetic by design — every
register holds `grounding_source` and `trace_hash` byte-identical
across {neutral, terse, convivial} for the same input (`core demo
register-tour` asserts this turn-by-turn).

The original deterministic-AI critique CORE answers (`identity informs
doing`, `truth is coherent`) asks for something stronger: the system
saying **genuinely different things from different conceptual
substrates**, not the same thing in different clothes.  That axis is
**substantive variation**.

The substrate to deliver it already sits half-built on disk.

* `language_packs/data/grc_logos_micro_v1` (11 entries, alignment),
  `grc_logos_cognition_v1` (20 entries, **no alignment**),
  `he_logos_micro_v1` (9 entries, alignment),
  `he_core_cognition_v1` (20 entries, **no alignment**) —
  all four mounted by default in `RuntimeConfig.input_packs`.
* Cross-language binding is **shared `semantic_domains` atoms**, not
  transliteration tables: the same load-bearing tag (e.g.
  `logos.aletheia.verity`) appears across grc/he/en, and the
  alignment file binds entry-id pairs with evidence ids.  This is the
  deterministic pivot an anchor-lens composer would traverse.
* `allow_cross_language_recall=True` already; cross-language
  *generation* is deliberately gated off.

Three honest gaps separate the substrate from anchor-lens-driven
surfaces:

1. **Distinction-bearing breadth absent.**  Greek's interesting move
   is splitting one English concept into multiple lemmas
   (γνῶσις / ἐπιστήμη / σύνεσις; ἀγάπη / φιλία / ἔρως / στοργή;
   αἰών / χρόνος), but the cognition packs carry one lemma per
   concept.  Hebrew distinction-bearing families (חסד, שלום, צדק)
   absent.  Without these families, anchor lens cannot render
   "knowing-as-experience grounds knowing-as-system."
2. **No teaching corpus for non-English.**  `teaching/cognition_chains/`,
   `teaching/relations_chains/`, `teaching/cross_pack_chains/` are
   English-only.  Anchor lens needs reviewed chains traversing the
   substrate's distinctions, not bare lexicon.
3. **No realizer infrastructure for cross-lingual surface
   composition.**  Today's composers assume English lemmas.  The
   anchor-lens composer must render Greek/Hebrew distinctions
   deterministically and ideally in English compound phrasing
   (e.g. "knowing-as-experience") rather than emitting raw
   non-English glyphs at a layperson.

The register subsystem solved a similar inside-out arc in five
phases (R1 class → R2 wiring → R3 first knob → R4 seeded variation
→ R5 operator surface).  Anchor lens warrants the same discipline:
the architecture is sound but the content prerequisites are real,
and entangling code work with bulk pack ingestion is the failure
mode this ADR exists to prevent.

---

## Decision

L1 ships an **anchor lens** as a fourth pack-layer sibling
(identity / safety / ethics / **register** / **anchor lens**),
delivered inside-out across **four phases** mirroring the R1–R5
cadence.  Each phase lands its own ADR; this ADR is the umbrella
that names the architecture and binds the phases together.

> Per `feedback-no-timelines`: phases are sequenced by prerequisites,
> not clock-time.  No phase starts until its predecessor's
> invariants are pinned in CI.

### Architectural commitments (all phases)

* **Anchor lens is the substantive axis.**  Register holds
  `grounding_source` and `trace_hash` byte-identical across choices;
  anchor lens **deliberately moves both** — different substrate ⇒
  different proposition ⇒ different trace_hash.  The R5 register-tour
  seam claim does not extend to anchor lens.  A new tour
  (`core demo anchor-lens-tour`) asserts the *opposite* claim:
  `trace_hashes_distinct_across_lenses` and
  `surface_propositions_distinct_across_lenses`.
* **Anchor lens does not emit non-English glyphs.**  The user-facing
  surface is composed in English compound phrasing
  ("knowing-as-experience", "knowing-as-system") derived from the
  non-English lemma's `semantic_domains` atoms.  Greek/Hebrew glyphs
  appear only in audit / trace / provenance fields, never in
  `ChatResponse.surface`.  This protects the layperson surface
  contract (`core demo conversation`) and matches existing
  `allow_cross_language_generation=False` policy.
* **The pivot is `semantic_domains`, not lemma strings.**  Anchor
  lens never resolves on `"γνῶσις"` literally; it resolves on
  `logos.epignosis.experiential_knowledge` (or whatever atoms the
  ratified pack content commits to).  This keeps the seam
  language-neutral so future substrates (Sanskrit, Aramaic) compose
  without touching anchor-lens code.
* **No new mutation surface.**  Anchor lens packs are ratified just
  like register / identity / safety / ethics packs: JSON +
  companion `.mastery_report.json` self-seal.  Pack mutation stays
  proposal-only.
* **Replay equivalence holds within a lens.**  Same input × same
  anchor lens × same packs ⇒ byte-identical surface and trace_hash.
  Replay equivalence does NOT hold across lenses — the whole point
  of anchor lens is that it changes the proposition.

### Phase L1.1 — Content phase (pack enrichment, no code change)

**Prerequisite for every later phase.**  Enrich the substrate so
distinction-bearing lemmas exist on disk:

* **grc cognition pack additions** (target: full distinction families
  for the load-bearing English collapses):
  * Knowledge family: γνῶσις (present), **ἐπιστήμη** (systematic
    knowledge), **σύνεσις** (insight), **σοφία** (wisdom, present).
  * Love family: **ἀγάπη**, **φιλία**, **ἔρως**, **στοργή**.
  * Time family: **αἰών** (age, era), **χρόνος** (clock time),
    **καιρός** (opportune moment).
* **he cognition pack additions**: **חסד** (covenant-love), **שלום**
  (peace-wholeness), **צדק** (righteousness-rightness).
* **`alignment.jsonl` on the cognition-tier packs** (currently only
  the micro packs carry it).  Binds new lemmas to their English /
  cross-lang counterparts where they exist, and records
  `relation: cross_lang.no_english_collapse` for families English
  doesn't split.
* **Distinguishing `semantic_domains` atoms** per family member —
  e.g. `logos.epignosis.experiential_knowledge`,
  `logos.epignosis.systematic_knowledge`,
  `logos.epignosis.insight` — so the anchor-lens composer has
  ratified atoms to render against.

No realizer / runtime / composer code in L1.1.  The phase
deliverable is enriched lexicon + alignment + ratified self-seal.
This is the highest-leverage step because it unblocks every later
phase without touching code at all.

### Phase L1.2 — Pack class + loader (architectural class, no consumer)

Once L1.1 ratifies the substrate, introduce the anchor-lens pack
class.  Mirrors the register pack class (ADR-0068):

```python
@dataclass(frozen=True, slots=True)
class AnchorLens:
    lens_id: str                         # e.g. "grc_logos_v1"
    primary_substrate: str               # "grc" | "he" | "en"
    semantic_domain_preferences: tuple[str, ...]
                                         # ordered atoms; left-most wins
    cognitive_mode_label: str            # rendered in English compound
                                         # phrasing — "experiential" / "systematic"
                                         # / "covenant-bound" / etc.

@classmethod
def unanchored(cls) -> "AnchorLens": ...
    # In-memory sentinel.  Lens-aware composers MUST treat it as
    # structurally identical to "no lens applied" — byte-identical
    # to pre-L1.2 behaviour.
```

L1.2 ships the class, the loader, and one ratified pack
(`default_unanchored_v1` — structurally equivalent to the unanchored
sentinel).  No composer consumes the lens yet.  CI pins:

* `anchor_lens_byte_identity_null_lift` — full lane unchanged whether
  `RuntimeConfig.anchor_lens_id` is `None` or `default_unanchored_v1`.

### Phase L1.3 — First non-trivial lens + composer wiring

L1.3 ships the first lens that actually moves the proposition:

* `grc_logos_v1` — primary substrate grc; domain preferences pivot
  knowledge-family queries onto `logos.epignosis.experiential_knowledge`
  rather than the en-default `cognition.knowledge`.
* `he_logos_v1` — primary substrate he; pivots claim-family queries
  onto `logos.aletheia.covenant_verity` rather than
  `cognition.truth`.

`chat/pack_grounding.py` gains an `AnchorLens` parameter (mirroring
the R3 register parameter pattern).  Composers consult the lens's
`semantic_domain_preferences` to pick which lemma to render *before*
constructing the surface string.  Rendering stays English compound:
e.g. `"Knowledge-as-experience is grounded in personal acquaintance,
not abstract system."`

CI pins:
* `anchor_lens_lifts_proposition` — same prompt × {unanchored,
  grc_logos_v1, he_logos_v1} produces three different propositions
  (surface differs structurally, not just lexically; trace_hash
  differs deliberately).
* `anchor_lens_no_glyph_leak` — non-ASCII characters are absent from
  `ChatResponse.surface` regardless of lens (audit / provenance
  fields are unrestricted).

### Phase L1.4 — Telemetry + operator surface + tour demo

Mirrors R5.  TurnEvent + ChatResponse gain `anchor_lens_id`.
Telemetry serializer surfaces it.  `core chat --anchor-lens <id>`
flag.  `core demo anchor-lens-tour` walks the same prompts under
{unanchored, grc_logos_v1, he_logos_v1} and asserts:

* `lens_ids_recorded_per_turn` — TurnEvent populates `anchor_lens_id`
  on every turn.
* `trace_hashes_distinct_across_lenses` — the *opposite* of
  `register-tour`'s claim, and load-bearing here.
* `surface_propositions_distinct_across_lenses` — at least one prompt
  yields a structurally-different proposition across lenses (not just
  marker variation).

Exit code 0 iff every claim holds.

---

## Consequences

### Capability unlocked at L1.4

CORE produces structurally different propositions from different
conceptual substrates, deterministically.  A Greek-anchored answer to
"what is knowledge?" does not rephrase the English answer; it answers
from γνῶσις-vs-ἐπιστήμη as compound English phrasing and produces a
proposition that English-default would have collapsed.  Combined with
register (ADR-0068..0072), the matrix is
`{substantive lens} × {presentation register}` — orthogonal axes.

### Trust boundaries

* **Lens packs ratified like every other pack class.**  Mastery
  reports self-seal; loader rejects unratified ids in production
  mode (per ADR-0027 pattern).
* **Glyph escape is not a silent regression.**  L1.3 invariant
  `anchor_lens_no_glyph_leak` is a hard gate: a non-ASCII character
  in `ChatResponse.surface` fails the lane.
* **No new mutation surface.**  Anchor lens consumption stays
  proposal-only at the pack-mutation layer.

### Cognition lane

L1.1 (content only) and L1.2 (null-lift unanchored sentinel) are
byte-identical.  L1.3 *deliberately* moves cognition-eval numbers
when a non-default lens is loaded; the public-split byte-identical
contract holds for the unanchored default.

### Backwards compatibility

* `RuntimeConfig.anchor_lens_id: str | None = None` — defaults
  preserve pre-L1 behaviour.
* TurnEvent / ChatResponse fields default to `""`.
* Existing register / identity / safety / ethics interactions
  unchanged — anchor lens composes *upstream* of those layers
  (the composer chooses which proposition to construct; register
  then varies the surface text of that proposition).

### Performance

Negligible.  Lens lookup is one tuple-iteration over
`semantic_domain_preferences`; no SHA-256 hash per turn (variant_id
discipline is register-specific; anchor lens identity is the lens_id
itself).

---

## Verification (L1.4 acceptance gate)

```
tests/test_anchor_lens_pack_loader.py            N passed
tests/test_anchor_lens_null_lift.py              N passed
tests/test_anchor_lens_runtime_threading.py      N passed
tests/test_anchor_lens_proposition_lift.py       N passed
tests/test_anchor_lens_no_glyph_leak.py          N passed
tests/test_anchor_lens_telemetry.py              N passed
tests/test_anchor_lens_tour_demo.py              N passed

Curated lanes (must remain green):
  smoke / cognition / teaching / packs / runtime / algebra

Cognition eval byte-identical under unanchored:
  public 100 / 100 / 91.7 / 100
  holdout 100 / 100 / 83.3 / 100

core demo register-tour                          exit 0 (still holds)
core demo anchor-lens-tour                       exit 0
```

The `register-tour` claim **must continue to hold** under any anchor
lens — within a fixed lens, register choice still preserves
grounding_source and trace_hash.  The two axes are genuinely
orthogonal, not just architecturally claimed.

---

## Open questions deferred

* **Composing anchor lens × register simultaneously in the tour.**
  Two-axis demo (lens × register × prompts) is a natural follow-on
  but inflates the grid 9×; L1.4 ships single-axis lens tour first,
  composition tour later.
* **Lens × identity interaction.**  Does a `precision_first_v1`
  identity bias propositions differently under `grc_logos_v1` than
  under `he_logos_v1`?  Probably yes (axis-hedge phrasing composes
  through), but documenting it needs L1.3 evidence first.
* **Cross-language teaching corpus.**  L1.3 lemma-tier lensing is a
  prerequisite for grc/he teaching chains; the chains themselves are
  a separate phase (L2+, ADR not yet drafted).
* **More substrates beyond grc/he.**  Sanskrit (jñāna/vidyā/prajñā)
  and Aramaic distinctions sit naturally on the
  language-neutral-pivot architecture but are deferred to post-L1
  ADRs after the two-substrate case has shipped.

---

## Sequencing summary

```
L1.1  content phase — pack enrichment + alignment           ADR-0073a (this scope)
L1.2  AnchorLens class + loader + unanchored sentinel       ADR-0073b
L1.3  first non-trivial lenses + composer wiring            ADR-0073c
L1.4  telemetry + operator CLI + anchor-lens-tour demo      ADR-0073d
```

Each sub-ADR ratifies its phase in isolation, in the R1–R5 style.
This umbrella ADR-0073 names the architecture; the sub-ADRs commit
to specific lemma lists, atom names, and pack ids.  Substrate
enrichment (L1.1) is the prerequisite that unblocks everything;
nothing in L1.2–L1.4 starts until L1.1 ratifies.

---

## Why this composes against register, not replaces it

Register and anchor lens are mathematically orthogonal because:

* Register operates **after** the proposition is fixed — it only
  varies the surface string the realizer emitted (post-composer
  decoration, ADR-0071 R4).
* Anchor lens operates **before** the proposition is constructed —
  it picks which lemma's `semantic_domains` the composer should
  render, which changes the proposition itself.

This means `register-tour` and `anchor-lens-tour` test *opposite*
invariants and both must pass:

```
register-tour   asserts:  per prompt, fixing lens, varying register   ⇒ trace_hash CONSTANT
anchor-lens-tour asserts: per prompt, fixing register, varying lens   ⇒ trace_hash DISTINCT
```

If either claim ever fails the seam is broken — the orthogonality is
the load-bearing architectural commitment.
